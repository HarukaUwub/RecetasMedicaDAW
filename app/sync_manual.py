#!/usr/bin/env python3
"""
Script para sincronizar pacientes desde Drive
"""

from sync_pacientes import PacienteSyncManager

def main():
    print("Iniciando sincronizacion de pacientes...")
    
    manager = PacienteSyncManager()
    resultado = manager.sincronizar_pacientes()
    
    print("Sincronizacion completada:")
    print(f"- Archivos procesados: {resultado['procesados']}")
    print(f"- Pacientes actualizados: {resultado['actualizados']}")
    print(f"- Errores: {resultado['errores']}")
    
    print("\nDetalles:")
    for detalle in resultado.get('detalles', []):
        # Limpiar caracteres Unicode problemáticos
        detalle_limpio = detalle.replace('✅', '[OK]').replace('❌', '[ERROR]')
        print(f"  {detalle_limpio}")
    
    # Verificar pacientes locales después de sincronización
    stats = manager.obtener_estadisticas_sync()
    print(f"\nEstadisticas finales:")
    print(f"- Total pacientes locales: {stats['total_pacientes_local']}")
    print(f"- Archivos procesados: {stats['archivos_procesados']}")
    print(f"- Archivos con error: {stats['archivos_error']}")

if __name__ == "__main__":
    main()
