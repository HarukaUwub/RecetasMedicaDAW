import os
import logging
import shutil
import time
from xml_utils import validar_receta_xml, parse_xml_to_dict
from database import Session, insert_receta

# --- Configuración de Logging ---
# Creamos un logger específico para el job para no mezclarlo con otros logs.
log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, 'sync_job.log')

# Configuración del logger
sync_logger = logging.getLogger('SyncJobLogger')
sync_logger.setLevel(logging.INFO)
handler = logging.FileHandler(log_file_path)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Evitar que se añadan múltiples handlers si se importa varias veces
if not sync_logger.handlers:
    sync_logger.addHandler(handler)


class SyncJob:
    """
    Clase que encapsula la lógica para procesar archivos XML de recetas
    desde una carpeta de entrada, validarlos y moverlos según el resultado.
    """

    def __init__(self, base_path):
        """
        Inicializa el job con las rutas de las carpetas simuladas.
        """
        self.base_path = base_path
        self.nuevos_dir = os.path.join(base_path, 'nuevos')
        self.procesados_dir = os.path.join(base_path, 'procesados')
        self.errores_dir = os.path.join(base_path, 'errores')
        self.xsd_path = os.path.join(os.path.dirname(__file__), 'receta.xsd')

        # Asegurarse de que las carpetas existan
        os.makedirs(self.nuevos_dir, exist_ok=True)
        os.makedirs(self.procesados_dir, exist_ok=True)
        os.makedirs(self.errores_dir, exist_ok=True)

        sync_logger.info("SyncJob inicializado. Rutas configuradas.")
        sync_logger.info(f" - Directorio de nuevos XML: {self.nuevos_dir}")
        sync_logger.info(f" - Directorio de XML procesados: {self.procesados_dir}")
        sync_logger.info(f" - Directorio de XML con errores: {self.errores_dir}")

    def _procesar_archivo(self, filename):
        """
        Lógica para procesar un único archivo XML.
        """
        filepath = os.path.join(self.nuevos_dir, filename)
        sync_logger.info(f"Procesando archivo: {filename}")

        try:
            with open(filepath, 'rb') as f:
                xml_content = f.read()

            # 1. Validar contra el XSD
            es_valido, errores_validacion = validar_receta_xml(xml_content, self.xsd_path)

            if not es_valido:
                # Si no es válido, se mueve a la carpeta de errores
                error_msg = f"Archivo '{filename}' inválido según XSD. Errores: {errores_validacion}"
                sync_logger.error(error_msg)
                shutil.move(filepath, os.path.join(self.errores_dir, filename))
                sync_logger.info(f"Archivo '{filename}' movido a '{self.errores_dir}'")
                return

            sync_logger.info(f"Archivo '{filename}' validado con éxito contra XSD.")

            # 2. Parsear el XML a un diccionario
            datos_receta = parse_xml_to_dict(xml_content)

            # 3. Insertar en la base de datos
            session = Session()
            try:
                sync_logger.info(f"Insertando datos de '{filename}' en la base de datos...")
                insert_receta(session, datos_receta)
                session.commit()
                sync_logger.info(f"Datos de '{filename}' insertados y confirmados en la BD.")
            except Exception as db_error:
                session.rollback()
                error_msg = f"Error de base de datos al procesar '{filename}': {db_error}"
                sync_logger.error(error_msg)
                shutil.move(filepath, os.path.join(self.errores_dir, filename))
                sync_logger.warning(f"Archivo '{filename}' movido a '{self.errores_dir}' por error en BD.")
                return
            finally:
                session.close()

            # 4. Mover a la carpeta de procesados
            shutil.move(filepath, os.path.join(self.procesados_dir, filename))
            sync_logger.info(f"Archivo '{filename}' procesado con éxito y movido a '{self.procesados_dir}'.")

        except FileNotFoundError:
            sync_logger.error(f"El archivo '{filename}' no fue encontrado. Pudo ser movido por otro proceso.")
        except Exception as e:
            # Captura cualquier otro error inesperado durante el procesamiento
            sync_logger.error(f"Error inesperado procesando '{filename}': {e}")
            # Intentar mover a errores si aún existe
            if os.path.exists(filepath):
                shutil.move(filepath, os.path.join(self.errores_dir, filename))
                sync_logger.warning(f"Archivo '{filename}' movido a '{self.errores_dir}' por error inesperado.")

    def run(self):
        """
        Ejecuta una pasada del job, buscando y procesando todos los archivos
        en el directorio 'nuevos'.
        """
        start_time = time.time()
        sync_logger.info("--- INICIANDO EJECUCIÓN DEL JOB DE SINCRONIZACIÓN ---")

        # Listar archivos .xml en el directorio de nuevos
        try:
            archivos_a_procesar = [f for f in os.listdir(self.nuevos_dir) if f.endswith('.xml')]
        except FileNotFoundError:
            sync_logger.error(f"El directorio de entrada '{self.nuevos_dir}' no existe. Abortando.")
            return

        if not archivos_a_procesar:
            sync_logger.info("No se encontraron nuevos archivos XML para procesar.")
        else:
            sync_logger.info(f"Se encontraron {len(archivos_a_procesar)} archivos: {archivos_a_procesar}")
            for filename in archivos_a_procesar:
                self._procesar_archivo(filename)

        end_time = time.time()
        duration = end_time - start_time
        sync_logger.info(f"--- FINALIZADA EJECUCIÓN DEL JOB. Duración: {duration:.2f} segundos. ---")