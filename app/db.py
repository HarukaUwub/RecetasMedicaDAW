import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Paciente, Medico, Receta, Medicamento
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER","root")
DB_PASSWORD = os.getenv("DB_PASSWORD","")
DB_HOST = os.getenv("DB_HOST","localhost")
DB_PORT = os.getenv("DB_PORT","3306")
DB_NAME = os.getenv("DB_NAME","recetas_db")

MYSQL_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
SQLITE_URL = "sqlite:///recetas_fallback.db"

engine = None
Session = None

def init_db():
    global engine, Session
    try:
        engine = create_engine(MYSQL_URL, echo=True)
        conn = engine.connect(); conn.close()
        print("✔ Conectado a MySQL")
    except Exception as e:
        print(f"❌ MySQL no disponible: {e}")
        engine = create_engine(SQLITE_URL, echo=True)
        print("⚙ Usando SQLite fallback")

    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    print("✔ Tablas verificadas/creadas")

def insert_receta(session, receta_obj):
    paciente_data = receta_obj['paciente']
    paciente = session.query(Paciente).filter_by(correo=paciente_data.get('correo')).first()
    if not paciente:
        paciente = Paciente(
            nombre=paciente_data['nombre'],
            edad=paciente_data.get('edad'),
            genero=paciente_data.get('genero'),
            correo=paciente_data.get('correo')
        )
        session.add(paciente)
        session.flush()

    medico_data = receta_obj['medico']
    medico = session.query(Medico).filter_by(cedula_profesional=medico_data.get('cedula')).first()
    if not medico:
        medico = Medico(
            nombre=medico_data['nombre'],
            cedula_profesional=medico_data.get('cedula'),
            especialidad=medico_data.get('especialidad')
        )
        session.add(medico)
        session.flush()

    receta = Receta(
        id_paciente=paciente.id,
        id_medico=medico.id,
        diagnostico=receta_obj.get('diagnostico')
    )
    session.add(receta)
    session.flush()

    for m in receta_obj.get('medicamentos', []):
        med = Medicamento(
            id_receta=receta.id,
            nombre=m['nombre'],
            dosis=m.get('dosis'),
            frecuencia=m.get('frecuencia')
        )
        session.add(med)

    session.commit()
    return receta.id
