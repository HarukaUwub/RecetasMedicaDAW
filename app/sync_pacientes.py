import os
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from .database import init_db, Session
from .models import PacienteLocal, SyncArchivos
from .drive_utils import (
    get_drive_service, list_pacientes_pendientes, download_file_bytes,
    mark_file_as_processed, calculate_checksum, verify_checksum
)
from .paciente_xml_utils import parse_xml_paciente, validar_xml_con_xsd

class PacienteSyncManager:
    """Manejador de sincronización de pacientes entre BD Web y BD Local."""
    
    def __init__(self):
        self.Session = init_db()
        self.service = get_drive_service()
        
    def sincronizar_pacientes(self):
        """
        Sincroniza pacientes desde Drive a BD Local.
        
        Returns:
            dict: Resultado de la sincronización
        """
        resultado = {
            "procesados": 0,
            "actualizados": 0,
            "errores": 0,
            "detalles": []
        }
        
        try:
            # Obtener archivos pendientes
            archivos_pendientes = list_pacientes_pendientes(self.service)
            
            if not archivos_pendientes:
                resultado["detalles"].append("No hay archivos pendientes de procesar")
                return resultado
            
            session = self.Session()
            
            for archivo in archivos_pendientes:
                try:
                    resultado_archivo = self._procesar_archivo_paciente(session, archivo)
                    resultado["procesados"] += 1
                    
                    if resultado_archivo["actualizado"]:
                        resultado["actualizados"] += 1
                    
                    resultado["detalles"].append(f"✅ {archivo['name']}: {resultado_archivo['mensaje']}")
                    
                except Exception as e:
                    resultado["errores"] += 1
                    resultado["detalles"].append(f"❌ {archivo['name']}: Error - {str(e)}")
                    
                    # Marcar archivo como error
                    self._marcar_archivo_error(session, archivo['name'], str(e))
                    mark_file_as_processed(self.service, archivo['id'], archivo['name'], success=False)
            
            session.commit()
            
        except Exception as e:
            resultado["detalles"].append(f"Error general en sincronización: {str(e)}")
            if 'session' in locals():
                session.rollback()
        finally:
            if 'session' in locals():
                session.close()
        
        return resultado
    
    def _procesar_archivo_paciente(self, session, archivo):
        """
        Procesa un archivo XML de paciente individual.
        
        Args:
            session: Sesión de base de datos
            archivo: Información del archivo de Drive
        
        Returns:
            dict: Resultado del procesamiento
        """
        filename = archivo['name']
        file_id = archivo['id']
        
        # Verificar si ya fue procesado
        if self._ya_procesado(session, filename):
            return {"actualizado": False, "mensaje": "Ya procesado anteriormente"}
        
        # Descargar archivo
        xml_bytes = download_file_bytes(self.service, file_id, filename)
        if not xml_bytes:
            raise Exception("No se pudo descargar el archivo")
        
        # Validar XML
        es_valido, errores = validar_xml_con_xsd(xml_bytes)
        if not es_valido:
            raise Exception(f"XML inválido: {', '.join(errores)}")
        
        # Parsear XML
        paciente_data = parse_xml_paciente(xml_bytes)
        if not paciente_data:
            raise Exception("No se pudieron extraer datos del XML")
        
        # Verificar checksum si está presente (opcional)
        if paciente_data.get("checksum"):
            if not verify_checksum(xml_bytes, paciente_data["checksum"]):
                raise Exception(f"Checksum no coincide para {filename}")
        
        # Procesar paciente en BD Local
        actualizado = self._upsert_paciente_local(session, paciente_data)
        
        # Registrar archivo como procesado
        self._registrar_archivo_procesado(session, filename, xml_bytes, True)
        
        # Marcar archivo como procesado en Drive
        mark_file_as_processed(self.service, file_id, filename, success=True)
        
        mensaje = "Actualizado" if actualizado else "Insertado"
        return {"actualizado": actualizado, "mensaje": mensaje}
    
    def _ya_procesado(self, session, filename):
        """Verifica si un archivo ya fue procesado."""
        return session.query(SyncArchivos).filter_by(nombre_archivo=filename).first() is not None
    
    def _upsert_paciente_local(self, session, paciente_data):
        """
        Inserta o actualiza paciente en BD Local.
        
        Args:
            session: Sesión de base de datos
            paciente_data: Datos del paciente
        
        Returns:
            bool: True si se actualizó, False si se insertó
        """
        id_externo = paciente_data.get("id")
        if not id_externo:
            raise Exception("ID externo del paciente no encontrado")
        
        # Buscar paciente existente
        paciente_existente = session.query(PacienteLocal).filter_by(id_externo=id_externo).first()
        
        if paciente_existente:
            # Actualizar paciente existente
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
            paciente_existente.updated_at = datetime.now()
            
            return True
        else:
            # Insertar nuevo paciente
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
                synced_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session.add(nuevo_paciente)
            return False
    
    def _registrar_archivo_procesado(self, session, filename, xml_bytes, success):
        """Registra archivo como procesado en la tabla de control."""
        checksum = calculate_checksum(xml_bytes)
        
        registro = SyncArchivos(
            nombre_archivo=filename,
            fecha_procesado=datetime.now(),
            estado="PROCESADO" if success else "ERROR",
            checksum=checksum
        )
        
        session.add(registro)
    
    def _marcar_archivo_error(self, session, filename, error_detail):
        """Marca archivo como error en la tabla de control."""
        registro = SyncArchivos(
            nombre_archivo=filename,
            fecha_procesado=datetime.now(),
            estado="ERROR",
            detalle_error=error_detail
        )
        
        session.add(registro)
    
    def obtener_estadisticas_sync(self):
        """Obtiene estadísticas de sincronización."""
        session = self.Session()
        try:
            total_pacientes = session.query(PacienteLocal).count()
            archivos_procesados = session.query(SyncArchivos).filter_by(estado="PROCESADO").count()
            archivos_error = session.query(SyncArchivos).filter_by(estado="ERROR").count()
            
            return {
                "total_pacientes_local": total_pacientes,
                "archivos_procesados": archivos_procesados,
                "archivos_error": archivos_error
            }
        finally:
            session.close()
    
    def limpiar_archivos_procesados(self, dias_antiguedad=30):
        """
        Limpia registros de archivos procesados más antiguos que X días.
        
        Args:
            dias_antiguedad: Días de antigüedad para limpiar
        """
        session = self.Session()
        try:
            fecha_limite = datetime.now() - timedelta(days=dias_antiguedad)
            
            registros_eliminados = session.query(SyncArchivos).filter(
                SyncArchivos.fecha_procesado < fecha_limite
            ).delete()
            
            session.commit()
            return registros_eliminados

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

# Función de conveniencia para sincronización manual
def sincronizar_pacientes_manual():
    """Función para sincronización manual desde interfaz."""
    manager = PacienteSyncManager()
    return manager.sincronizar_pacientes()

# Función para sincronización programada
def sincronizar_pacientes_programada():
    """Función para sincronización programada (JOB)."""
    try:
        manager = PacienteSyncManager()
        resultado = manager.sincronizar_pacientes()
        
        print(f"Sincronización completada:")
        print(f"- Archivos procesados: {resultado['procesados']}")
        print(f"- Pacientes actualizados: {resultado['actualizados']}")
        print(f"- Errores: {resultado['errores']}")
        
        for detalle in resultado['detalles']:
            print(f"  {detalle}")
        
        return resultado
        
    except Exception as e:
        print(f"Error en sincronización programada: {e}")
        return {"error": str(e)}