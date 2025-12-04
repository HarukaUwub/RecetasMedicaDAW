# backend/jobs/receiver_job.py
import os
import sys
import time
import glob
import secrets

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from lxml import etree
from database.base import SessionLocal, LocalSessionLocal
from database.local_models import RecetaLocal
from database.web_models import RecetaWeb, PacienteWeb, MedicoWeb
from services.checksum import validar_checksum
from services.drive_service import sync_drive_to_local
from services.xsd_validator import validate_xml_against_xsd
from services.xml_generator import parse_receta_xml
from services.pdf_generator import generate_receta_pdf
from services.pdf_protect import proteger_pdf_con_contrasena
from services.email_sender import enviar_receta_completa
from core.logger import logger
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INBOX_DIR = os.path.join(ROOT, "data", "drive_inbox")
PROCESADOS_DIR = os.path.join(ROOT, "data", "procesados_inbox")
ERRORES_DIR = os.path.join(ROOT, "data", "errores_inbox")
PDFS_DIR = os.path.join(ROOT, "data", "pdf")
ROOT_LOCAL = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_DIR = os.path.join(ROOT, "data", "generados")
MEDICOS_DIR = os.path.join(ROOT, "data", "medicos_validos")
PACIENTES_DIR = os.path.join(ROOT, "data", "pacientes_validos")

os.makedirs(MEDICOS_DIR, exist_ok=True)
os.makedirs(PACIENTES_DIR, exist_ok=True)

os.makedirs(LOCAL_DIR, exist_ok=True)

os.makedirs(INBOX_DIR, exist_ok=True)
os.makedirs(PROCESADOS_DIR, exist_ok=True)
os.makedirs(ERRORES_DIR, exist_ok=True)
os.makedirs(PDFS_DIR, exist_ok=True)

def move_file(src: str, dest: str) -> bool:
    """Mueve un archivo."""
    try:
        os.rename(src, dest)
        logger.info(f"[MOVE] {os.path.basename(src)} -> {os.path.basename(dest)}")
        return True
    except Exception as e:
        logger.error(f"[MOVE] Error: {e}")
        return False

