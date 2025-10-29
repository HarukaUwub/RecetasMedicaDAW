import os
from drive_utils import upload_file_bytes, get_service, get_or_create_folder
from xml_utils import parse_xml_receta

# --- DB opcional ---
DB_AVAILABLE = False
try:
    from database import Session, insert_receta
    DB_AVAILABLE = True
except Exception as e:
    print("⚠ Base de datos no disponible:", e)
    DB_AVAILABLE = False

OFFLINE_FOLDER = "data_local"

def sincronizar_offline(window):
    """Sube a Drive y DB los archivos locales pendientes."""
    print("🔄 Ejecutando sincronización offline...")

    if not os.path.exists(OFFLINE_FOLDER):
        print("✅ No hay archivos locales.")
        return

    # Inicializar Drive
    service = get_service()
    if not service:
        print("⚠ Aún sin conexión a Drive.")
        return

    folder_id = get_or_create_folder(service, "RecetasMedicas")

    for file in os.listdir(OFFLINE_FOLDER):
        if not file.endswith(".xml"):
            continue

        path = os.path.join(OFFLINE_FOLDER, file)
        try:
            with open(path, "rb") as f:
                xml_data = f.read()

            upload_file_bytes(service, xml_data, file, folder_id)
            print(f"✅ Sincronizado con Drive: {file}")

            if DB_AVAILABLE:
                try:
                    data = parse_xml_receta(xml_data)
                    session = Session()
                    insert_receta(session, data)
                    session.commit()
                    session.close()
                    print(f"✅ Sincronizado con DB: {file}")
                except Exception as e:
                    print(f"⚠ Error guardando en DB durante sincronización: {e}")

            # Eliminar archivo local solo si se subió correctamente
            os.remove(path)
        except Exception as e:
            print(f"⚠ No se pudo sincronizar {file}: {e}")
