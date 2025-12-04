# backend/scripts/init_db.py
"""
Inicializa/crea las tablas definidas en backend/database/*.py
Ejecutar: python backend/scripts/init_db.py
"""
import os
import sys


# Ruta al directorio raíz del proyecto
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

# Agregar rutas al PYTHONPATH
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, BACKEND_DIR)

# --- IMPORTS CORRECTOS (desde backend/) ---
from backend.database.base import Base, engine, local_engine
from backend.database.local_models import *  # noqa: F401
from backend.database.web_models import *  # noqa: F401
from backend.core.logger import logger



def init_web_db():
    """Crea todas las tablas en la BD web."""
    try:
        logger.info("[DB WEB] Creando tablas...")
        Base.metadata.create_all(bind=engine)

        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"[DB WEB] ✅ Tablas: {tables}")
        return True
    except Exception as e:
        logger.error(f"[DB WEB] ❌ Error: {e}", exc_info=True)
        return False


def init_local_db():
    """Crea todas las tablas en la BD local."""
    try:
        logger.info("[DB LOCAL] Creando tablas...")
        Base.metadata.create_all(bind=local_engine)

        from sqlalchemy import inspect
        inspector = inspect(local_engine)
        tables = inspector.get_table_names()
        logger.info(f"[DB LOCAL] ✅ Tablas: {tables}")
        return True
    except Exception as e:
        logger.error(f"[DB LOCAL] ❌ Error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("INICIALIZANDO BASES DE DATOS")
    print("=" * 50)

    web_ok = init_web_db()
    local_ok = init_local_db()

    print("=" * 50)
    if web_ok and local_ok:
        print("✅ ÉXITO: Todas las BDs inicializadas")
        sys.exit(0)
    else:
        print("❌ ERROR: Falló la inicialización")
        sys.exit(1)
