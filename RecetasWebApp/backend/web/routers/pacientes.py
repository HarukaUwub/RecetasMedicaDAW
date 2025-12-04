from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.auth import get_current_user
from database.base import SessionLocal
from database.web_models import PacienteWeb
from core.logger import logger

router = APIRouter(prefix="/pacientes", tags=["pacientes"])

class PacienteIn(BaseModel):
    id: str
    nombre: str
    apellido: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    sexo: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None

# ✅ EXPORT/IMPORT PRIMERO (antes de GET/POST genéricos)
@router.post("/export-xsd", summary="Exportar pacientes a XSD")
async def export_pacientes_xsd(user=Depends(get_current_user)):
    """Exporta todos los pacientes a XML con validación XSD"""
    try:
        from scripts.export_patients_xsd import export_all
        result = export_all()
        logger.info(f"Export pacientes: {result}")
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Error exportando pacientes XSD: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import-xsd", summary="Importar pacientes XSD")
async def import_pacientes_xsd(user=Depends(get_current_user)):
    """Importa pacientes desde XMLs en la carpeta local"""
    try:
        from scripts.import_patients_xsd import import_all
        result = import_all()
        logger.info(f"Import pacientes: {result}")
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Error importando pacientes XSD: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ✅ DESPUÉS: endpoints genéricos
@router.get("/", summary="Listar pacientes")
async def listar_pacientes(user=Depends(get_current_user)):
    """Lista todos los pacientes"""
    db = SessionLocal()
    try:
        pacientes = db.query(PacienteWeb).all()
        return [{"id": p.id, "nombre": p.nombre, "apellido": p.apellido, "correo": p.correo} for p in pacientes]
    finally:
        db.close()

@router.get("/{paciente_id}", summary="Obtener paciente por ID")
async def obtener_paciente(paciente_id: str, user=Depends(get_current_user)):
    """Obtiene un paciente específico"""
    db = SessionLocal()
    try:
        paciente = db.query(PacienteWeb).filter(PacienteWeb.id == paciente_id).first()
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        return paciente
    finally:
        db.close()

@router.post("/", summary="Crear paciente")
async def crear_paciente(payload: PacienteIn, user=Depends(get_current_user)):
    """Crea un nuevo paciente"""
    db = SessionLocal()
    try:
        existente = db.query(PacienteWeb).filter(PacienteWeb.id == payload.id).first()
        if existente:
            raise HTTPException(status_code=400, detail="Paciente con este ID ya existe")
        
        paciente = PacienteWeb(
            id=payload.id,
            nombre=payload.nombre,
            apellido=payload.apellido,
            fecha_nacimiento=payload.fecha_nacimiento,
            sexo=payload.sexo,
            telefono=payload.telefono,
            correo=payload.correo
        )
        db.add(paciente)
        db.commit()
        logger.info(f"Paciente creado: {payload.id}")
        return {"msg": "Paciente creado", "id": payload.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear paciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
