#!/usr/bin/env python3
"""
Script para crear una RECETA desde la aplicación y sincronizarla.
Simula el flujo completo: Web App -> Drive -> App Local.
"""

import os
from .xml_utils import generar_xml_receta
from .drive_utils import get_drive_service, get_or_create_folder, upload_file_bytes
from .sync_recetas import RecetaSyncManager

def crear_y_sincronizar_receta():
    """Crea una receta, la sube a Drive y la sincroniza."""
    print("=== Creando y Sincronizando Receta ===")

    # 1. Datos de prueba para la receta
    receta_data = {
        "paciente": {
            "nombre": "Laura Nuñez",
            "edad": 55,
            "genero": "F",
            "correo": "laura.nunez@email.com"
        },
        "medico": {
            "nombre": "Dr. Alberto Solis",
            "cedula": "87654321",
            "especialidad": "Cardiología"
        },
        "diagnostico": "Control de colesterol alto.",
        "medicamentos": [
            {"nombre": "Atorvastatina", "dosis": "20mg", "frecuencia": "1 por la noche"}
        ]
    }
    print(f"Receta creada para: {receta_data['paciente']['nombre']}")

    # 2. Generar XML de la receta
    print("\nGenerando XML de la receta...")
    try:
        xml_bytes, filename = generar_xml_receta(receta_data)
        print(f"[OK] XML generado: {filename}")
    except Exception as e:
        print(f"[ERROR] No se pudo generar el XML: {e}")
        return

    # 3. Subir a Google Drive
    print("\nSubiendo a Google Drive...")
    service = get_drive_service()
    if service:
        # Usaremos una estructura de carpetas para recetas
        main_folder_id = get_or_create_folder(service, "RecetasSync")
        pendientes_folder_id = get_or_create_folder(service, "pendientes", parent_id=main_folder_id)
        file_id = upload_file_bytes(service, xml_bytes, filename, pendientes_folder_id)
        if file_id:
            print(f"[OK] Archivo subido a Drive con ID: {file_id}")
        else:
            print("[ERROR] Falló la subida a Drive.")
    else:
        print("[ADVERTENCIA] Drive no disponible. No se pudo subir el archivo.")

    # 4. Sincronizar en la app local
    print("\nIniciando sincronización local de recetas...")
    manager = RecetaSyncManager()
    procesados, errores = manager.sincronizar_desde_drive()

    print("\n[ÉXITO] Flujo de receta completado.")
    print(f"Resultados: {procesados} recetas procesadas, {errores} errores.")
    print("Ahora puedes ver la receta en la pestaña 'Recetas Offline' de la app de escritorio.")

if __name__ == "__main__":
    crear_y_sincronizar_receta()