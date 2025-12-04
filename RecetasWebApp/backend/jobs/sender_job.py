import os
import time
import shutil
from core.logger import logger
from services.drive_service import upload_xml_bytes

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTBOX = os.path.join(ROOT, "data", "drive_outbox")
PROCESADOS_OUTBOX = os.path.join(ROOT, "data", "procesados_outbox")

INTERVALO = int(os.getenv("SENDER_INTERVAL_SECONDS", "10"))  # segundos

os.makedirs(OUTBOX, exist_ok=True)
os.makedirs(PROCESADOS_OUTBOX, exist_ok=True)

def job_sender():
    logger.info("JOB SENDER iniciado - Monitoreando carpeta drive_outbox/")
    
    while True:
        try:
            if not os.path.exists(OUTBOX):
                logger.warning(f"Carpeta {OUTBOX} no existe")
                time.sleep(INTERVALO)
                continue
                
            archivos = [f for f in os.listdir(OUTBOX) if f.lower().endswith(".xml")]
            
            if not archivos:
                logger.debug("No hay archivos XML en drive_outbox/")
            else:
                logger.info(f"Encontrados {len(archivos)} archivo(s) XML para enviar")

            for xml_file in archivos:
                path = os.path.join(OUTBOX, xml_file)
                try:
                    with open(path, "rb") as f:
                        xml_bytes = f.read()
                    
                    # Subir a Drive (simulado o real)
                    res = upload_xml_bytes(xml_file, xml_bytes)
                    logger.info(f"XML {xml_file} enviado -> {res}")
                    
                    # Mover a carpeta de procesados
                    dest = os.path.join(PROCESADOS_OUTBOX, xml_file)
                    shutil.move(path, dest)
                    logger.info(f"Archivo {xml_file} movido a procesados_outbox/")
                    
                except Exception as e:
                    logger.error(f"Error procesando {xml_file}: {e}")
                    # Mover a errores si falla
                    errores_dir = os.path.join(ROOT, "data", "errores_outbox")
                    os.makedirs(errores_dir, exist_ok=True)
                    try:
                        shutil.move(path, os.path.join(errores_dir, xml_file))
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Error en job_sender: {e}")
        
        time.sleep(INTERVALO)
