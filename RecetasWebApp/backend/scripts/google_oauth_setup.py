"""
Script interactivo para obtener el REFRESH TOKEN de Google Drive
usando un credentials.json de tipo "Desktop App".

Uso:
  1) Copia tu credentials.json (de la consola de Google Cloud) a backend/credentials.json
  2) Activa tu venv y ejecuta:

       cd backend
       python scripts/google_oauth_setup.py

  3) Se abrirá el navegador para que inicies sesión y autorices la app.
  4) El script imprimirá:
       - refresh_token
       - client_id
       - client_secret

  5) Copia esos valores en tu archivo .env:

       GOOGLE_DRIVE_CLIENT_ID=...
       GOOGLE_DRIVE_CLIENT_SECRET=...
       GOOGLE_DRIVE_REFRESH_TOKEN=...

  6) Reinicia el backend. A partir de ahí, se usará tu unidad personal de Drive.
"""

import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    credentials_path = os.path.join(base_dir, "credentials.json")

    if not os.path.exists(credentials_path):
        raise SystemExit(
            f"No se encontró credentials.json en: {credentials_path}\n"
            "Copia aquí el archivo descargado de la consola de Google Cloud (tipo Desktop)."
        )

    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n=== Datos obtenidos para .env ===\n")
    print(f"GOOGLE_DRIVE_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_DRIVE_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_DRIVE_REFRESH_TOKEN={creds.refresh_token}")
    print("\nCopia estas líneas en tu archivo .env y reinicia el backend.\n")


if __name__ == "__main__":
    main()




