import os
import time
import random
from apscheduler.schedulers.blocking import BlockingScheduler
from .job_sync import SyncJob, sync_logger

# --- Configuración ---
DRIVE_SIM_PATH = os.path.join(os.path.dirname(__file__), '..', 'drive_simulation')
INTERVALO_SEGUNDOS = 10  # El JOB se ejecutará cada 10 segundos


def ejecutar_job_sincronizacion():
    """
    Función que será llamada por el planificador (Scheduler).
    Crea una instancia del Job y la ejecuta.
    """
    job = SyncJob(base_path=DRIVE_SIM_PATH)
    job.run()


def simular_creacion_de_xml():
    """
    SIMULACIÓN DEL JOB A (Aplicación Web)
    Esta función crea archivos XML de prueba (válidos e inválidos)
    en la carpeta 'nuevos' para que el JOB B los procese.
    """
    sync_logger.info("[SIMULACIÓN] Creando un nuevo archivo XML de prueba...")

    # Contenido de ejemplo
    xml_valido = f"""<?xml version='1.0' encoding='UTF-8'?>
<receta>
  <paciente><nombre>Paciente-{int(time.time())}</nombre><edad>35</edad><genero>F</genero><correo>paciente.{int(time.time())}@test.com</correo></paciente>
  <medico><nombre>Dr. Simulador</nombre><cedula>987654</cedula><especialidad>General</especialidad></medico>
  <diagnostico>Prueba de Job</diagnostico>
  <medicamentos><medicamento><nombre>Test-Med</nombre><dosis>500 mg</dosis><frecuencia>Cada 8 horas</frecuencia></medicamento></medicamentos>
</receta>"""

    xml_invalido = """<?xml version='1.0' encoding='UTF-8'?>
<receta>
  <paciente><nombre>Paciente Invalido</nombre><edad>50</edad><genero>M</genero><correo>invalido@test.com</correo></paciente>
  <!-- Faltan campos obligatorios -->
</receta>"""

    # Decidir aleatoriamente si crear un archivo válido o inválido
    if random.choice([True, False]):
        contenido = xml_valido
        filename = f"receta_valida_{int(time.time())}.xml"
    else:
        contenido = xml_invalido
        filename = f"receta_invalida_{int(time.time())}.xml"

    filepath = os.path.join(DRIVE_SIM_PATH, 'nuevos', filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(contenido)
    sync_logger.info(f"[SIMULACIÓN] Archivo '{filename}' creado en la carpeta 'nuevos'.")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")
    # JOB B: Tarea principal de recepción y procesamiento
    scheduler.add_job(ejecutar_job_sincronizacion, 'interval', seconds=INTERVALO_SEGUNDOS, id='sync_job')
    # JOB A (Simulado): Tarea que crea archivos nuevos para probar el sistema
    scheduler.add_job(simular_creacion_de_xml, 'interval', seconds=INTERVALO_SEGUNDOS * 2, id='xml_creator_job')

    sync_logger.info(f"Planificador iniciado. El JOB de sincronización se ejecutará cada {INTERVALO_SEGUNDOS} segundos.")
    print(f"Planificador iniciado. Presiona Ctrl+C para detener.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        sync_logger.info("Planificador detenido por el usuario.")
        print("Planificador detenido.")