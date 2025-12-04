from services.xml_generator import generar_receta_xml
import json

data = {
    "paciente": {"id": "P001"},
    "medico": {"id": "M001", "nombre": "Dr. Test", "cedula": "12345"},
    "diagnostico": "Gripe",
    "medicamentos": [
        {"nombre": "Paracetamol", "dosis": "500mg", "frecuencia": "Cada 8 horas"}
    ],
    "indications": "Descanso",
    "metadatos": {"id_receta": "R001"}
}

xml = generar_receta_xml(data)
print(xml)
