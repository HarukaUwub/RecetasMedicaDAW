# listar_recetas.py
from database import Session
from models import Receta
session = Session()
for r in session.query(Receta).all():
    print(r.id, r.diagnostico, r.fecha, r.paciente.nombre, r.medico.nombre)
