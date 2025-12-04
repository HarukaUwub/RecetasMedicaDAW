from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.auth import get_current_user
from database.base import SessionLocal
from database.web_models import MedicoWeb
from core.logger import logger

router = APIRouter(prefix="/medicos", tags=["medicos"])

class MedicoIn(BaseModel):
    id: str
    nombre: str
    cedula: Optional[str] = None
    correo: Optional[str] = None

# ✅ EXPORT/IMPORT PRIMERO
@router.post("/export-xsd", summary="Exportar médicos a XSD")
async def export_medicos_xsd(user=Depends(get_current_user)):
    """Exporta todos los médicos a XML con validación XSD"""
    try:
        from scripts.export_medicos_xsd import export_all
        result = export_all()
        logger.info(f"Export medicos: {result}")
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Error exportando medicos XSD: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import-xsd", summary="Importar médicos XSD")
async def import_medicos_xsd(user=Depends(get_current_user)):
    """Importa médicos desde XMLs en la carpeta local"""
    try:
        from scripts.import_medicos_xsd import import_all
        result = import_all()
        logger.info(f"Import medicos: {result}")
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Error importando medicos XSD: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ✅ DESPUÉS: endpoints genéricos
@router.get("/", summary="Listar médicos")
async def listar_medicos(user=Depends(get_current_user)):
    """Lista todos los médicos"""
    db = SessionLocal()
    try:
        medicos = db.query(MedicoWeb).all()
        return [{"id": m.id, "nombre": m.nombre, "cedula": m.cedula, "correo": m.correo} for m in medicos]
    finally:
        db.close()

@router.get("/{medico_id}", summary="Obtener médico por ID")
async def obtener_medico(medico_id: str, user=Depends(get_current_user)):
    """Obtiene un médico específico"""
    db = SessionLocal()
    try:
        medico = db.query(MedicoWeb).filter(MedicoWeb.id == medico_id).first()
        if not medico:
            raise HTTPException(status_code=404, detail="Médico no encontrado")
        return medico
    finally:
        db.close()

@router.post("/", summary="Crear médico")
async def crear_medico(payload: MedicoIn, user=Depends(get_current_user)):
    """Crea un nuevo médico"""
    db = SessionLocal()
    try:
        existente = db.query(MedicoWeb).filter(MedicoWeb.id == payload.id).first()
        if existente:
            raise HTTPException(status_code=400, detail="Médico con este ID ya existe")
        
        medico = MedicoWeb(
            id=payload.id,
            nombre=payload.nombre,
            cedula=payload.cedula,
            correo=payload.correo
        )
        db.add(medico)
        db.commit()
        logger.info(f"Médico creado: {payload.id}")
        return {"msg": "Médico creado", "id": payload.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear médico: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
