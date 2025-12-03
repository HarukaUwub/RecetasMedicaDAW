import os
import hashlib
from datetime import datetime
from io import BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
os.makedirs("data_local", exist_ok=True)

# ====================== Servicio de Drive ======================
def get_drive_service():
    """Crea el servicio de Drive; devuelve None si falla."""
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')
    CREDS_PATH = os.path.join(BASE_DIR, 'credentials.json')

    try:
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        print("[ADVERTENCIA] No se pudo conectar a Drive:", e)
        return None

# ====================== Carpeta ======================
def get_or_create_folder(service, folder_name, parent_id=None):
    """Obtiene o crea una carpeta en Drive; devuelve folder_id o None."""
    if not service:
        return None
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get("files", [])
        if folders:
            return folders[0]["id"]
        # Crear carpeta si no existe
        file_metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            file_metadata["parents"] = [parent_id]
        folder = service.files().create(body=file_metadata, fields="id").execute()
        return folder.get("id")
    except Exception as e:
        print("[ERROR] Error en get_or_create_folder:", e)
        return None

# ====================== Subir archivo ======================
def upload_file_bytes(service, file_bytes, filename, folder_id=None):
    """Sube archivo a Drive o lo guarda localmente si falla."""
    if not service:
        print(f"[INFO] Guardando localmente: {filename}")
        os.makedirs("data_local", exist_ok=True)
        with open(os.path.join("data_local", filename), "wb") as f:
            f.write(file_bytes)
        return None

    try:
        media = MediaIoBaseUpload(BytesIO(file_bytes), mimetype="application/xml")
        file_metadata = {"name": filename}
        if folder_id:
            file_metadata["parents"] = [folder_id]
        f = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        print(f"[OK] Archivo subido a Drive: {filename}")
        return f.get("id")
    except Exception as e:
        print("[ERROR] Error subiendo a Drive, guardando localmente:", e)
        os.makedirs("data_local", exist_ok=True)
        with open(os.path.join("data_local", filename), "wb") as f:
            f.write(file_bytes)
        return None

# ====================== Listar archivos ======================
def list_files_in_folder(service, folder_id):
    if not service:
        return []
    try:
        results = service.files().list(q=f"'{folder_id}' in parents and trashed=false",
                                       fields="files(id, name, modifiedTime)").execute()
        return results.get("files", [])
    except Exception as e:
        print("⚠ Error list_files_in_folder:", e)
        return []

