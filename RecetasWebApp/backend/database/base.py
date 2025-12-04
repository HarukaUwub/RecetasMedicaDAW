import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings
from core.logger import logger

# Crear directorio de datos si no existe
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))

os.makedirs(DATA_DIR, exist_ok=True)

# URLs de bases de datos
WEB_DB_PATH = os.path.join(DATA_DIR, "web.db")
LOCAL_DB_PATH = os.path.join(DATA_DIR, "local.db")

WEB_DATABASE_URL = f"sqlite:///{WEB_DB_PATH}"
LOCAL_DATABASE_URL = f"sqlite:///{LOCAL_DB_PATH}"

logger.info(f"[DB] Web DB: {WEB_DATABASE_URL}")
logger.info(f"[DB] Local DB: {LOCAL_DATABASE_URL}")

# Motor para BD web
engine = create_engine(
    WEB_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Motor para BD local
local_engine = create_engine(
    LOCAL_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
LocalSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=local_engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_local_db():
    db = LocalSessionLocal()
    try:
        yield db
    finally:
        db.close()
