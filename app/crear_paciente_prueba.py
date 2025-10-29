#!/usr/bin/env python3
"""
Script para crear un paciente de prueba y subirlo a Drive
"""

from paciente_xml_utils import generar_y_subir_paciente_xml
from drive_utils import get_drive_service

def main():
    print("Creando paciente de prueba...")
    
    # Datos del paciente de prueba
    paciente_data = {
        "id": 1001,
        "nombre": "Ana Garcia Lopez",
        "edad": 28,
        "genero": "F",
        "correo": "ana.garcia@email.com",
        "telefono": "555-123-4567",
        "calle": "Av. Principal 123",
        "colonia": "Centro",
        "ciudad": "Guadalajara",
        "estado": "Jalisco",
        "cp": "44100"
    }
    
    # Conectar a Drive
    service = get_drive_service()
    
    # Generar y subir XML
    file_id, filename = generar_y_subir_paciente_xml(service, paciente_data, "ALTA")
    
    if file_id:
        print(f"[OK] Paciente creado y subido exitosamente:")
        print(f"- Archivo: {filename}")
        print(f"- Drive ID: {file_id}")
    else:
        print(f"[OK] Paciente creado localmente:")
        print(f"- Archivo: {filename}")
    
    print("\nAhora puedes sincronizar desde la aplicacion para ver el paciente en la lista local.")

if __name__ == "__main__":
    main()

