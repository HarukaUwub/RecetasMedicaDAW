import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Base
from datetime import datetime

def init_db():
    """Inicializa la BD MySQL si hay conexión, si no usa SQLite local."""
    print("-> Iniciando verificacion de tablas...")
    try:
        engine = create_engine("mysql+pymysql://root:@localhost/recetario_db", echo=False)
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        print("OK Conectado a MySQL")
    except Exception as e:
        print(f"ADVERTENCIA No se pudo conectar a MySQL: {e}")
        print("-> Usando base de datos SQLite local (offline).")
        os.makedirs("data_local", exist_ok=True)  # crear carpeta local
        engine = create_engine("sqlite:///data_local/recetario_offline.db", echo=False)


    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session

# Crear instancia global de Session para importación
Session = init_db()

# Función para insertar receta (compatibilidad con código existente)
def insert_receta(session, data):
    """Inserta una receta en la base de datos."""
    from models import Paciente, Medico, Receta, Medicamento
    
    # Buscar o crear paciente
    paciente = session.query(Paciente).filter_by(correo=data["paciente"]["correo"]).first()
    if not paciente:
        paciente = Paciente(
            nombre=data["paciente"]["nombre"],
            edad=data["paciente"]["edad"],
            genero=data["paciente"]["genero"],
            correo=data["paciente"]["correo"]
        )
        session.add(paciente)
        session.flush()
    
    # Buscar o crear médico
    medico = session.query(Medico).filter_by(cedula_profesional=data["medico"]["cedula"]).first()
    if not medico:
        medico = Medico(
            nombre=data["medico"]["nombre"],
            cedula_profesional=data["medico"]["cedula"],
            especialidad=data["medico"]["especialidad"]
        )
        session.add(medico)
        session.flush()
    
    # Crear receta
    receta = Receta(
        id_paciente=paciente.id,
        id_medico=medico.id,
        diagnostico=data["diagnostico"]
    )
    session.add(receta)
    session.flush()
    
    # Agregar medicamentos
    for med_data in data["medicamentos"]:
        medicamento = Medicamento(
            id_receta=receta.id,
            nombre=med_data["nombre"],
            dosis=med_data["dosis"],
            frecuencia=med_data["frecuencia"]
        )
        session.add(medicamento)
    
    return receta
