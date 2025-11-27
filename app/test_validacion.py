import os
import logging
from xml_utils import validar_receta_xml

# --- Configuración de logging ---
LOG_FILE = 'test_validacion.log'
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# --- Archivos de prueba ---
XSD_PATH = 'receta.xsd'
TEST_FILES = [
    'receta_valida.xml',
    'receta_invalida.xml'
]

def run_tests():
    """
    Ejecuta las pruebas de validación de XML.
    """
    logging.info("--- INICIANDO PRUEBAS DE VALIDACIÓN DE RECETAS XML ---")
    
    if not os.path.exists(XSD_PATH):
        logging.error(f"No se encontró el archivo XSD en '{XSD_PATH}'. Abortando pruebas.")
        return

    for filename in TEST_FILES:
        logging.info(f"--- Procesando archivo: {filename} ---")
        
        if not os.path.exists(filename):
            logging.error(f"El archivo de prueba '{filename}' no existe.")
            continue
            
        with open(filename, 'rb') as f:
            xml_content = f.read()
            
        es_valido, errores = validar_receta_xml(xml_content, XSD_PATH)
        
        if es_valido:
            logging.info(f"Archivo '{filename}' es VÁLIDO y fue aceptado.")
            logging.info(f"Acción tomada: Receta '{filename}' procesada correctamente.")
        else:
            error_str = "\n".join(errores)
            logging.error(f"Falló la validación del archivo '{filename}'")
            for error in errores:
                logging.error(f"  Motivo: {error}")
            logging.warning(f"Acción tomada: Receta '{filename}' rechazada, no se procesará.")

    logging.info("--- PRUEBAS DE VALIDACIÓN FINALIZADAS ---")

if __name__ == "__main__":
    run_tests()