# ====================== Descargar archivo ======================
def download_file_bytes(service, file_id, filename=None):
    if not service:
        local_path = os.path.join("data_local", filename) if filename else None
        if local_path and os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        return None
    try:
        request = service.files().get_media(fileId=file_id)
        file_bytes = BytesIO()
        downloader = MediaIoBaseDownload(file_bytes, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return file_bytes.getvalue()
    except Exception as e:
        print(f"⚠ Error descargando {filename}: {e}")
        return None

# ====================== Carpetas específicas para pacientes ======================
def get_or_create_pacientes_folder(service):
    """Obtiene o crea las subcarpetas para pacientes en Drive; devuelve un dict de folder_ids."""
    if not service:
        return None
    
    subfolder_ids = {}
    
    try:
        # 1. Encontrar o crear la carpeta principal "PacientesSync"
        main_folder_name = "PacientesSync"
        query_main = f"name='{main_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results_main = service.files().list(q=query_main, fields="files(id, name)").execute()
        main_folders = results_main.get("files", [])
        
        if main_folders:
            main_folder_id = main_folders[0]["id"]
        else:
            file_metadata = {"name": main_folder_name, "mimeType": "application/vnd.google-apps.folder"}
            folder = service.files().create(body=file_metadata, fields="id").execute()
            main_folder_id = folder.get("id")
            
        # 2. Encontrar o crear las subcarpetas dentro de "PacientesSync"
        subfolder_names = ["pendientes", "procesados", "errores"]
        
        for subfolder_name in subfolder_names:
            query_sub = f"name='{subfolder_name}' and '{main_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results_sub = service.files().list(q=query_sub, fields="files(id, name)").execute()
            sub_folders = results_sub.get("files", [])
            
            if sub_folders:
                subfolder_ids[subfolder_name] = sub_folders[0]["id"]
            else:
                subfolder_metadata = {
                    "name": subfolder_name,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [main_folder_id]
                }
                subfolder = service.files().create(body=subfolder_metadata, fields="id").execute()
                subfolder_ids[subfolder_name] = subfolder.get("id")
        
        return subfolder_ids # Always return the dictionary of subfolder IDs
    
    except Exception as e:
        print("⚠ Error en get_or_create_pacientes_folder:", e)
        return None

# ====================== Subir XML de paciente ======================
def upload_paciente_xml(service, xml_bytes, filename):
    """Sube XML de paciente a la carpeta pendientes."""
    if not service:
        print(f"[INFO] Guardando localmente: {filename}")
        os.makedirs("data_local/pacientes", exist_ok=True)
        with open(os.path.join("data_local/pacientes", filename), "wb") as f:
            f.write(xml_bytes)
        return None
    
    try:
        subfolder_ids = get_or_create_pacientes_folder(service)
        pendientes_folder_id = subfolder_ids.get("pendientes")
        
        if pendientes_folder_id:
            return upload_file_bytes(service, xml_bytes, filename, pendientes_folder_id)
        else:
            # Fallback if pendientes folder not found (should not happen with refactored get_or_create)
            print(f"⚠ No se encontró la carpeta 'pendientes', subiendo a la raíz de PacientesSync o a Drive por defecto.")
            return upload_file_bytes(service, xml_bytes, filename) # Uploads to root or default Drive
    except Exception as e:
        print(f"⚠ Error subiendo XML de paciente: {e}")
        return upload_file_bytes(service, xml_bytes, filename)

# ====================== Listar XMLs de pacientes pendientes ======================
def list_pacientes_pendientes(service):
    """Lista archivos XML de pacientes pendientes de procesar."""
    if not service:
        # Fallback a archivos locales
        local_files = []
        pacientes_dir = "data_local/pacientes"
        if os.path.exists(pacientes_dir):
            for filename in os.listdir(pacientes_dir):
                if filename.endswith('.xml') and not filename.endswith('_OK.xml') and not filename.endswith('_ERR.xml'):
                    local_files.append({
                        'id': f"local_{filename}",
                        'name': filename,
                        'modifiedTime': datetime.now().isoformat()
                    })
        return local_files
    
    try:
        subfolder_ids = get_or_create_pacientes_folder(service)
        
        if subfolder_ids and "pendientes" in subfolder_ids:
            pendientes_folder_id = subfolder_ids["pendientes"]
            return list_files_in_folder(service, pendientes_folder_id)
        else:
            print("⚠ No se encontró la carpeta 'pendientes' para listar archivos.")
            return []
    except Exception as e:
        print(f"⚠ Error listando pacientes pendientes: {e}")
        return []

# ====================== Mover archivo entre carpetas ======================
def move_file_to_folder(service, file_id, target_folder_id, new_name=None):
    """Mueve un archivo a otra carpeta en Drive."""
    if not service:
        return False
    
    try:
        # Obtener información del archivo actual
        file_info = service.files().get(fileId=file_id, fields="parents").execute()
        previous_parents = ",".join(file_info.get("parents"))
        
        # Mover archivo
        file_body = {}
        if new_name:
            file_body["name"] = new_name
        
        service.files().update(
            fileId=file_id,
            addParents=target_folder_id,
            removeParents=previous_parents,
            body=file_body,
            fields="id, parents"
        ).execute()
        
        return True
    except Exception as e:
        print(f"⚠ Error moviendo archivo: {e}")
        return False

# ====================== Marcar archivo como procesado ======================
def mark_file_as_processed(service, file_id, filename, success=True):
    """Marca un archivo como procesado moviéndolo a la carpeta correspondiente."""
    if not service:
        # Fallback local: renombrar archivo
        try:
            pacientes_dir = "data_local/pacientes"
            old_path = os.path.join(pacientes_dir, filename)
            if os.path.exists(old_path):
                suffix = "_OK.xml" if success else "_ERR.xml"
                new_name = filename.replace('.xml', f'{suffix}.xml')
                new_path = os.path.join(pacientes_dir, new_name)
                os.rename(old_path, new_path)
                return True
        except Exception as e:
            print(f"⚠ Error renombrando archivo local: {e}")
        return False
    
    try:
        subfolder_ids = get_or_create_pacientes_folder(service)
        
        if subfolder_ids:
            target_folder_id = subfolder_ids.get("procesados" if success else "errores")
            
            if target_folder_id:
                suffix = "_OK" if success else "_ERR"
                new_name = filename.replace('.xml', f'{suffix}.xml')
                return move_file_to_folder(service, file_id, target_folder_id, new_name)
        
        print(f"⚠ No se encontró la carpeta destino para mover el archivo {filename}.")
        return False
    except Exception as e:
        print(f"⚠ Error marcando archivo como procesado: {e}")
        return False

# ====================== Utilidades de checksum ======================
def calculate_checksum(data):
    """Calcula el checksum MD5 de los datos."""
    return hashlib.md5(data).hexdigest()

def verify_checksum(data, expected_checksum):
    """Verifica que el checksum de los datos coincida con el esperado."""
    return calculate_checksum(data) == expected_checksum
