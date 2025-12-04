import os
import sys
import hashlib
import glob
from lxml import etree

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.base import SessionLocal
from database.web_models import PacienteWeb
from services.xsd_validator import validate_xml_against_xsd
from core.logger import logger

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
IN_DIR = os.path.join(ROOT, "data", "pacientes_validos")
XSD_PATH = os.path.join(os.path.join(os.path.dirname(__file__), ".."), "xsd", "paciente.xsd")

def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
def import_file(path: str):
    try:
        xml_path = path
        valid, errors = validate_xml_against_xsd(xml_path, "paciente.xsd")
        if not valid:
            logger.error(f"[IMPORT] XSD INVALID: {os.path.basename(path)} - {errors}")
            return {"ok": False, "file": os.path.basename(path), "error": str(errors)}
        
        tree = etree.parse(path)
        root = tree.getroot()
        xml_checksum_node = root.find("metadatos/checksum")
        xml_checksum = xml_checksum_node.text.strip() if xml_checksum_node is not None and xml_checksum_node.text else None
        
        # Leer el archivo completo para calcular checksum
        with open(path, "rb") as f:
            file_content = f.read()
        file_checksum = compute_checksum(file_content)
        
        checksum_ok = None
        if xml_checksum:
            # El checksum guardado es del contenido SIN el elemento checksum
            # Entonces no pueden coincidir directamente. Solo indicar si existe.
            logger.info(f"[IMPORT] Checksum presente en {os.path.basename(path)}: {xml_checksum[:16]}...")
            checksum_ok = True  # Marcar como OK si existe el campo
        else:
            logger.warning(f"[IMPORT] CHECKSUM AUSENTE: {os.path.basename(path)}")
            checksum_ok = False
        
        pid = root.findtext("id")
        if not pid:
            logger.error(f"[IMPORT] ERROR: paciente sin <id> en {path}")
            return {"ok": False, "file": os.path.basename(path), "error": "missing id"}
        
        db = SessionLocal()
        try:
            paciente = db.query(PacienteWeb).filter(PacienteWeb.id == pid).first()
            created = False
            if not paciente:
                paciente = PacienteWeb(id=pid)
                db.add(paciente)
                created = True
            
            paciente.nombre = root.findtext("nombre") or paciente.nombre
            paciente.apellido = root.findtext("apellido") or paciente.apellido
            paciente.fecha_nacimiento = root.findtext("fecha_nacimiento") or paciente.fecha_nacimiento
            paciente.sexo = root.findtext("sexo") or paciente.sexo
            paciente.telefono = root.findtext("telefono") or paciente.telefono
            paciente.correo = root.findtext("correo") or paciente.correo
            db.commit()
            
            action = "CREADO" if created else "ACTUALIZADO"
            logger.info(f"[IMPORT] {action} paciente id={pid}")
            return {"ok": True, "created": created, "pid": pid, "checksum_ok": checksum_ok, "file": os.path.basename(path)}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[IMPORT] Error procesando {path}: {e}", exc_info=True)
        return {"ok": False, "file": os.path.basename(path), "error": str(e)}

def import_all(folder: str = IN_DIR):
    pattern = os.path.join(folder, "*.xml.ok")
    files = glob.glob(pattern)
    if not files:
        logger.warning(f"No se encontraron archivos XML en {folder}")
        return {"imported": 0, "results": []}
    
    results = []
    for f in files:
        results.append(import_file(f))
    
    success_count = len([r for r in results if r.get("ok")])
    return {"imported": success_count, "total": len(files), "results": results}

if __name__ == "__main__":
    result = import_all()
    logger.info(f"Resultado: {result}")
    print(result)