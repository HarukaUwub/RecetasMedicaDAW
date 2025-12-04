import os
import sys
from database.base import SessionLocal
from database.web_models import RecetaWeb
from core.logger import logger

try:
    from services.drive_service import upload_xml_bytes
    drive_available = True
except Exception as e:
    logger.warning(f"Drive no disponible: {e}")
    upload_xml_bytes = None
    drive_available = False


DRIVE_FOLDER = os.getenv("DRIVE_EXPORT_FOLDER_RECETAS_ID", "1hshMryU26Lf2MCCSeF7w1Ws-DQNjZhKL").strip()


def try_upload_to_drive(local_path: str, filename: str):
    if not drive_available:
        logger.error("[DRIVE] Servicio no disponible")
        return False

    if not DRIVE_FOLDER:
        logger.error("[DRIVE] DRIVE_EXPORT_FOLDER_RECETAS_ID vacío o no configurado")
        return False

    if not os.path.exists(local_path):
        logger.error(f"[DRIVE] Archivo no existe en disco: {local_path}")
        return False

    logger.info(f"[DRIVE] Intentando subir: {filename} -> carpeta {DRIVE_FOLDER}")

    try:
        with open(local_path, "rb") as f:
            xml_bytes = f.read()

        try:
            upload_xml_bytes(xml_bytes, filename, DRIVE_FOLDER)
        except TypeError:
            upload_xml_bytes(filename, xml_bytes, DRIVE_FOLDER)

        logger.info(f"[DRIVE] Subida exitosa: {filename}")
        return True

    except Exception as e:
        logger.error(f"[DRIVE] Error subiendo {filename}: {e}", exc_info=True)
        return False


def export_pending():
    db = SessionLocal()
    try:
        recetas = db.query(RecetaWeb).filter(
            RecetaWeb.xml_path != None,
            RecetaWeb.sent == False
        ).all()

        # Filtrar además que el archivo exista en disco
        recetas = [
            r for r in recetas
            if r.xml_path and os.path.exists(r.xml_path)
        ]

        if not recetas:
            return {"exported": 0, "total": 0, "details": []}

        results = []

        for m in recetas:
            filename = os.path.basename(m.xml_path)

            # --- Intentar subir ---
            uploaded = try_upload_to_drive(m.xml_path, filename)

            if uploaded:
                m.sent = True
                db.commit()

            results.append({
                "id": m.id,
                "file": filename,
                "uploaded": uploaded,
                "ok": uploaded
            })

        return {
            "exported": len([x for x in results if x["ok"]]),
            "total": len(recetas),
            "details": results
        }

    finally:
        db.close()


if __name__ == "__main__":
    result = export_pending()
    logger.info(f"Resultado: {result}")
    print(result)
