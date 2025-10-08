# database.py
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Base, Paciente, Medico, Receta, Medicamento

# Configura tu conexión a MySQL (XAMPP)
engine = create_engine(
    "mysql+pymysql://root:@localhost/recetario_db",
    echo=True
)


Session = sessionmaker(bind=engine)

def init_db():
    print("→ Iniciando verificación de tablas...")

    try:
        with engine.connect() as conn:
            print("✔ Conexión establecida con la base de datos.")
            inspector = inspect(conn)
            existing_tables = inspector.get_table_names()
            print(f"Tablas detectadas: {existing_tables}")

        for table_name, table_obj in Base.metadata.tables.items():
            if table_name not in existing_tables:
                print(f"⚙ Creando tabla: {table_name}")
                table_obj.create(engine)
            else:
                print(f"✔ Tabla existente: {table_name}")
    except Exception as e:
        print("❌ Error durante la inspección o creación:", e)
        Base.metadata.create_all(engine)
        print("✔ Todas las tablas creadas manualmente.")


def insert_receta(session, receta_obj):
    """
    Inserta una receta en la base de datos.
    Si el paciente o médico ya existen, se reutilizan.
    """
    # --- Paciente ---
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
        session.flush()  # Para obtener paciente.id

    # --- Médico ---
    medico_data = receta_obj['medico']
    medico = session.query(Medico).filter_by(cedula_profesional=medico_data.get('cedula')).first()
    if not medico:
        medico = Medico(
            nombre=medico_data['nombre'],
            cedula_profesional=medico_data.get('cedula'),
            especialidad=medico_data.get('especialidad')
        )
        session.add(medico)
        session.flush()  # Para obtener medico.id

    # --- Receta ---
    receta = Receta(
        id_paciente=paciente.id,
        id_medico=medico.id,
        diagnostico=receta_obj.get('diagnostico'),
        fecha=datetime.now()
    )
    session.add(receta)
    session.flush()  # Para obtener receta.id

    # --- Medicamentos ---
    for m in receta_obj.get('medicamentos', []):
        med = Medicamento(
            id_receta=receta.id,
            nombre=m['nombre'],
            dosis=m.get('dosis'),
            frecuencia=m.get('frecuencia')
        )
        session.add(med)

    # --- Guardar cambios ---
    session.commit()
    return receta.id
