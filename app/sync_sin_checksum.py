#!/usr/bin/env python3
"""
Script para sincronizar pacientes SIN verificar checksum
"""

from sync_pacientes import PacienteSyncManager
from drive_utils import get_drive_service, list_pacientes_pendientes, download_file_bytes
from paciente_xml_utils import parse_xml_paciente, validar_xml_con_xsd
from database import Session
from models import PacienteLocal, SyncArchivos
from drive_utils import mark_file_as_processed, calculate_checksum

def sincronizar_sin_checksum():
    """Sincroniza pacientes sin verificar checksum."""
    print("Iniciando sincronizacion SIN verificacion de checksum...")
    
    service = get_drive_service()
    archivos_pendientes = list_pacientes_pendientes(service)
    
    print(f"Archivos pendientes encontrados: {len(archivos_pendientes)}")
    
    session = Session()
    procesados = 0
    errores = 0
    
    try:
        for archivo in archivos_pendientes:
            filename = archivo['name']
            file_id = archivo['id']
            
            # Saltar carpetas
            if not filename.endswith('.xml'):
                continue
            
            print(f"Procesando: {filename}")
            
            try:
                # Descargar archivo
                xml_bytes = download_file_bytes(service, file_id, filename)
                if not xml_bytes:
                    print(f"[ERROR] No se pudo descargar: {filename}")
                    errores += 1
                    continue
                
                # Validar XML
                es_valido, errores_xml = validar_xml_con_xsd(xml_bytes)
                if not es_valido:
                    print(f"[ERROR] XML invalido: {filename} - {errores_xml}")
                    errores += 1
                    continue
                
                # Parsear XML
                paciente_data = parse_xml_paciente(xml_bytes)
                if not paciente_data:
                    print(f"[ERROR] No se pudieron extraer datos: {filename}")
                    errores += 1
                    continue
                
                # Procesar paciente
                id_externo = paciente_data.get("id")
                if not id_externo:
                    print(f"[ERROR] ID externo no encontrado: {filename}")
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
                        cp=paciente_data.get("cp", "")
                    )
                    session.add(nuevo_paciente)
                    print(f"[OK] Insertado: {paciente_data.get('nombre')}")
                
                # Registrar como procesado
                checksum = calculate_checksum(xml_bytes)
                registro = SyncArchivos(
                    nombre_archivo=filename,
                    fecha_procesado=datetime.now(),
                    estado="PROCESADO",
                    checksum=checksum
                )
                session.add(registro)
                
                # Marcar archivo como procesado en Drive
                mark_file_as_processed(service, file_id, filename, success=True)
                
                procesados += 1
                
            except Exception as e:
                print(f"[ERROR] Error procesando {filename}: {e}")
                errores += 1
        
        session.commit()
        print(f"\nSincronizacion completada:")
        print(f"- Archivos procesados: {procesados}")
        print(f"- Errores: {errores}")
        
        # Verificar pacientes locales
        total_pacientes = session.query(PacienteLocal).count()
        print(f"- Total pacientes locales: {total_pacientes}")
        
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Error general: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    from datetime import datetime
    sincronizar_sin_checksum()