def process_receta_xml(xml_path: str, origen: str) -> dict:
    """Procesa receta XML completa: validación → PDF → BD → envío correo."""
    filename = os.path.basename(xml_path)
    logger.info(f"[PROCESS] Inicio ({origen}): {xml_path}")

    try:
        # 1️⃣ Validar XSD
        valid, errors = validate_xml_against_xsd(xml_path, "receta.xsd")
        if not valid:
            logger.error(f"[XSD] INVALID: {filename}")
            error_path = os.path.join(ERRORES_DIR, f"{filename}.xsd_error")
            move_file(xml_path, error_path)
            return {"ok": False, "file": filename, "error": f"XSD: {errors}"}

        # 2️⃣ Validar CHECKSUM
        if not validar_checksum(xml_path):
            logger.error(f"[CHECKSUM] INVALID: {filename}")
            error_path = os.path.join(ERRORES_DIR, f"{filename}.checksum_error")
            move_file(xml_path, error_path)
            return {"ok": False, "file": filename, "error": "Checksum inválido"}
        # 2️⃣ Parsear XML
        try:
            receta_data = parse_receta_xml(xml_path)
        except Exception as e:
            logger.error(f"[PARSE] Error: {e}")
            error_path = os.path.join(ERRORES_DIR, f"{filename}.parse_error")
            move_file(xml_path, error_path)
            return {"ok": False, "file": filename, "error": f"Parse: {str(e)}"}

        # 3️⃣ Obtener datos adicionales desde BD Web
        web_db = SessionLocal()
        try:
            paciente = web_db.query(PacienteWeb).filter(
                PacienteWeb.id == receta_data.get('paciente_id')
            ).first()

            medico = web_db.query(MedicoWeb).filter(
                MedicoWeb.id == receta_data.get('medico_id')
            ).first()

            email_paciente = paciente.correo if paciente else None

        finally:
            web_db.close()

        # 4️⃣ Generar PDF
        pdf_filename = f"receta_{receta_data.get('id_receta')}.pdf"
        pdf_path = os.path.join(PDFS_DIR, pdf_filename)

        try:
            logger.info(f"[PDF] Generando: {pdf_path}")
            generate_receta_pdf(receta_data, pdf_path)
        except Exception as e:
            logger.warning(f"[PDF] ⚠️ Error generando PDF: {e}")
            pdf_path = None

        # 5️⃣ Proteger PDF
        contrasena_pdf = None
        if pdf_path and os.path.exists(pdf_path):
            try:
                contrasena_pdf = secrets.token_urlsafe(12)
                pdf_path = proteger_pdf_con_contrasena(pdf_path, contrasena_pdf)
                logger.info(f"[PDF PROTECT] PDF protegido correctamente")
            except Exception as e:
                logger.warning(f"[PDF PROTECT] ⚠️ Error: {e}")

        # 6️⃣ Mover XML a procesados
        success_path = os.path.join(PROCESADOS_DIR, f"{filename}.ok")
        move_file(xml_path, success_path)

        # 7️⃣ Guardar en BD Local
        local_db = LocalSessionLocal()
        try:
            # Parsear fecha
            fecha_emision_str = receta_data.get('fecha_emision')
            fecha_emision_dt = None
            if fecha_emision_str:
                try:
                    fecha_emision_dt = datetime.fromisoformat(fecha_emision_str)
                except:
                    logger.warning(f"[DATE] Fecha inválida: {fecha_emision_str}")

            # Verificar si ya existe en BD local
            existe = local_db.query(RecetaLocal).filter(
                RecetaLocal.id_receta == receta_data.get('id_receta')
            ).first()

            if existe:
                logger.warning(
                    f"[DB LOCAL] Receta DUPLICADA ignorada: {receta_data.get('id_receta')}"
                )
                return {
                    "ok": True,
                    "file": filename,
                    "id_receta": receta_data.get('id_receta'),
                    "duplicado": True,
                    "origen": origen
                }

            # Crear registro nuevo
            receta_local = RecetaLocal(
                id_receta=receta_data.get('id_receta'),
                paciente_id=receta_data.get('paciente_id'),
                medico_id=receta_data.get('medico_id'),
                diagnostico=receta_data.get('diagnostico'),
                indicaciones=receta_data.get('indicaciones'),
                xml_path=success_path,
                pdf_path=pdf_path,
                checksum=receta_data.get('checksum'),
                fecha_emision=fecha_emision_dt,
                origen=origen
            )

            local_db.add(receta_local)
            local_db.commit()
            logger.info(f"[DB LOCAL] Receta guardada correctamente")

        except Exception as e:
            local_db.rollback()
            logger.error(f"[DB LOCAL] Error: {e}")
            error_path = os.path.join(ERRORES_DIR, f"{filename}.db_error")
            move_file(xml_path, error_path)
            return {"ok": False, "file": filename, "error": f"DB: {str(e)}"}

        finally:
            local_db.close()

        # 8️⃣ Guardar en BD Web (no importa duplicados)
        try:
            web_db = SessionLocal()
            receta_web = RecetaWeb(
                id_receta=receta_data.get('id_receta'),
                paciente_id=receta_data.get('paciente_id'),
                medico_id=receta_data.get('medico_id'),
                diagnostico=receta_data.get('diagnostico'),
                indicaciones=receta_data.get('indicaciones'),
                xml_path=xml_path,
                pdf_path=pdf_path,
                checksum=receta_data.get('checksum'),
                fecha_emision=fecha_emision_dt,
                origen=origen
            )
            web_db.add(receta_web)
            web_db.commit()

        except Exception as e:
            web_db.rollback()
            logger.warning(f"[DB WEB] Warning insertando receta: {e}")

        finally:
            web_db.close()

        return {
            "ok": True,
            "file": filename,
            "id_receta": receta_data.get('id_receta'),
            "pdf_protegido": pdf_path is not None,
            "origen": origen
        }

    except Exception as e:
        logger.error(f"[PROCESS] Error general: {e}", exc_info=True)
        error_path = os.path.join(ERRORES_DIR, f"{filename}.error")
        move_file(xml_path, error_path)
        return {"ok": False, "file": filename, "error": str(e)}

def check_inbox():
    """Descarga desde Drive y luego procesa XMLs."""

    # 1. Descargar nuevos archivos
    nuevos = sync_drive_to_local()
    if nuevos > 0:
        logger.info(f"[INBOX] 🚀 Descargados desde Drive: {nuevos}")
    else:
        logger.info(f"[INBOX] No hay nuevos archivos en Drive")

    # 2. Procesar XML locales
    xml_files = glob.glob(os.path.join(INBOX_DIR, "*.xml"))

    if not xml_files:
        logger.debug("[INBOX] Sin archivos por procesar")
        return

    logger.info(f"[INBOX] Procesando {len(xml_files)} archivos...")

    for xml_path in xml_files:
        fname = os.path.basename(xml_path)

        # 🩵 Orden correcto:
        if fname.startswith("medico_"):
            process_medico_xml(xml_path, origen="drive")

        elif fname.startswith("paciente_"):
            process_paciente_xml(xml_path, origen="drive")

        elif fname.startswith("receta_"):
            process_receta_xml(xml_path, origen="drive")

        else:
            logger.warning(f"[INBOX] Archivo desconocido ignorado: {fname}")

        

