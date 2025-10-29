#!/usr/bin/env python3
"""
Script para crear una receta de prueba y procesarla
"""

from xml_utils import generar_xml_receta
import os

def crear_receta_prueba():
    """Crea una receta de prueba con datos válidos."""
    
    data = {
        "paciente": {
            "nombre": "María González",
            "edad": 45,
            "genero": "F",
            "correo": "maria.gonzalez@email.com"
        },
        "medico": {
            "nombre": "Dr. Carlos Mendoza",
            "cedula": "12345678",
            "especialidad": "Medicina General"
        },
        "diagnostico": "Hipertensión arterial leve",
        "medicamentos": [
            {
                "nombre": "Losartán",
                "dosis": "50mg",
                "frecuencia": "Una vez al día"
            },
            {
                "nombre": "Hidroclorotiazida",
                "dosis": "25mg", 
                "frecuencia": "Una vez al día"
            }
        ]
    }
    
    # Generar XML
    xml_bytes, filename = generar_xml_receta(data)
    
    # Guardar en carpeta xmls
    os.makedirs("xmls", exist_ok=True)
    xml_path = os.path.join("xmls", filename)
    
    with open(xml_path, 'wb') as f:
        f.write(xml_bytes)
    
    print(f"[OK] Receta de prueba creada: {filename}")
    print(f"[INFO] Archivo guardado en: {xml_path}")
    
    return xml_path

if __name__ == "__main__":
    crear_receta_prueba()


