# backend/scripts/create_admin.py
import os, sys
# Ruta al directorio raíz del proyecto
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

# Agregar rutas al PYTHONPATH
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, BACKEND_DIR)
from core.auth import get_password_hash
from database.base import SessionLocal, Base, engine
from database.web_models import UserWeb

def create_admin(username, password, full_name=None, email=None):
    db = SessionLocal()
    exists = db.query(UserWeb).filter(UserWeb.username == username).first()
    if exists:
        print("Usuario ya existe")
        return
    user = UserWeb(username=username, hashed_password=get_password_hash(password), full_name=full_name, email=email)
    db.add(user)
    db.commit()
    print("Usuario creado:", username)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--name", default=None)
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    create_admin(args.username, args.password, args.name, args.email)
