from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from database.base import Base
from datetime import datetime

class PacienteLocal(Base):
    __tablename__ = "pacientes_local"
    id = Column(String, primary_key=True)
    nombre = Column(String)
    apellido = Column(String, nullable=True)
    fecha_nacimiento = Column(String, nullable=True)
    sexo = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    correo = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MedicoLocal(Base):
    __tablename__ = "medicos_local"
    id = Column(String, primary_key=True)
    nombre = Column(String)
    cedula = Column(String, nullable=True)
    correo = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RecetaLocal(Base):
    __tablename__ = "recetas_local"
    id_receta = Column(String, primary_key=True)
    paciente_id = Column(String, ForeignKey("pacientes_local.id"))
    medico_id = Column(String, ForeignKey("medicos_local.id"))
    diagnostico = Column(Text, nullable=True)
    indicaciones = Column(Text, nullable=True)
    xml_path = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    checksum = Column(String, nullable=True)
    fecha_emision = Column(DateTime, nullable=True)
    origen = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MedicamentoLocal(Base):
    __tablename__ = "medicamentos_local"
    id = Column(Integer, primary_key=True, autoincrement=True)
    receta_id = Column(String, ForeignKey("recetas_local.id_receta"))
    nombre = Column(String)
    dosis = Column(String, nullable=True)
    frecuencia = Column(String, nullable=True)
    duracion = Column(String, nullable=True)

