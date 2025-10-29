#!/usr/bin/env python3
"""
Script para procesar archivos XML locales cuando no hay conexión
"""

import os
from database import Session
from models import PacienteLocal, SyncArchivos
from paciente_xml_utils import parse_xml_paciente, validar_xml_con_xsd
from datetime import datetime

def procesar_archivos_locales():
    """Procesa archivos XML locales cuando no hay conexión."""
    print("=== PROCESANDO ARCHIVOS XML LOCALES ===")
    
    # Buscar archivos XML en data_local
    archivos_locales = []
    data_local_dir = "data_local"
    
    if os.path.exists(data_local_dir):
        for archivo in os.listdir(data_local_dir):
            if archivo.endswith('.xml') and not archivo.endswith('_OK.xml') and not archivo.endswith('_ERR.xml'):
                archivos_locales.append(os.path.join(data_local_dir, archivo))
    
    print(f"Archivos XML locales encontrados: {len(archivos_locales)}")
    
    if not archivos_locales:
        print("No hay archivos XML locales para procesar")
        return
    
    session = Session()
    procesados = 0
    errores = 0
    
    try:
        for archivo_path in archivos_locales:
            archivo_name = os.path.basename(archivo_path)
            print(f"\nProcesando: {archivo_name}")
            
            try:
                # Leer archivo XML
                with open(archivo_path, 'rb') as f:
                    xml_bytes = f.read()
                
                # Validar XML
                es_valido, errores_xml = validar_xml_con_xsd(xml_bytes)
                if not es_valido:
                    print(f"[ERROR] XML inválido: {errores_xml}")
                    errores += 1
                    continue
                
                # Parsear XML
                paciente_data = parse_xml_paciente(xml_bytes)
                if not paciente_data:
                    print(f"[ERROR] No se pudieron extraer datos del XML")
                    errores += 1
                    continue
                
                # Verificar si ya existe
                id_externo = paciente_data.get("id")
                if not id_externo:
                    print(f"[ERROR] ID externo no encontrado")
                    errores += 1
                    continue
                
                # Buscar paciente existente
                paciente_existente = session.query(PacienteLocal).filter_by(id_externo=id_externo).first()
                
                if paciente_existente:
                    # Actualizar
                    paciente_existente.nombre = paciente_data.get("nombre", "")
                    paciente_existente.edad = paciente_data.get("edad")
                    paciente_existente.genero = paciente_data.get("genero", "")
                    paciente_existente.correo = paciente_data.get("correo", "")
                    paciente_existente.telefono = paciente_data.get("telefono", "")
                    paciente_existente.calle = paciente_data.get("calle", "")
                    paciente_existente.colonia = paciente_data.get("colonia", "")
                    paciente_existente.ciudad = paciente_data.get("ciudad", "")
                    paciente_existente.estado = paciente_data.get("estado", "")
                    paciente_existente.cp = paciente_data.get("cp", "")
                    paciente_existente.synced_at = datetime.now()
                    print(f"[OK] Actualizado: {paciente_data.get('nombre')}")
                else:
                    # Insertar nuevo
                    nuevo_paciente = PacienteLocal(
                        id_externo=id_externo,
                        nombre=paciente_data.get("nombre", ""),
                        edad=paciente_data.get("edad"),
                        genero=paciente_data.get("genero", ""),
                        correo=paciente_data.get("correo", ""),
                        telefono=paciente_data.get("telefono", ""),
                        calle=paciente_data.get("calle", ""),
                        colonia=paciente_data.get("colonia", ""),
                        ciudad=paciente_data.get("ciudad", ""),
                        estado=paciente_data.get("estado", ""),
                        cp=paciente_data.get("cp", ""),
                        synced_at=datetime.now()
                    )
                    session.add(nuevo_paciente)
                    print(f"[OK] Insertado: {paciente_data.get('nombre')}")
                
                # Registrar como procesado
                registro = SyncArchivos(
                    nombre_archivo=archivo_name,
                    fecha_procesado=datetime.now(),
                    estado="PROCESADO",
                    checksum="local"
                )
                session.add(registro)
                
                # Renombrar archivo como procesado
                nuevo_nombre = archivo_name.replace('.xml', '_OK.xml')
                nuevo_path = os.path.join(data_local_dir, nuevo_nombre)
                os.rename(archivo_path, nuevo_path)
                print(f"[OK] Archivo renombrado a: {nuevo_nombre}")
                
                procesados += 1
                
            except Exception as e:
                print(f"[ERROR] Error procesando {archivo_name}: {e}")
                errores += 1
                
                # Renombrar archivo como error
                nuevo_nombre = archivo_name.replace('.xml', '_ERR.xml')
                nuevo_path = os.path.join(data_local_dir, nuevo_nombre)
                try:
                    os.rename(archivo_path, nuevo_path)
                except:
                    pass
        
        session.commit()
        
        print(f"\n=== RESUMEN ===")
        print(f"Archivos procesados: {procesados}")
        print(f"Errores: {errores}")
        
        # Verificar pacientes locales
        total_pacientes = session.query(PacienteLocal).count()
        print(f"Total pacientes locales: {total_pacientes}")
        
        print("\n[EXITO] Archivos locales procesados correctamente!")
        print("Ahora puedes abrir main_with_sync.py y hacer clic en 'Refrescar Lista' para ver los pacientes.")
        
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Error general: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    procesar_archivos_locales()


