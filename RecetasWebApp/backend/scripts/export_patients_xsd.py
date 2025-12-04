import os
import sys
import hashlib
from datetime import datetime
from lxml import etree

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.base import SessionLocal
from database.web_models import PacienteWeb
from services.xsd_validator import validate_xml_against_xsd
from core.logger import logger

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
OUT_DIR = os.path.join(ROOT, "data", "pacientes_validos")
XSD_PATH = os.path.join(os.path.join(os.path.dirname(__file__), ".."), "xsd", "paciente.xsd")
DRIVE_FOLDER = os.getenv("DRIVE_EXPORT_FOLDER_PATIENTS_ID", "1VI0PVZhhjNuKBezFrOO50m1GiIV2IK8x").strip()
os.makedirs(OUT_DIR, exist_ok=True)

try:
    from services.drive_service import upload_xml_bytes
    drive_available = True
except Exception as e:
    logger.warning(f"Drive no disponible: {e}")
    upload_xml_bytes = None
    drive_available = False

def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def build_patient_xml(p: PacienteWeb) -> etree._Element:
    root = etree.Element("paciente", id=str(p.id) if p.id is not None else "")
    def add(tag, text):
        if text is None:
            return
        el = etree.SubElement(root, tag)
        el.text = str(text)
    add("id", p.id)
    add("nombre", p.nombre)
    add("apellido", p.apellido)
    add("fecha_nacimiento", p.fecha_nacimiento)
    add("sexo", p.sexo)
    add("telefono", p.telefono)
    add("correo", p.correo)
    meta = etree.SubElement(root, "metadatos")
    fecha = etree.SubElement(meta, "fecha_creacion")
    fecha.text = datetime.utcnow().isoformat()
    return root

def try_upload_to_drive(local_path: str, filename: str):
    if not drive_available or not DRIVE_FOLDER:
        logger.debug(f"[DRIVE] No configurado")
        return False
    try:
        with open(local_path, "rb") as f:
            xml_bytes = f.read()
        try:
            upload_xml_bytes(xml_bytes, filename, DRIVE_FOLDER)
        except TypeError:
            upload_xml_bytes(filename, xml_bytes, DRIVE_FOLDER)
        logger.info(f"[DRIVE] Subido {filename} a carpeta {DRIVE_FOLDER}")
        return True
    except Exception as e:
        logger.error(f"[DRIVE] Error subiendo {filename}: {e}")
        return False

def export_all():
    db = SessionLocal()
    try:
        pacientes = db.query(PacienteWeb).all()
        if not pacientes:
            logger.warning("No hay pacientes para exportar.")
            return {"exported": 0, "details": []}
        count = 0
        results = []
        for p in pacientes:
            try:
                root = build_patient_xml(p)
                
                filename = f"paciente_{p.id}.xml"
                out_path = os.path.join(OUT_DIR, filename)
                
                # 1. Escribir XML SIN checksum
                etree.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True, pretty_print=True)
                
                # 2. Leer el archivo escrito para calcular el checksum exacto
                with open(out_path, "rb") as f:
                    xml_bytes = f.read()
                checksum = compute_checksum(xml_bytes)
                logger.info(f"[EXPORT] Checksum calculado para {filename}: {checksum}")
                
                # 3. Releer el árbol, añadir checksum y volver a escribir
                tree = etree.parse(out_path)
                root = tree.getroot()
                meta = root.find("metadatos")
                checksum_el = etree.SubElement(meta, "checksum")
                checksum_el.text = checksum
                
                # 4. Escribir nuevamente con el checksum
                tree.write(out_path, encoding="utf-8", xml_declaration=True, pretty_print=True)
                
                valid, errors = validate_xml_against_xsd(out_path, "paciente.xsd")
                if valid:
                    uploaded = False
                    if drive_available and DRIVE_FOLDER:
                        uploaded = try_upload_to_drive(out_path, filename)
                    results.append({"file": filename, "checksum": checksum, "uploaded": uploaded, "ok": True})
                    logger.info(f"[EXPORT] OK: {filename}")
                    count += 1
                else:
                    results.append({"file": filename, "error": str(errors), "ok": False})
                    logger.error(f"[EXPORT] XSD INVALID: {filename} - {errors}")
            except Exception as e:
                logger.error(f"[EXPORT] Error procesando paciente {p.id}: {e}", exc_info=True)
                results.append({"file": f"paciente_{p.id}.xml", "error": str(e), "ok": False})
        return {"exported": count, "total": len(pacientes), "details": results}
    except Exception as e:
        logger.error(f"[EXPORT] Error general: {e}")
        return {"exported": 0, "error": str(e)}
    finally:
        db.close()

if __name__ == "__main__":
    result = export_all()
    logger.info(f"Resultado: {result}")
    print(result)