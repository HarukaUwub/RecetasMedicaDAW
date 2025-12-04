# backend/services/drive_service.py
import os
import shutil
from dotenv import load_dotenv

load_dotenv()
from core.logger import logger

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
OUTBOX = os.path.join(DATA_ROOT, "drive_outbox")
INBOX = os.path.join(DATA_ROOT, "drive_inbox")
SIMULATED = os.getenv("DRIVE_SIMULATED", "false").lower() in ("1", "true", "yes")

# --- Configuración Drive ---
# Service Account (modo antiguo / shared drive)
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "service_account.json")

# OAuth2 (usar tu cuenta personal de Google Drive)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "574854646055-73gvb9a339fks488pbjeuafojpndqa5r.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", "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")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_DRIVE_REFRESH_TOKEN", "1//0fYwUvsiq3_SCCgYIARAAGA8SNwF-L9Ir0lJWaSSFb0Dfoj-pq79ha4_zV8Dl7ZopqiN7OdPYRWE58EjO9-qrKTI2xs32ZVP2gRs")
GOOGLE_TOKEN_URI = os.getenv("GOOGLE_DRIVE_TOKEN_URI", "https://oauth2.googleapis.com/token")

FOLDER_OUTBOX_ID = os.getenv("GOOGLE_DRIVE_FOLDER_OUTBOX_ID", "")
FOLDER_INBOX_ID = os.getenv("GOOGLE_DRIVE_FOLDER_INBOX_ID", "")

def upload_simulated(filepath):
    os.makedirs(OUTBOX, exist_ok=True)
    dest = os.path.join(OUTBOX, os.path.basename(filepath))
    shutil.copy(filepath, dest)
    logger.info(f"[Drive Simulado] Copiado a {dest}")
    return {"mode": "simulated", "path": dest}

def upload_bytes_simulated(filename, data: bytes):
    os.makedirs(OUTBOX, exist_ok=True)
    os.makedirs(INBOX, exist_ok=True)
    
    # Guardar en outbox (para sender_job)
    dest_outbox = os.path.join(OUTBOX, filename)
    with open(dest_outbox, "wb") as f:
        f.write(data)
    logger.info(f"[Drive Simulado] Guardado en outbox: {dest_outbox}")
    
    # También copiar a inbox para simular el flujo completo (receiver_job procesará)
    dest_inbox = os.path.join(INBOX, filename)
    with open(dest_inbox, "wb") as f:
        f.write(data)
    logger.info(f"[Drive Simulado] Copiado a inbox: {dest_inbox}")
    
    return {"mode": "simulated", "path": dest_outbox, "inbox_path": dest_inbox}


