import logging
import os

def setup_logging():
    """Configura el sistema de logging para todo el proyecto."""
    
    # Crear carpeta de logs si no existe
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')

    # Configurar el logger raíz
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Para ver los logs en la consola también
        ]
    )