# backend/web/routers/recetas.py  (actualizado)
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from core.auth import get_current_user
from core.logger import logger
from database.base import SessionLocal
from database.web_models import RecetaWeb, MedicamentoWeb, PacienteWeb, MedicoWeb
from lxml import etree

from services.xml_generator import generar_receta_xml_bytes
from services.drive_service import upload_xml_bytes
from services.pdf_generator import generate_receta_pdf
from services.pdf_protect import proteger_pdf_con_contrasena
from services.email_sender import enviar_receta_completa

# para firmar
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64
from fastapi.responses import FileResponse

SIGNING_KEY_PATH = os.getenv("SIGNING_KEY_PATH", "")

router = APIRouter(prefix="/recetas", tags=["recetas"])

class MedicamentoIn(BaseModel):
    nombre: str
    dosis: Optional[str] = ""
    frecuencia: Optional[str] = ""
    duracion: Optional[str] = ""

class RecetaIn(BaseModel):
    paciente_id: str
    medico: dict
    diagnostico: str
    indicaciones: Optional[str] = ""
    medicamentos: List[MedicamentoIn] = []
@router.post("/reintentar", summary="Intentar subir pendientes a drive")
async def export_receta(user=Depends(get_current_user)):
    try:
        from scripts.export_recetas import export_pending
        result = export_pending()
        logger.info(f"Export pendientes: {result}")
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Error exportando recetas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", summary="Crear receta (protected)", response_model=dict)
def crear_receta(payload: RecetaIn, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        # Verificar que paciente existe
        paciente = db.query(PacienteWeb).filter(PacienteWeb.id == payload.paciente_id).first()
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        
        # Preparar datos del paciente para XML
        paciente_data = {
            "nombre": paciente.nombre,
            "apellido": paciente.apellido,
            "fecha_nacimiento": paciente.fecha_nacimiento,
            "sexo": paciente.sexo,
            "telefono": paciente.telefono,
            "correo": paciente.correo
        }
        
        # Verificar que médico existe o crearlo si no existe
        medico = db.query(MedicoWeb).filter(MedicoWeb.id == payload.medico.get("id")).first()
        if not medico:
            medico = MedicoWeb(
                id=payload.medico.get("id"),
                nombre=payload.medico.get("nombre", ""),
                cedula=payload.medico.get("cedula", ""),
                correo=payload.medico.get("correo")
            )
            db.add(medico)
            db.commit()

        # generar XML bytes
        xml_bytes = generar_receta_xml_bytes(
            paciente_id=payload.paciente_id,
            medico=payload.medico,
            diagnostico=payload.diagnostico,
            medicamentos=[m.dict() for m in payload.medicamentos],
            indicaciones=payload.indicaciones,
            origen="WEB",
            paciente_data=paciente_data
        )

        # Parsear XML para extraer metadatos
        tree = etree.fromstring(xml_bytes)
        id_receta = tree.findtext(".//metadatos/id_receta")
        checksum = tree.findtext(".//metadatos/checksum")
        fecha_emision_str = tree.findtext(".//metadatos/fecha_emision")

        # firmar XML si existe clave privada
        if SIGNING_KEY_PATH and os.path.exists(SIGNING_KEY_PATH):
            with open(SIGNING_KEY_PATH, "rb") as f:
                key_data = f.read()
            password = os.getenv("SIGNING_KEY_PASSWORD") or None
            private_key = load_pem_private_key(key_data, password=password.encode() if password else None)
            signature = private_key.sign(
                xml_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            sig_b64 = base64.b64encode(signature).decode()
            meta = tree.find(".//metadatos")
            if meta is None:
                raise HTTPException(status_code=500, detail="XML sin metadatos")
            sig_el = etree.SubElement(meta, "signature")
            sig_el.text = sig_b64
            xml_bytes = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="utf-8")

        # Guardar XML localmente y copiar a drive_outbox para el sender_job
        xml_path = None
        os.makedirs("data/generados", exist_ok=True)
        xml_path = f"data/generados/receta_{id_receta}.xml"
        with open(xml_path, "wb") as f:
            f.write(xml_bytes)
        
        # Copiar también a drive_outbox para que el sender_job lo procese
        drive_outbox = os.path.join("data", "drive_outbox")
        os.makedirs(drive_outbox, exist_ok=True)
        outbox_path = os.path.join(drive_outbox, f"receta_{id_receta}.xml")
        with open(outbox_path, "wb") as f:
            f.write(xml_bytes)
        logger.info(f"XML copiado a drive_outbox: {outbox_path}")

        # Guardar receta en BD Web
        from datetime import datetime
        receta = RecetaWeb(
            id_receta=id_receta,
            paciente_id=payload.paciente_id,
            medico_id=payload.medico.get("id"),
            diagnostico=payload.diagnostico,
            indicaciones=payload.indicaciones,
            xml_path=xml_path,
            checksum=checksum,
            fecha_emision=datetime.fromisoformat(fecha_emision_str.replace("Z", "+00:00")) if fecha_emision_str else datetime.utcnow(),
            sent=False
        )
        db.add(receta)
        db.flush()  # Para obtener el ID de la receta

        # Guardar medicamentos en BD Web
        for med in payload.medicamentos:
            medicamento = MedicamentoWeb(
                receta_id=receta.id,
                nombre=med.nombre,
                dosis=med.dosis,
                frecuencia=med.frecuencia,
                duracion=med.duracion
            )
            db.add(medicamento)

        db.commit()

        # Generar PDF inmediatamente
        try:
            receta_data = {
                "id_receta": id_receta,
                "paciente_id": payload.paciente_id,
                "medico_id": payload.medico.get("id"),
                "diagnostico": payload.diagnostico,
                "indicaciones": payload.indicaciones,
                "fecha_emision": fecha_emision_str,
                "checksum": checksum,
            }

            pdf_path = f"data/generados/receta_{id_receta}.pdf"

            pdf_path = generate_receta_pdf(receta_data, pdf_path)

            
            # Proteger PDF con contraseña
            pdf_password = os.getenv("PDF_PASSWORD", None)
            if not pdf_password:
                import random
                import string
                pdf_password = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
                print(f"Generada contraseña aleatoria para PDF: {pdf_password}")
            
            pdf_protected_path = proteger_pdf_con_contrasena(pdf_path, pdf_password)
            
            # Actualizar receta con ruta del PDF y contraseña
            receta.pdf_path = pdf_protected_path
            receta.pdf_password = pdf_password  # ✅ Guardar contraseña
            db.commit()
            
            # ✅ ENVIAR CORREOS
            try:
                enviar_receta_completa(paciente.correo, pdf_protected_path, pdf_password)
                logger.info(f"Correos enviados para receta {id_receta}")
            except Exception as e:
                logger.error(f"Error al enviar correos: {e}")
                # No fallar la receta si falla el email

            logger.info(f"PDF generado para receta {id_receta}: {pdf_protected_path}")
        except Exception as e:
            logger.error(f"Error al generar PDF para receta {id_receta}: {e}")
            # No fallar la creación de la receta si el PDF falla

        # Subir a Drive (simulado o real)
        filename = f"receta_{id_receta}.xml"
        res = upload_xml_bytes(filename, xml_bytes)
        
        # Marcar como enviada
        receta.sent = True
        db.commit()

        logger.info(f"Usuario {user.id} creó receta {id_receta} y fue subida -> {res}")
        return {"status": "created", "id_receta": id_receta, "upload": res, "pdf_path": receta.pdf_path}
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear receta: {e}")
        raise HTTPException(status_code=500, detail=f"Error al crear receta: {str(e)}")
    finally:
        db.close()

@router.get("/", summary="Listar recetas")
def listar_recetas(user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        recetas = db.query(RecetaWeb).order_by(RecetaWeb.created_at.desc()).all()
        result = []
        for r in recetas:
            medicamentos = db.query(MedicamentoWeb).filter(MedicamentoWeb.receta_id == r.id).all()
            result.append({
                "id": r.id,
                "id_receta": r.id_receta,
                "paciente_id": r.paciente_id,
                "medico_id": r.medico_id,
                "diagnostico": r.diagnostico,
                "fecha_emision": r.fecha_emision.isoformat() if r.fecha_emision else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "sent": r.sent,
                "pdf_path": r.pdf_path,
                "medicamentos": [{"nombre": m.nombre, "dosis": m.dosis, "frecuencia": m.frecuencia} for m in medicamentos]
            })
        return result
    finally:
        db.close()

@router.get("/{id_receta}/pdf", summary="Descargar/ver PDF de receta web")
def ver_pdf_receta_web(id_receta: str, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        receta = db.query(RecetaWeb).filter(RecetaWeb.id_receta == id_receta).first()
        if not receta or not receta.pdf_path:
            raise HTTPException(status_code=404, detail="PDF no encontrado para esta receta")
        
        # Asegurar ruta absoluta
        pdf_path_abs = os.path.abspath(receta.pdf_path) if not os.path.isabs(receta.pdf_path) else receta.pdf_path
        
        if not os.path.exists(pdf_path_abs):
            raise HTTPException(status_code=404, detail=f"Archivo PDF no existe en disco: {pdf_path_abs}")
        return FileResponse(pdf_path_abs, media_type="application/pdf", filename=os.path.basename(pdf_path_abs))
    finally:
        db.close()

@router.post("/{id_receta}/reenviar-correo", summary="Reenviar correo con PDF")
def reenviar_correo(id_receta: str, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        receta = db.query(RecetaWeb).filter(RecetaWeb.id_receta == id_receta).first()
        if not receta:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        
        paciente = db.query(PacienteWeb).filter(PacienteWeb.id == receta.paciente_id).first()
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")

        medico = db.query(MedicoWeb).filter(MedicoWeb.id == receta.medico_id).first()
        if not medico:
            raise HTTPException(status_code=404, detail="Médico no encontrado")

        if not receta.pdf_path or not receta.pdf_password:
            raise HTTPException(status_code=400, detail="PDF o contraseña no disponibles")
        
        if not os.path.exists(receta.pdf_path):
            raise HTTPException(status_code=400, detail="Archivo PDF no encontrado")
        
        # Llamada correcta con todos los parámetros requeridos
        enviar_receta_completa(
            email_paciente=paciente.correo,
            pdf_path=receta.pdf_path,
            contrasena=receta.pdf_password,
            paciente_nombre=f"{paciente.nombre} {paciente.apellido}",
            medico_nombre=medico.nombre
        )

        logger.info(f"Correo reenviado para receta {id_receta}")
        return {"status": "success", "message": "Correo reenviado exitosamente"}
    
    except Exception as e:
        logger.error(f"Error al reenviar: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        db.close()
