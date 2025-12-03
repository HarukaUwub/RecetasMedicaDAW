#!/usr/bin/env python3
"""
Script para crear un paciente desde la aplicación y sincronizarlo
"""

from .paciente_xml_utils import crear_paciente_desde_formulario, generar_y_subir_paciente_xml
from .drive_utils import get_drive_service
from .sync_pacientes import PacienteSyncManager

def crear_y_sincronizar_paciente():
    """Crea un paciente y lo sincroniza."""
    print("=== Creando y Sincronizando Paciente ===")
    
    # Crear paciente con datos de prueba
    paciente_data = crear_paciente_desde_formulario(
        nombre="Carlos Rodriguez",
        edad="42",
        genero="M",
        correo="carlos.rodriguez@email.com",
        telefono="555-987-6543",
        calle="Calle Secundaria 789",
        colonia="Norte",
        ciudad="Tijuana",
        estado="Baja California",
        cp="22010"
    )
    
    print(f"Paciente creado con ID: {paciente_data['id']}")
    print(f"Nombre: {paciente_data['nombre']}")
    print(f"Correo: {paciente_data['correo']}")
    
    # Conectar a Drive
    service = get_drive_service()
    
    # Generar y subir XML
    print("\nGenerando XML y subiendo a Drive...")
    file_id, filename = generar_y_subir_paciente_xml(service, paciente_data, "ALTA")
    
    if file_id:
        print(f"[OK] XML subido exitosamente:")
        print(f"- Archivo: {filename}")
        print(f"- Drive ID: {file_id}")
    else:
        print(f"[OK] XML guardado localmente: {filename}")
    
    # Sincronizar
    print("\nSincronizando paciente...")
    manager = PacienteSyncManager()
    resultado = manager.sincronizar_pacientes()
    
    print(f"Sincronizacion completada:")
    print(f"- Archivos procesados: {resultado['procesados']}")
    print(f"- Pacientes actualizados: {resultado['actualizados']}")
    print(f"- Errores: {resultado['errores']}")
    
    # Verificar pacientes locales
    stats = manager.obtener_estadisticas_sync()
    print(f"\nEstadisticas finales:")
    print(f"- Total pacientes locales: {stats['total_pacientes_local']}")
    
    print("\n[EXITO] Paciente creado y sincronizado correctamente!")
    print("Ahora puedes abrir main_with_sync.py y hacer clic en 'Refrescar Lista' para ver el paciente.")

if __name__ == "__main__":
    crear_y_sincronizar_paciente()


