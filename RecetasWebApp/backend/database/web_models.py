# backend/database/web_models.py  (añadir o editar)
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text
from database.base import Base
from datetime import datetime

class PacienteWeb(Base):
    __tablename__ = "pacientes_web"
    id = Column(String, primary_key=True)
    nombre = Column(String)
    apellido = Column(String)
    fecha_nacimiento = Column(String)
    sexo = Column(String)
    telefono = Column(String, nullable=True)
    correo = Column(String, nullable=True)

class MedicoWeb(Base):
    __tablename__ = "medicos_web"
    id = Column(String, primary_key=True)
    nombre = Column(String)
    cedula = Column(String)
    correo = Column(String, nullable=True)

class RecetaWeb(Base):
    __tablename__ = "recetas_web"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_receta = Column(String, unique=True, index=True)
    paciente_id = Column(String, ForeignKey("pacientes_web.id"))
    medico_id = Column(String, ForeignKey("medicos_web.id"))
    diagnostico = Column(Text)
    indicaciones = Column(Text, nullable=True)
    xml_path = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    pdf_password = Column(String, nullable=True)
    checksum = Column(String, nullable=True)
    fecha_emision = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent = Column(Boolean, default=False)

class MedicamentoWeb(Base):
    __tablename__ = "medicamentos_web"
    id = Column(Integer, primary_key=True, autoincrement=True)
    receta_id = Column(Integer, ForeignKey("recetas_web.id"))
    nombre = Column(String)
    dosis = Column(String, nullable=True)
    frecuencia = Column(String, nullable=True)
    duracion = Column(String, nullable=True)

# NUEVO: Usuario para auth
class UserWeb(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
