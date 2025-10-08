# sync_job.py
from apscheduler.schedulers.background import BackgroundScheduler
from drive_utils import get_drive_service, list_files_in_folder, download_file
from xml_utils import parsear_xml_receta
from database import Session, insert_receta

def sync_drive_folder(folder_id):
    service = get_drive_service()
    files = list_files_in_folder(service, folder_id)
    session = Session()
    for f in files:
        data_bytes = download_file(service, f['id'])
        receta_obj = parsear_xml_receta(data_bytes)
        insert_receta(session, receta_obj)

        receta_for_db = {
            "paciente": {"nombre": receta_obj['paciente']['nombre'], "edad": receta_obj['paciente'].get('edad'), "genero": receta_obj['paciente'].get('genero'), "correo": None},
            "medico": {"nombre": receta_obj['medico']['nombre'], "cedula": receta_obj['medico'].get('cedula'), "especialidad": None},
            "diagnostico": receta_obj.get('diagnostico'),
            "medicamentos": receta_obj.get('medicamentos', [])
        }
        try:
            insert_receta(session, receta_for_db)
        except Exception as e:
            print("Error insertando:", e)

def start_scheduler(folder_id):
    sched = BackgroundScheduler()
    sched.add_job(lambda: sync_drive_folder(folder_id), 'interval', minutes=15)
    sched.start()