def _build_service_account_drive():
    """Construye el cliente de Drive usando Service Account (modo anterior)."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception:
        logger.error(
            "Dependencias Google API no instaladas: pip install google-api-python-client google-auth"
        )
        raise

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_JSON,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    return build("drive", "v3", credentials=creds)


def _build_oauth_drive():
    """
    Construye el cliente de Drive usando OAuth2 con tu cuenta personal.

    Requiere en .env:
      GOOGLE_DRIVE_CLIENT_ID
      GOOGLE_DRIVE_CLIENT_SECRET
      GOOGLE_DRIVE_REFRESH_TOKEN
    (obtenidos desde credentials.json de una app Desktop)
    """
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN):
        raise RuntimeError(
            "Faltan variables de entorno para OAuth2 de Drive "
            "(GOOGLE_DRIVE_CLIENT_ID / SECRET / REFRESH_TOKEN)."
        )

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except Exception:
        logger.error(
            "Dependencias Google API no instaladas: pip install google-api-python-client google-auth"
        )
        raise

    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    # Refrescar el access token usando el refresh token (sin interacción)
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


def _get_drive_service():
    """
    Devuelve un cliente de Drive.
    - Si hay refresh token configurado -> usa OAuth2 (tu unidad personal).
    - Si no -> usa Service Account (modo anterior).
    """
    if GOOGLE_REFRESH_TOKEN:
        logger.info("[Drive] Usando OAuth2 (cuenta personal)")
        return _build_oauth_drive()
    logger.info("[Drive] Usando Service Account")
    return _build_service_account_drive()



def upload_bytes_real(filename, data: bytes, folder_id: str):
    """
    Sube bytes como archivo con nombre filename a Google Drive.
    Puede usar Service Account o OAuth2 según configuración.
    """
    try:
        from googleapiclient.http import MediaIoBaseUpload
        import io
    except Exception:
        logger.error(
            "Dependencias Google API no instaladas: pip install google-api-python-client google-auth"
        )
        raise

    service = _get_drive_service()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype="text/xml")
    meta = {"name": filename}
    if folder_id:
        meta["parents"] = [folder_id]
    uploaded = (
        service.files()
        .create(body=meta, media_body=media, fields="id")
        .execute()
    )
    logger.info(f"[Drive Real] Subido bytes {filename} id={uploaded.get('id')}")
    return {"mode": "drive", "file_id": uploaded.get("id")}

# Public API


def upload_xml_bytes(filename, data: bytes, folder_id: str):
    if SIMULATED:
        return upload_bytes_simulated(filename, data)
    else:
        return upload_bytes_real(filename, data, folder_id)


def list_files_simulated(folder_id: str = None):
    """Lista archivos XML en el directorio local de inbox (modo simulado)."""
    os.makedirs(INBOX, exist_ok=True)
    files = []
    if os.path.exists(INBOX):
        for f in os.listdir(INBOX):
            if f.lower().endswith(".xml"):
                file_path = os.path.join(INBOX, f)
                files.append({
                    "id": f,
                    "name": f,
                    "path": file_path,
                    "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                })
    return files


def list_files_real(folder_id: str = None):
    """Lista archivos XML de una carpeta en Google Drive."""
    try:
        service = _get_drive_service()
        query = "mimeType='text/xml' or mimeType='application/xml'"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        elif FOLDER_INBOX_ID:
            query += f" and '{FOLDER_INBOX_ID}' in parents"
        
        results = service.files().list(
            q=query,
            fields="files(id, name, size, modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = []
        for item in results.get("files", []):
            files.append({
                "id": item["id"],
                "name": item["name"],
                "size": int(item.get("size", 0)),
                "modifiedTime": item.get("modifiedTime", "")
            })
        return files
    except Exception as e:
        logger.error(f"Error al listar archivos de Drive: {e}")
        raise


def download_file_simulated(file_id: str, dest_path: str = None):
    """Descarga un archivo del inbox local (modo simulado)."""
    if not dest_path:
        dest_path = os.path.join(INBOX, file_id)
    else:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    if os.path.exists(file_id):
        shutil.copy(file_id, dest_path)
        logger.info(f"[Drive Simulado] Descargado {file_id} a {dest_path}")
        return dest_path
    elif os.path.exists(os.path.join(INBOX, file_id)):
        source = os.path.join(INBOX, file_id)
        shutil.copy(source, dest_path)
        logger.info(f"[Drive Simulado] Descargado {source} a {dest_path}")
        return dest_path
    else:
        raise FileNotFoundError(f"Archivo no encontrado: {file_id}")


def download_file_real(file_id: str, dest_path: str = None):
    """Descarga un archivo de Google Drive por su ID."""
    try:
        from googleapiclient.http import MediaIoBaseDownload
        import io
        
        service = _get_drive_service()
        
        # Obtener metadatos del archivo
        file_metadata = service.files().get(
            fileId=file_id,
            supportsAllDrives=True
        ).execute()
        
        filename = file_metadata.get("name", f"file_{file_id}.xml")
        
        if not dest_path:
            os.makedirs(INBOX, exist_ok=True)
            dest_path = os.path.join(INBOX, filename)
        else:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # Descargar contenido
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(dest_path, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        logger.info(f"[Drive Real] Descargado {filename} a {dest_path}")
        return dest_path
    except Exception as e:
        logger.error(f"Error al descargar archivo de Drive: {e}")
        raise


def list_drive_files(folder_id: str = None):
    """Lista archivos XML de Drive (simulado o real)."""
    if SIMULATED:
        return list_files_simulated(folder_id)
    else:
        return list_files_real(folder_id)


def download_drive_file(file_id: str, dest_path: str = None):
    """Descarga un archivo de Drive (simulado o real)."""
    if SIMULATED:
        return download_file_simulated(file_id, dest_path)
    else:
        return download_file_real(file_id, dest_path)
def sync_drive_to_local():
    """
    Sincroniza archivos XML desde Google Drive hacia data/drive_inbox.
    Utiliza list_drive_files() y download_drive_file() (simulado o real).
    """
    try:
        os.makedirs(INBOX, exist_ok=True)

        archivos_drive = list_drive_files(FOLDER_INBOX_ID)
        logger.info(f"[Drive Sync] Archivos detectados en Drive: {len(archivos_drive)}")

        nuevos = 0

        for item in archivos_drive:
            nombre = item["name"]

            # Solo XML
            if not nombre.lower().endswith(".xml"):
                continue

            destino = os.path.join(INBOX, nombre)

            # Evitar duplicados
            if os.path.exists(destino):
                logger.info(f"[Drive Sync] Ya existe → {nombre}")
                continue

            logger.info(f"[Drive Sync] ⬇️ Descargando {nombre} ...")

            download_drive_file(item["id"], destino)
            nuevos += 1

        logger.info(f"[Drive Sync] Sincronización completada. Nuevos archivos: {nuevos}")
        return nuevos

    except Exception as e:
        logger.error(f"[Drive Sync] ❌ Error: {e}", exc_info=True)
        return 0