def job_receiver():
    """JOB que corre continuamente."""
    logger.info("[JOB RECEIVER] Iniciado")
    
    while True:
        try:
            check_inbox()
        except Exception as e:
            logger.error(f"[JOB] Error: {e}", exc_info=True)
        
        time.sleep(10)
def process_medico_xml(xml_path: str, origen: str):
    filename = os.path.basename(xml_path)
    logger.info(f"[MEDICO] Procesando {filename} ({origen})")

    try:
        valid, errors = validate_xml_against_xsd(xml_path, "medico.xsd")
        if not valid:
            logger.error(f"[MEDICO XSD] INVALID: {filename}")
            move_file(xml_path, os.path.join(ERRORES_DIR, f"{filename}.xsd_error"))
            return
# Añadir aquí:
        if not validar_checksum(xml_path):
            logger.error(f"[MEDICO CHECKSUM] INVALID: {filename}")
            move_file(xml_path, os.path.join(ERRORES_DIR, f"{filename}.checksum_error"))
            return
        tree = etree.parse(xml_path)
        root = tree.getroot()

        mid = root.findtext("id")
        nombre = root.findtext("nombre")
        cedula = root.findtext("cedula")
        correo = root.findtext("correo")

        db = SessionLocal()
        try:
            medico = db.query(MedicoWeb).filter(MedicoWeb.id == mid).first()
            if medico:
                medico.nombre = nombre or medico.nombre
                medico.cedula = cedula or medico.cedula
                medico.correo = correo or medico.correo
                logger.info(f"[MEDICO] Actualizado {mid}")
            else:
                medico = MedicoWeb(
                    id=mid,
                    nombre=nombre,
                    cedula=cedula,
                    correo=correo
                )
                db.add(medico)
                logger.info(f"[MEDICO] Creado {mid}")

            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"[MEDICO] Error: {e}")
        finally:
            db.close()

        move_file(xml_path, os.path.join(MEDICOS_DIR, f"{filename}.ok"))

    except Exception as e:
        logger.error(f"[MEDICO] Error general: {e}", exc_info=True)
def process_paciente_xml(xml_path: str, origen: str):
    filename = os.path.basename(xml_path)
    logger.info(f"[PACIENTE] Procesando {filename} ({origen})")

    try:
        valid, errors = validate_xml_against_xsd(xml_path, "paciente.xsd")
        if not valid:
            logger.error(f"[PACIENTE XSD] INVALID: {filename}")
            move_file(xml_path, os.path.join(ERRORES_DIR, f"{filename}.xsd_error"))
            return
        if not validar_checksum(xml_path):
            logger.error(f"[PACIENTE CHECKSUM] INVALID: {filename}")
            move_file(xml_path, os.path.join(ERRORES_DIR, f"{filename}.checksum_error"))
            return
        tree = etree.parse(xml_path)
        root = tree.getroot()

        pid = root.findtext("id")
        nombre = root.findtext("nombre")
        apellido = root.findtext("apellido")
        fecha = root.findtext("fecha_nacimiento")
        sexo = root.findtext("sexo")
        telefono = root.findtext("telefono")
        correo = root.findtext("correo")

        db = SessionLocal()
        try:
            paciente = db.query(PacienteWeb).filter(PacienteWeb.id == pid).first()
            if paciente:
                paciente.nombre = nombre or paciente.nombre
                paciente.apellido = apellido or paciente.apellido
                paciente.fecha_nacimiento = fecha or paciente.fecha_nacimiento
                paciente.sexo = sexo or paciente.sexo
                paciente.telefono = telefono or paciente.telefono
                paciente.correo = correo or paciente.correo
                logger.info(f"[PACIENTE] Actualizado {pid}")
            else:
                paciente = PacienteWeb(
                    id=pid,
                    nombre=nombre,
                    apellido=apellido,
                    fecha_nacimiento=fecha,
                    sexo=sexo,
                    telefono=telefono,
                    correo=correo
                )
                db.add(paciente)
                logger.info(f"[PACIENTE] Creado {pid}")

            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"[PACIENTE] Error: {e}")
        finally:
            db.close()

        move_file(xml_path, os.path.join(PACIENTES_DIR, f"{filename}.ok"))

    except Exception as e:
        logger.error(f"[PACIENTE] Error general: {e}", exc_info=True)

if __name__ == "__main__":
    job_receiver()
