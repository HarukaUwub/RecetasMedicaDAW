#!/usr/bin/env python3
"""
Script de Demostración - Integración de Aplicaciones con Google Drive
Este script demuestra el flujo completo de sincronización de pacientes.
"""

import os
import sys
import time
from datetime import datetime

def print_header(title):
    """Imprime un encabezado formateado."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_step(step, description):
    """Imprime un paso del proceso."""
    print(f"\n[{step}] {description}")
    print("-" * 40)

def demo_web_app():
    """Demuestra la funcionalidad de la aplicación web."""
    print_header("DEMOSTRACIÓN: APLICACIÓN WEB")
    
    try:
        from web_app_simulator import WebAppSimulator
        
        print_step("1", "Inicializando aplicación web simulada...")
        app = WebAppSimulator()
        
        print_step("2", "Agregando paciente de prueba...")
        resultado = app.agregar_paciente(
            nombre="Juan Pérez García",
            edad="35",
            genero="M",
            correo="juan.perez@email.com",
            telefono="333-123-4567",
            calle="Av. Revolución 123",
            colonia="Centro",
            ciudad="Guadalajara",
            estado="Jalisco",
            cp="44100"
        )
        
        if resultado["success"]:
            print(f"✅ Paciente agregado exitosamente:")
            print(f"   - ID: {resultado['paciente_id']}")
            print(f"   - XML: {resultado['filename']}")
            print(f"   - Drive ID: {resultado['file_id']}")
        else:
            print(f"❌ Error: {resultado['message']}")
            return False
        
        print_step("3", "Actualizando paciente...")
        resultado_update = app.actualizar_paciente(
            resultado['paciente_id'],
            telefono="333-987-6543",
            ciudad="Zapopan"
        )
        
        if resultado_update["success"]:
            print(f"✅ Paciente actualizado:")
            print(f"   - XML: {resultado_update['filename']}")
        else:
            print(f"❌ Error en actualización: {resultado_update['message']}")
        
        print_step("4", "Listando pacientes en BD Web...")
        pacientes = app.listar_pacientes()
        print(f"Total de pacientes en BD Web: {len(pacientes)}")
        for p in pacientes:
            print(f"   - ID: {p['id']} | {p['nombre']} | {p['correo']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en demostración web: {e}")
        return False

def demo_local_app():
    """Demuestra la funcionalidad de la aplicación local."""
    print_header("DEMOSTRACIÓN: APLICACIÓN LOCAL")
    
    try:
        from sync_pacientes import PacienteSyncManager
        
        print_step("1", "Inicializando sincronizador local...")
        sync_manager = PacienteSyncManager()
        
        print_step("2", "Obteniendo estadísticas iniciales...")
        stats_inicial = sync_manager.obtener_estadisticas_sync()
        print(f"   - Pacientes locales: {stats_inicial['total_pacientes_local']}")
        print(f"   - Archivos procesados: {stats_inicial['archivos_procesados']}")
        print(f"   - Archivos con error: {stats_inicial['archivos_error']}")
        
        print_step("3", "Ejecutando sincronización...")
        resultado_sync = sync_manager.sincronizar_pacientes()
        
        print(f"✅ Sincronización completada:")
        print(f"   - Archivos procesados: {resultado_sync['procesados']}")
        print(f"   - Pacientes actualizados: {resultado_sync['actualizados']}")
        print(f"   - Errores: {resultado_sync['errores']}")
        
        for detalle in resultado_sync.get('detalles', []):
            print(f"   {detalle}")
        
        print_step("4", "Obteniendo estadísticas finales...")
        stats_final = sync_manager.obtener_estadisticas_sync()
        print(f"   - Pacientes locales: {stats_final['total_pacientes_local']}")
        print(f"   - Archivos procesados: {stats_final['archivos_procesados']}")
        print(f"   - Archivos con error: {stats_final['archivos_error']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en demostración local: {e}")
        return False

def demo_xml_validation():
    """Demuestra la validación de XML."""
    print_header("DEMOSTRACIÓN: VALIDACIÓN XML")
    
    try:
        from paciente_xml_utils import generar_xml_paciente, validar_xml_con_xsd, parse_xml_paciente
        
        print_step("1", "Generando XML de paciente...")
        paciente_data = {
            "id": 999,
            "nombre": "María González",
            "edad": 28,
            "genero": "F",
            "correo": "maria.gonzalez@email.com",
            "telefono": "555-123-4567",
            "calle": "Calle Principal 456",
            "colonia": "Residencial",
            "ciudad": "Tijuana",
            "estado": "Baja California",
            "cp": "22000"
        }
        
        xml_bytes, filename = generar_xml_paciente(paciente_data, "ALTA")
        print(f"✅ XML generado: {filename}")
        
        print_step("2", "Validando XML contra XSD...")
        es_valido, errores = validar_xml_con_xsd(xml_bytes)
        
        if es_valido:
            print("✅ XML válido según esquema XSD")
        else:
            print(f"❌ XML inválido: {errores}")
        
        print_step("3", "Parseando XML...")
        datos_parseados = parse_xml_paciente(xml_bytes)
        
        if datos_parseados:
            print("✅ XML parseado exitosamente:")
            for campo, valor in datos_parseados.items():
                if campo != "checksum":
                    print(f"   - {campo}: {valor}")
        else:
            print("❌ Error parseando XML")
        
        print_step("4", "Mostrando contenido XML...")
        print("Contenido del XML generado:")
        print("-" * 40)
        print(xml_bytes.decode('utf-8'))
        
        return True
        
    except Exception as e:
        print(f"❌ Error en demostración XML: {e}")
        return False

def demo_drive_operations():
    """Demuestra las operaciones con Google Drive."""
    print_header("DEMOSTRACIÓN: OPERACIONES GOOGLE DRIVE")
    
    try:
        from drive_utils import (
            get_drive_service, list_pacientes_pendientes, 
            get_or_create_pacientes_folder
        )
        
        print_step("1", "Conectando a Google Drive...")
        service = get_drive_service()
        
        if service:
            print("✅ Conectado a Google Drive")
        else:
            print("⚠️ Drive no disponible, usando modo local")
        
        print_step("2", "Configurando carpetas de pacientes...")
        folder_info = get_or_create_pacientes_folder(service)
        
        if folder_info:
            if isinstance(folder_info, tuple):
                main_id, subfolder_ids = folder_info
                print(f"✅ Carpetas configuradas:")
                print(f"   - Principal: {main_id}")
                print(f"   - Pendientes: {subfolder_ids.get('pendientes', 'N/A')}")
                print(f"   - Procesados: {subfolder_ids.get('procesados', 'N/A')}")
                print(f"   - Errores: {subfolder_ids.get('errores', 'N/A')}")
            else:
                print(f"✅ Carpeta principal: {folder_info}")
        else:
            print("⚠️ No se pudieron configurar carpetas")
        
        print_step("3", "Listando archivos pendientes...")
        archivos_pendientes = list_pacientes_pendientes(service)
        
        print(f"Archivos pendientes encontrados: {len(archivos_pendientes)}")
        for archivo in archivos_pendientes:
            print(f"   - {archivo['name']} (ID: {archivo['id']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en demostración Drive: {e}")
        return False

def demo_error_handling():
    """Demuestra el manejo de errores."""
    print_header("DEMOSTRACIÓN: MANEJO DE ERRORES")
    
    try:
        from paciente_xml_utils import validar_xml_con_xsd
        
        print_step("1", "Probando XML inválido...")
        xml_invalido = b"""<?xml version="1.0" encoding="UTF-8"?>
