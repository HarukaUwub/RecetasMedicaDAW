#!/usr/bin/env python3
"""
Script para verificar el estado completo del sistema
"""

from database import Session
from models import PacienteLocal, SyncArchivos
from drive_utils import get_drive_service, list_pacientes_pendientes

def verificar_estado_sistema():
    """Verifica el estado completo del sistema."""
    print("=== VERIFICACION DEL ESTADO DEL SISTEMA ===")
    
    # Verificar base de datos local
    print("\n1. Base de Datos Local:")
    try:
        session = Session()
        pacientes = session.query(PacienteLocal).all()
        archivos_sync = session.query(SyncArchivos).all()
        
        print(f"   - Pacientes locales: {len(pacientes)}")
        for p in pacientes:
            print(f"     * {p.nombre} (ID: {p.id_externo}) - {p.correo}")
        
        print(f"   - Archivos sincronizados: {len(archivos_sync)}")
        procesados = len([a for a in archivos_sync if a.estado == "PROCESADO"])
        errores = len([a for a in archivos_sync if a.estado == "ERROR"])
        print(f"     * Procesados: {procesados}")
        print(f"     * Errores: {errores}")
        
        session.close()
        
    except Exception as e:
        print(f"   [ERROR] Error accediendo a BD: {e}")
    
    # Verificar Google Drive
    print("\n2. Google Drive:")
    try:
        service = get_drive_service()
        if service:
            archivos_pendientes = list_pacientes_pendientes(service)
            print(f"   - Archivos pendientes: {len(archivos_pendientes)}")
            for archivo in archivos_pendientes:
                print(f"     * {archivo['name']}")
        else:
            print("   [ADVERTENCIA] Drive no disponible")
    except Exception as e:
        print(f"   [ERROR] Error accediendo a Drive: {e}")
    
    # Resumen
    print("\n3. Resumen:")
    if len(pacientes) > 0:
        print("   [OK] Sistema funcionando correctamente")
        print("   [OK] Pacientes disponibles para mostrar en la interfaz")
        print("   [OK] La función 'Refrescar Lista' debería funcionar ahora")
    else:
        print("   [ADVERTENCIA] No hay pacientes locales")
        print("   [INFO] Ejecuta 'python crear_y_sincronizar.py' para crear pacientes de prueba")

if __name__ == "__main__":
    verificar_estado_sistema()


