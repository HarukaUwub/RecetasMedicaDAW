# backend/scripts/migrate_add_pdf_path.py
"""
Migración: Agrega la columna pdf_path a la tabla recetas_web si no existe.
Ejecutar desde el directorio backend con el venv activado:
  python scripts/migrate_add_pdf_path.py
O ejecutar el SQL directamente:
  sqlite3 web.db < scripts/migrate_add_pdf_path.sql
"""
import os
import sys

# Agregar el directorio backend al path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

try:
    from sqlalchemy import create_engine, text, inspect
    from database.base import engine
    from core.logger import logger
except ImportError as e:
    print(f"Error al importar módulos: {e}")
    print("Asegúrate de estar en el directorio backend y tener el venv activado.")
    print("O ejecuta el SQL directamente: sqlite3 web.db < scripts/migrate_add_pdf_path.sql")
    sys.exit(1)

def migrate():
    """Agrega la columna pdf_path si no existe."""
    try:
        with engine.connect() as conn:
            # Verificar si la columna ya existe
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('recetas_web')]
            
            if 'pdf_path' in columns:
                logger.info("La columna pdf_path ya existe en recetas_web. No se requiere migración.")
                print("✓ La columna pdf_path ya existe. No se requiere migración.")
                return
            
            # Agregar la columna
            logger.info("Agregando columna pdf_path a recetas_web...")
            conn.execute(text("ALTER TABLE recetas_web ADD COLUMN pdf_path VARCHAR"))
            conn.commit()
            logger.info("Columna pdf_path agregada exitosamente.")
            print("✓ Columna pdf_path agregada exitosamente a recetas_web.")
            
    except Exception as e:
        # En SQLite, si la columna ya existe, dará un error específico
        error_msg = str(e).lower()
        if 'duplicate column' in error_msg or 'already exists' in error_msg:
            logger.info("La columna pdf_path ya existe.")
            print("✓ La columna pdf_path ya existe.")
            return
        logger.error(f"Error en migración: {e}")
        print(f"✗ Error en migración: {e}")
        print("\nAlternativa: Ejecuta el SQL directamente:")
        print("  sqlite3 web.db < scripts/migrate_add_pdf_path.sql")
        raise

if __name__ == "__main__":
    migrate()

