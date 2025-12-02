import os
from dotenv import load_dotenv

print("--- Verificando variables de entorno ---")

# Cargar el archivo .env desde el directorio actual
load_dotenv()

db_pass = os.getenv("DB_PASS")

print(f"La contraseña de la base de datos que Python ve es: '{db_pass}'")
print("----------------------------------------")