<paciente>
    <id>123</id>
    <nombre>Test</nombre>
    <edad>abc</edad>
    <genero>X</genero>
</paciente>"""
        
        es_valido, errores = validar_xml_con_xsd(xml_invalido)
        
        if not es_valido:
            print("✅ Error detectado correctamente:")
            for error in errores:
                print(f"   - {error}")
        else:
            print("❌ Error no detectado")
        
        print_step("2", "Probando archivo XSD inexistente...")
        es_valido, errores = validar_xml_con_xsd(xml_invalido, "archivo_inexistente.xsd")
        
        if not es_valido:
            print("✅ Error de archivo XSD detectado:")
            for error in errores:
                print(f"   - {error}")
        
        print_step("3", "Probando XML malformado...")
        xml_malformado = b"<paciente><id>123</paciente>"
        
        es_valido, errores = validar_xml_con_xsd(xml_malformado)
        
        if not es_valido:
            print("✅ XML malformado detectado:")
            for error in errores:
                print(f"   - {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en demostración de errores: {e}")
        return False

def main():
    """Función principal de demostración."""
    print_header("DEMOSTRACIÓN COMPLETA - INTEGRACIÓN DE APLICACIONES")
    print("Este script demuestra el flujo completo de sincronización")
    print("de pacientes entre aplicaciones usando Google Drive como puente.")
    
    demos = [
        ("Validación XML", demo_xml_validation),
        ("Operaciones Drive", demo_drive_operations),
        ("Manejo de Errores", demo_error_handling),
        ("Aplicación Web", demo_web_app),
        ("Aplicación Local", demo_local_app),
    ]
    
    resultados = {}
    
    for nombre, funcion in demos:
        print(f"\n[EJECUTANDO] {nombre}")
        try:
            resultado = funcion()
            resultados[nombre] = resultado
            if resultado:
                print(f"[OK] {nombre}: Completado exitosamente")
            else:
                print(f"[ERROR] {nombre}: Falló")
        except Exception as e:
            print(f"[ERROR] {nombre}: Error - {e}")
            resultados[nombre] = False
        
        time.sleep(1)  # Pausa entre demostraciones
    
    # Resumen final
    print_header("RESUMEN DE DEMOSTRACIÓN")
    
    exitosos = sum(1 for r in resultados.values() if r)
    total = len(resultados)
    
    print(f"Demostraciones completadas: {exitosos}/{total}")
    print("\nDetalles:")
    for nombre, resultado in resultados.items():
        estado = "[OK] Exitoso" if resultado else "[ERROR] Falló"
        print(f"   - {nombre}: {estado}")
    
    if exitosos == total:
        print("\n[EXITO] ¡Todas las demostraciones completadas exitosamente!")
        print("\nEl sistema de integración está funcionando correctamente.")
        print("Puedes usar:")
        print("   - web_app_simulator.py para simular la aplicación web")
        print("   - main_with_sync.py para la aplicación de escritorio")
        print("   - sync_pacientes.py para sincronización manual")
    else:
        print(f"\n[ADVERTENCIA] {total - exitosos} demostraciones fallaron.")
        print("Revisa los errores anteriores para más detalles.")

if __name__ == "__main__":
    main()
