from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Paciente(Base):
    __tablename__ = "pacientes"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    edad = Column(Integer)
    genero = Column(String(1))
    correo = Column(String(100), unique=True)

    recetas = relationship("Receta", back_populates="paciente")

class Medico(Base):
    __tablename__ = "medicos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    cedula_profesional = Column(String(50), unique=True, nullable=False)
    especialidad = Column(String(100))

    recetas = relationship("Receta", back_populates="medico")

class Receta(Base):
    __tablename__ = "recetas"
    id = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    id_medico= Column(Integer, ForeignKey("medicos.id"), nullable=False)
    diagnostico = Column(String(500))
    fecha = Column(DateTime, default=datetime.now)

    paciente = relationship("Paciente", back_populates="recetas")
    medico = relationship("Medico", back_populates="recetas")
    medicamentos = relationship("Medicamento", back_populates="receta", cascade="all, delete-orphan")

class Medicamento(Base):
    __tablename__ = "medicamentos"
    id = Column(Integer, primary_key=True)
    id_receta = Column(Integer, ForeignKey("recetas.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    dosis = Column(String(50))
    frecuencia = Column(String(100))

    receta = relationship("Receta", back_populates="medicamentos")
