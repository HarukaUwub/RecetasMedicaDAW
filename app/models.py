from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
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
    telefono = Column(String(20))
    calle = Column(String(100))
    colonia = Column(String(100))
    ciudad = Column(String(100))
    estado = Column(String(100))
    cp = Column(String(10))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    recetas = relationship("Receta", back_populates="paciente")

# Tabla para pacientes en BD Local (con id_externo para sincronización)
class PacienteLocal(Base):
    __tablename__ = "pacientes_local"
    id = Column(Integer, primary_key=True)
    id_externo = Column(Integer)  # ID del paciente en BD Web (opcional para recetas offline)
    nombre = Column(String(100), nullable=False)
    edad = Column(Integer)
    genero = Column(String(1))
    correo = Column(String(100))
    telefono = Column(String(20))
    calle = Column(String(100))
    colonia = Column(String(100))
    ciudad = Column(String(100))
    estado = Column(String(100))
    cp = Column(String(10))
    synced_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# Tabla de control para archivos procesados
class SyncArchivos(Base):
    __tablename__ = "sync_archivos"
    id = Column(Integer, primary_key=True)
    nombre_archivo = Column(String(200), nullable=False)
    fecha_procesado = Column(DateTime, default=datetime.now)
    estado = Column(String(20), nullable=False)  # PROCESADO, ERROR
    detalle_error = Column(Text)
    checksum = Column(String(64))

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

# ==================== MODELOS LOCALES (OFFLINE) ====================

class MedicoLocal(Base):
    """Modelo para médicos almacenados localmente (offline)"""
    __tablename__ = "medicos_local"
    id = Column(Integer, primary_key=True)
    id_externo = Column(Integer)  # ID del médico en la BD web (opcional para recetas offline)
    nombre = Column(String(100), nullable=False)
    cedula_profesional = Column(String(20), unique=True)
    especialidad = Column(String(100))
    synced_at = Column(DateTime)
    
    recetas_local = relationship("RecetaLocal", back_populates="medico_local")

class RecetaLocal(Base):
    """Modelo para recetas almacenadas localmente (offline)"""
    __tablename__ = "recetas_local"
    id = Column(Integer, primary_key=True)
    id_externo = Column(Integer)  # ID de la receta en la BD web
    id_paciente_local = Column(Integer, ForeignKey("pacientes_local.id"), nullable=False)
    id_medico_local = Column(Integer, ForeignKey("medicos_local.id"), nullable=False)
    diagnostico = Column(String(500))
    fecha = Column(DateTime, default=datetime.now)
    synced_at = Column(DateTime)
    drive_file_id = Column(String(255))  # ID del archivo en Google Drive
    xml_filename = Column(String(255))  # Nombre del archivo XML local
    
    paciente_local = relationship("PacienteLocal", back_populates="recetas_local")
    medico_local = relationship("MedicoLocal", back_populates="recetas_local")
    medicamentos_local = relationship("MedicamentoLocal", back_populates="receta_local", cascade="all, delete-orphan")

class MedicamentoLocal(Base):
    """Modelo para medicamentos almacenados localmente (offline)"""
    __tablename__ = "medicamentos_local"
    id = Column(Integer, primary_key=True)
    id_receta_local = Column(Integer, ForeignKey("recetas_local.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    dosis = Column(String(100))
    frecuencia = Column(String(100))
    
    receta_local = relationship("RecetaLocal", back_populates="medicamentos_local")

# Agregar relación a PacienteLocal
PacienteLocal.recetas_local = relationship("RecetaLocal", back_populates="paciente_local")
