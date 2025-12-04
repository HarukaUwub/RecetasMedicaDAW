# backend/core/auth.py
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.config import settings
from core.logger import logger
from database.base import get_db
from database.web_models import UserWeb

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# -------- PASSWORDS -------- #

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# -------- DB DEPENDENCY -------- #
def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

# -------- AUTHENTICATION -------- #

def authenticate_user(db: Session, username: str, password: str):
    """Busca el usuario en la BD y valida su contraseña."""
    user = db.query(UserWeb).filter(UserWeb.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# -------- JWT -------- #

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None):
    """Crea un JWT compatible con tu router (requiere subject)."""
    to_encode = {"sub": subject}

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")

        user = db.query(UserWeb).filter(UserWeb.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")

        return user
    
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


# -------- MODEL -------- #

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
