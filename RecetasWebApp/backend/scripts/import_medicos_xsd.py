import os
import sys
import hashlib
import glob
from lxml import etree

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.base import SessionLocal
from database.web_models import MedicoWeb
from services.xsd_validator import validate_xml_against_xsd
from core.logger import logger

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
IN_DIR = os.path.join(ROOT, "data", "medicos_validos")
XSD_PATH = os.path.join(os.path.join(os.path.dirname(__file__), "..", "xsd", "medico.xsd"))

def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def import_file(path: str):
    try:
        xml_path = path
        valid, errors = validate_xml_against_xsd(xml_path, "receta.xsd")
        if not valid:
            logger.error(f"[IMPORT MEDICOS] XSD INVALID: {os.path.basename(path)} - {errors}")
            return {"ok": False, "file": os.path.basename(path), "error": str(errors)}
        
        tree = etree.parse(path)
        root = tree.getroot()
        xml_checksum_node = root.find("metadatos/checksum")
        xml_checksum = xml_checksum_node.text.strip() if xml_checksum_node is not None and xml_checksum_node.text else None
        
        checksum_ok = None
        if xml_checksum:
            logger.info(f"[IMPORT MEDICOS] Checksum presente en {os.path.basename(path)}: {xml_checksum[:16]}...")
            checksum_ok = True
        else:
            logger.warning(f"[IMPORT MEDICOS] CHECKSUM AUSENTE: {os.path.basename(path)}")
            checksum_ok = False
        
        mid = root.findtext("id")
        if not mid:
            logger.error(f"[IMPORT MEDICOS] ERROR: medico sin <id> en {path}")
            return {"ok": False, "file": os.path.basename(path), "error": "missing id"}
        
        db = SessionLocal()
        try:
            medico = db.query(MedicoWeb).filter(MedicoWeb.id == mid).first()
            created = False
            if not medico:
                medico = MedicoWeb(id=mid)
                db.add(medico)
                created = True
            
            medico.nombre = root.findtext("nombre") or medico.nombre
            medico.cedula = root.findtext("cedula") or medico.cedula
            medico.correo = root.findtext("correo") or medico.correo
            db.commit()
            
            action = "CREADO" if created else "ACTUALIZADO"
            logger.info(f"[IMPORT MEDICOS] {action} medico id={mid}")
            return {"ok": True, "created": created, "mid": mid, "checksum_ok": checksum_ok, "file": os.path.basename(path)}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[IMPORT MEDICOS] Error procesando {path}: {e}", exc_info=True)
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