from sqlalchemy import create_engine

engine = create_engine("mysql+mysqlconnector://root:@localhost/recetario_db")
try:
    connection = engine.connect()
    print("Conectado a MySQL correctamente")
except Exception as e:
    print("Error al conectar:", e)
