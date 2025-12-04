# backend/web/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from core.auth import authenticate_user, create_access_token, get_db, get_password_hash
from database.web_models import UserWeb

router = APIRouter(prefix="/auth", tags=["auth"])

security = HTTPBearer()

@router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    access_token = create_access_token(subject=user.username)

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/create_user")
def create_user(payload: dict, db: Session = Depends(get_db)):
    username = payload.get("username")
    password = payload.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="username y password requeridos")

    exists = db.query(UserWeb).filter(UserWeb.username == username).first()
    if exists:
        raise HTTPException(status_code=400, detail="Usuario ya existe")

    hashed = get_password_hash(password)
    user = UserWeb(
        username=username,
        hashed_password=hashed,
        full_name=payload.get("full_name"),
        email=payload.get("email"),
    )
    db.add(user)
    db.commit()

    return {"msg": "usuario creado"}
