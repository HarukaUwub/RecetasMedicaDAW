import os
from io import BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PICKLE = "token.pkl"

def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PICKLE, "wb") as token:
            pickle.dump(creds, token)

    service = build("drive", "v3", credentials=creds)
    return service

def get_or_create_folder(service, folder_name="RecetasMedicas"):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    else:
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        folder = service.files().create(body=file_metadata, fields="id").execute()
        return folder.get("id")

def upload_file_bytes(service, file_bytes, filename, folder_id=None):
    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    media = MediaIoBaseUpload(BytesIO(file_bytes), mimetype="text/xml")
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")

def list_files_in_folder(service, folder_id):
    query = f"'{folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name, modifiedTime)").execute()
    return results.get("files", [])

def download_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return fh.getvalue()
def download_file_bytes(service, file_id):
    """Descarga un archivo de Google Drive y devuelve su contenido en bytes."""
    from io import BytesIO
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read()
