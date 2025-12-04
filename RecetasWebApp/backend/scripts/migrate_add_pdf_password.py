import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "web.db"))

def migrate():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Intentar agregar columna
        cursor.execute("ALTER TABLE recetas_web ADD COLUMN pdf_password VARCHAR(255) NULL;")
        conn.commit()
        print("✅ Columna pdf_password agregada correctamente")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("✅ La columna pdf_password ya existe")
        else:
            print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()