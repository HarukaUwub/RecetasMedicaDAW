from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Optional
from core.auth import get_current_user
from database.base import LocalSessionLocal
from jobs.receiver_job import check_inbox


from database.local_models import RecetaLocal
from core.logger import logger
import os

# ✅ IMPORTANTE: Sin prefix aquí, se añade en app.py
router = APIRouter(tags=["local_admin"])

@router.get("/local-admin/recetas-locales", summary="Listar recetas locales")
def listar_recetas_local(
    filtro_origen: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Lista recetas locales procesadas."""
    db = LocalSessionLocal()
    try:
        query = db.query(RecetaLocal).order_by(RecetaLocal.created_at.desc())
        
        if filtro_origen:
            query = query.filter(RecetaLocal.origen == filtro_origen)
        
        recetas = query.all()
        logger.info(f"[LOCAL ADMIN] Listadas {len(recetas)} recetas")
        return recetas
    except Exception as e:
        logger.error(f"[LOCAL ADMIN] Error listando: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/local-admin/recetas-locales/{id_receta}", summary="Obtener receta local")
def obtener_receta_local(
    id_receta: str,
    user=Depends(get_current_user)
):
    """Obtiene una receta local específica."""
    db = LocalSessionLocal()
    try:
        receta = db.query(RecetaLocal).filter(RecetaLocal.id_receta == id_receta).first()
        if not receta:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        return receta
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LOCAL ADMIN] Error obteniendo receta: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/local-admin/recetas-locales/{id_receta}/pdf", summary="Descargar PDF")
def descargar_pdf_receta(
    id_receta: str,
    user=Depends(get_current_user)
):
    """Descarga el PDF de una receta."""
    db = LocalSessionLocal()
    try:
        receta = db.query(RecetaLocal).filter(RecetaLocal.id_receta == id_receta).first()
        if not receta:
            logger.warning(f"[LOCAL ADMIN] Receta no encontrada: {id_receta}")
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        
        if not receta.pdf_path:
            logger.warning(f"[LOCAL ADMIN] PDF_PATH vacío para {id_receta}")
            raise HTTPException(status_code=404, detail="PDF no disponible (sin ruta)")
        
        if not os.path.exists(receta.pdf_path):
            logger.error(f"[LOCAL ADMIN] PDF no existe: {receta.pdf_path}")
            raise HTTPException(status_code=404, detail=f"PDF no existe en servidor")
        
        logger.info(f"[LOCAL ADMIN] Descargando PDF: {receta.pdf_path}")
        
        return FileResponse(
            path=receta.pdf_path,
            media_type="application/pdf",
            filename=f"receta_{id_receta}.pdf"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LOCAL ADMIN] Error descargando PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.delete("/local-admin/recetas-locales/{id_receta}", summary="Eliminar receta")
def eliminar_receta_local(
    id_receta: str,
    user=Depends(get_current_user)
):
    """Elimina una receta local."""
    db = LocalSessionLocal()
    try:
        receta = db.query(RecetaLocal).filter(RecetaLocal.id_receta == id_receta).first()
        if not receta:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        
        if receta.pdf_path and os.path.exists(receta.pdf_path):
            try:
                os.remove(receta.pdf_path)
                logger.info(f"[LOCAL ADMIN] PDF eliminado: {receta.pdf_path}")
            except Exception as e:
                logger.warning(f"[LOCAL ADMIN] Error eliminando PDF: {e}")
        
        db.delete(receta)
        db.commit()
        logger.info(f"[LOCAL ADMIN] Receta eliminada: {id_receta}")
        return {"msg": "Receta eliminada", "id_receta": id_receta}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[LOCAL ADMIN] Error eliminando: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/local-admin/stats", summary="Estadísticas")
def obtener_stats(user=Depends(get_current_user)):
    """Retorna estadísticas de recetas locales."""
    db = LocalSessionLocal()
    try:
        total = db.query(RecetaLocal).count()
        por_origen = {}
        for origen in ["drive", "local", "web"]:
            count = db.query(RecetaLocal).filter(RecetaLocal.origen == origen).count()
            if count > 0:
                por_origen[origen] = count
        
        con_pdf = db.query(RecetaLocal).filter(RecetaLocal.pdf_path.isnot(None)).count()
        
        return {
            "total": total,
            "por_origen": por_origen,
            "con_pdf": con_pdf,
            "sin_pdf": total - con_pdf
        }
    except Exception as e:
        logger.error(f"[LOCAL ADMIN] Error en stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/local-admin/forzar-sincronizacion", summary="Forzar sincronización")
def forzar_sincronizacion(user=Depends(get_current_user)):
    """Sincroniza Drive → Local y procesa XML."""
    try:
        logger.info("[LOCAL ADMIN] 🔄 Iniciando sincronización Drive → Local...")

        nuevos = check_inbox()

        return {
            "msg": "✔️ Sincronización completada",
            "nuevos_descargados": nuevos,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"[LOCAL ADMIN] Error sincronizando: {e}")
        raise HTTPException(status_code=500, detail=str(e))
