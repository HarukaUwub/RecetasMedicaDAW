#!/usr/bin/env python3
"""
Sistema de Sincronización de Recetas
Maneja la sincronización entre archivos XML locales, base de datos local y Google Drive
"""

import os
import hashlib
from datetime import datetime
from .database import Session
from .models import (
    RecetaLocal, MedicoLocal, MedicamentoLocal, PacienteLocal, 
    SyncArchivos, Receta, Medico, Medicamento, Paciente
)
from .xml_utils import parse_xml_receta, generar_xml_receta
from .drive_utils import (
    get_drive_service, get_or_create_folder, upload_file_bytes,
    list_files_in_folder, download_file_bytes, move_file_to_folder
)

class RecetaSyncManager:
    """Gestor de sincronización de recetas."""
    
    def __init__(self):
        self.session = Session()
        self.drive_service = None
        self.xml_folder = "xmls"
        self.pendientes_folder = "RecetasSync/pendientes"
        self.procesados_folder = "RecetasSync/procesados"
        self.errores_folder = "RecetasSync/errores"
        
    def init_drive(self):
        """Inicializa conexión con Google Drive."""
        try:
            self.drive_service = get_drive_service()
            if self.drive_service:
                print("[INFO] Conexión con Google Drive establecida")
                return True
            else:
                print("[ADVERTENCIA] No se pudo conectar a Google Drive")
                return False
        except Exception as e:
            print(f"[ERROR] Error inicializando Drive: {e}")
            return False
    
    def procesar_archivos_xml_locales(self):
        """Procesa archivos XML locales y los guarda en la base de datos local."""
        print("=== PROCESANDO ARCHIVOS XML LOCALES DE RECETAS ===")
        
        if not os.path.exists(self.xml_folder):
            print(f"[INFO] No existe la carpeta {self.xml_folder}")
            return
        
        archivos_xml = []
        for archivo in os.listdir(self.xml_folder):
            if archivo.endswith('.xml') and not archivo.endswith('_OK.xml') and not archivo.endswith('_ERR.xml'):
                archivos_xml.append(os.path.join(self.xml_folder, archivo))
        
        print(f"[INFO] Archivos XML encontrados: {len(archivos_xml)}")
        
        if not archivos_xml:
            print("[INFO] No hay archivos XML para procesar")
            return
        
        procesados = 0
        errores = 0
        
        for archivo_path in archivos_xml:
            archivo_name = os.path.basename(archivo_path)
            print(f"\n[PROCESANDO] {archivo_name}")
            
            try:
                # Leer archivo XML
                with open(archivo_path, 'rb') as f:
                    xml_bytes = f.read()
                
                # Parsear XML
                receta_data = parse_xml_receta(xml_bytes)
                if not receta_data:
                    print(f"[ERROR] No se pudieron extraer datos del XML")
                    errores += 1
                    continue
                
                # Validar que tenga datos mínimos
                if not receta_data.get("paciente", {}).get("nombre") or not receta_data.get("medico", {}).get("nombre"):
                    print(f"[ERROR] XML sin datos mínimos requeridos")
                    errores += 1
                    continue
                
                # Verificar si ya existe
                checksum = self._calculate_checksum(xml_bytes)
                registro_existente = self.session.query(SyncArchivos).filter_by(
                    nombre_archivo=archivo_name
                ).first()
                
                if registro_existente:
                    print(f"[INFO] Archivo ya procesado: {archivo_name}")
                    continue
                
                # Buscar o crear paciente local
                paciente_local = self._buscar_o_crear_paciente_local(receta_data["paciente"])
                
                # Buscar o crear médico local
                medico_local = self._buscar_o_crear_medico_local(receta_data["medico"])
                
                # Crear receta local
                receta_local = RecetaLocal(
                    id_paciente_local=paciente_local.id,
                    id_medico_local=medico_local.id,
                    diagnostico=receta_data.get("diagnostico", ""),
                    fecha=datetime.now(),
                    xml_filename=archivo_name,
                    synced_at=datetime.now()
                )
                self.session.add(receta_local)
                self.session.flush()
                
                # Agregar medicamentos
                for med_data in receta_data.get("medicamentos", []):
                    medicamento_local = MedicamentoLocal(
                        id_receta_local=receta_local.id,
                        nombre=med_data.get("nombre", ""),
                        dosis=med_data.get("dosis", ""),
                        frecuencia=med_data.get("frecuencia", "")
                    )
                    self.session.add(medicamento_local)
                
                # Registrar como procesado
                registro = SyncArchivos(
                    nombre_archivo=archivo_name,
                    fecha_procesado=datetime.now(),
                    estado="PROCESADO",
                    checksum=checksum
                )
                self.session.add(registro)
                
                # Renombrar archivo como procesado
                nuevo_nombre = archivo_name.replace('.xml', '_OK.xml')
                nuevo_path = os.path.join(self.xml_folder, nuevo_nombre)
                os.rename(archivo_path, nuevo_path)
                
                print(f"[OK] Receta procesada: {receta_data['paciente']['nombre']}")
                procesados += 1
                
            except Exception as e:
                print(f"[ERROR] Error procesando {archivo_name}: {e}")
                errores += 1
                
                # Renombrar archivo como error
                nuevo_nombre = archivo_name.replace('.xml', '_ERR.xml')
                nuevo_path = os.path.join(self.xml_folder, nuevo_nombre)
                try:
                    os.rename(archivo_path, nuevo_path)
                except:
                    pass
        
        self.session.commit()
        
        print(f"\n=== RESUMEN ===")
        print(f"Recetas procesadas: {procesados}")
        print(f"Errores: {errores}")
        
        return procesados, errores
    
    def sincronizar_con_drive(self):
        """Sincroniza recetas locales con Google Drive."""
        print("=== SINCRONIZANDO RECETAS CON GOOGLE DRIVE ===")
        
        if not self.init_drive():
            print("[ADVERTENCIA] No se puede sincronizar con Drive - modo offline")
            return
        
        # Obtener recetas locales no sincronizadas
        recetas_pendientes = self.session.query(RecetaLocal).filter(
            RecetaLocal.drive_file_id.is_(None)
        ).all()
        
        print(f"[INFO] Recetas pendientes de sincronización: {len(recetas_pendientes)}")
        
        sincronizadas = 0
        errores = 0
        
        for receta_local in recetas_pendientes:
            try:
                # Generar XML desde datos locales
                xml_data = self._generar_xml_desde_local(receta_local)
                
                # Subir a Drive
                filename = f"receta_local_{receta_local.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
                
                # Crear carpetas si no existen
                folder_id = get_or_create_folder(self.drive_service, "RecetasMedicas")
                pendientes_id = get_or_create_folder(self.drive_service, self.pendientes_folder)
                
                # Subir archivo
                file_id = upload_file_bytes(
                    self.drive_service, 
                    xml_data, 
                    filename, 
                    folder_id=pendientes_id
                )
                
                # Actualizar receta local
                receta_local.drive_file_id = file_id
                receta_local.synced_at = datetime.now()
                
                print(f"[OK] Receta sincronizada: {receta_local.paciente_local.nombre}")
                sincronizadas += 1
                
            except Exception as e:
                print(f"[ERROR] Error sincronizando receta {receta_local.id}: {e}")
                errores += 1
        
        self.session.commit()
        
        print(f"\n=== RESUMEN SINCRONIZACIÓN ===")
        print(f"Recetas sincronizadas: {sincronizadas}")
        print(f"Errores: {errores}")
        
        return sincronizadas, errores
    
    def sincronizar_desde_drive(self):
        """Sincroniza recetas desde Google Drive a la base de datos local."""
        print("=== SINCRONIZANDO RECETAS DESDE GOOGLE DRIVE ===")
        
        if not self.init_drive():
            print("[ADVERTENCIA] No se puede sincronizar desde Drive - modo offline")
            return
        
        try:
            # Listar archivos en carpeta pendientes
            main_folder_name, subfolder_name = self.pendientes_folder.split('/')
            main_folder_id = get_or_create_folder(self.drive_service, main_folder_name)
            
            if not main_folder_id:
                raise Exception(f"No se pudo encontrar o crear la carpeta principal '{main_folder_name}'")
            pendientes_folder_id = get_or_create_folder(self.drive_service, subfolder_name, parent_id=main_folder_id)
            files = list_files_in_folder(self.drive_service, pendientes_folder_id)
            
            print(f"[INFO] Archivos encontrados en Drive: {len(files)}")
            
            procesados = 0
            errores = 0
            
            for file_info in files:
                filename = file_info['name']
                file_id = file_info['id']
                
                print(f"\n[PROCESANDO] {filename}")
                
                try:
                    # Verificar si ya fue procesado
                    registro_existente = self.session.query(SyncArchivos).filter_by(
                        nombre_archivo=filename
                    ).first()
                    
                    if registro_existente:
                        print(f"[INFO] Archivo ya procesado: {filename}")
                        continue
                    
                    # Descargar archivo
                    xml_bytes = download_file_bytes(self.drive_service, file_id)
                    
                    # Parsear XML
                    receta_data = parse_xml_receta(xml_bytes)
                    if not receta_data:
                        print(f"[ERROR] No se pudieron extraer datos del XML")
                        errores += 1
                        continue
                    
                    # Buscar o crear paciente local
                    paciente_local = self._buscar_o_crear_paciente_local(receta_data["paciente"])
                    
                    # Buscar o crear médico local
                    medico_local = self._buscar_o_crear_medico_local(receta_data["medico"])
                    
                    # Crear receta local
                    receta_local = RecetaLocal(
                        id_paciente_local=paciente_local.id,
                        id_medico_local=medico_local.id,
                        diagnostico=receta_data.get("diagnostico", ""),
                        fecha=datetime.now(),
                        drive_file_id=file_id,
                        xml_filename=filename,
                        synced_at=datetime.now()
                    )
                    self.session.add(receta_local)
                    self.session.flush()
                    
                    # Agregar medicamentos
                    for med_data in receta_data.get("medicamentos", []):
                        medicamento_local = MedicamentoLocal(
                            id_receta_local=receta_local.id,
                            nombre=med_data.get("nombre", ""),
                            dosis=med_data.get("dosis", ""),
                            frecuencia=med_data.get("frecuencia", "")
                        )
                        self.session.add(medicamento_local)
                    
                    # Registrar como procesado
                    checksum = self._calculate_checksum(xml_bytes)
                    registro = SyncArchivos(
                        nombre_archivo=filename,
                        fecha_procesado=datetime.now(),
                        estado="PROCESADO",
                        checksum=checksum
                    )
                    self.session.add(registro)
                    
                    # Mover archivo a procesados
                    procesados_id = get_or_create_folder(self.drive_service, self.procesados_folder)
                    move_file_to_folder(self.drive_service, file_id, procesados_id)
                    
                    print(f"[OK] Receta procesada: {receta_data['paciente']['nombre']}")
                    procesados += 1
                    
                except Exception as e:
                    print(f"[ERROR] Error procesando {filename}: {e}")
                    errores += 1
                    
                    # Mover archivo a errores
                    errores_id = get_or_create_folder(self.drive_service, self.errores_folder)
                    try:
                        move_file_to_folder(self.drive_service, file_id, errores_id)
                    except:
                        pass
            
            self.session.commit()
            
            print(f"\n=== RESUMEN SINCRONIZACIÓN ===")
            print(f"Recetas procesadas: {procesados}")
            print(f"Errores: {errores}")
            
            return procesados, errores
            
        except Exception as e:
            print(f"[ERROR] Error general en sincronización: {e}")
            self.session.rollback()
            return 0, 1
    
    def _buscar_o_crear_paciente_local(self, paciente_data):
        """Busca o crea un paciente local."""
        correo = paciente_data.get("correo", "")
        nombre = paciente_data.get("nombre", "")

        if not nombre:
            raise ValueError("El nombre del paciente es obligatorio para crear o buscar un registro local.")
        
        if correo:
            paciente = self.session.query(PacienteLocal).filter_by(correo=correo).first()
            if paciente:
                return paciente
        
        # Generar ID externo temporal si no hay correo
        import time
        id_externo = int(time.time() * 1000) % 100000 if not correo else None
        
        # Crear nuevo paciente local
        paciente = PacienteLocal(
            id_externo=id_externo,
            nombre=nombre,
            edad=paciente_data.get("edad"),
            genero=paciente_data.get("genero", ""),
            correo=correo,
            synced_at=datetime.now()
        )
        self.session.add(paciente)
        self.session.flush()
        return paciente
    
    def _buscar_o_crear_medico_local(self, medico_data):
        """Busca o crea un médico local."""
        cedula = medico_data.get("cedula", "")
        
        if cedula:
            medico = self.session.query(MedicoLocal).filter_by(cedula_profesional=cedula).first()
            if medico:
                return medico
        
        # Generar ID externo temporal si no hay cédula
        import time
        id_externo = int(time.time() * 1000) % 100000 if not cedula else None
        
        # Crear nuevo médico local
        medico = MedicoLocal(
            id_externo=id_externo,
            nombre=medico_data.get("nombre", ""),
            cedula_profesional=cedula,
            especialidad=medico_data.get("especialidad", ""),
            synced_at=datetime.now()
        )
        self.session.add(medico)
        self.session.flush()
        return medico
    
    def _generar_xml_desde_local(self, receta_local):
        """Genera XML desde datos de receta local."""
        data = {
            "paciente": {
                "nombre": receta_local.paciente_local.nombre,
                "edad": receta_local.paciente_local.edad,
                "genero": receta_local.paciente_local.genero,
                "correo": receta_local.paciente_local.correo
            },
            "medico": {
                "nombre": receta_local.medico_local.nombre,
                "cedula": receta_local.medico_local.cedula_profesional,
                "especialidad": receta_local.medico_local.especialidad
            },
            "diagnostico": receta_local.diagnostico,
            "medicamentos": [
                {
                    "nombre": med.nombre,
                    "dosis": med.dosis,
                    "frecuencia": med.frecuencia
                }
                for med in receta_local.medicamentos_local
            ]
        }
        
        xml_bytes, _ = generar_xml_receta(data)
        return xml_bytes
    
    def _calculate_checksum(self, data):
        """Calcula checksum MD5 de los datos."""
        return hashlib.md5(data).hexdigest()
    
    def obtener_recetas_locales(self):
        """Obtiene todas las recetas locales."""
        return self.session.query(RecetaLocal).all()
    
    def obtener_receta_por_id(self, receta_id):
        """Obtiene una receta local por ID."""
        return self.session.query(RecetaLocal).filter_by(id=receta_id).first()
    
    def cerrar_sesion(self):
        """Cierra la sesión de base de datos."""
        self.session.close()

def sincronizar_recetas_completo():
    """Función para sincronización completa de recetas."""
    manager = RecetaSyncManager()
    
    try:
        print("=== INICIANDO SINCRONIZACIÓN COMPLETA DE RECETAS ===")
        
        # 1. Procesar archivos XML locales
        print("\n1. Procesando archivos XML locales...")
        procesados_locales, errores_locales = manager.procesar_archivos_xml_locales()
        
        # 2. Sincronizar con Drive
        print("\n2. Sincronizando con Google Drive...")
        sincronizadas_drive, errores_drive = manager.sincronizar_con_drive()
        
        # 3. Sincronizar desde Drive
        print("\n3. Sincronizando desde Google Drive...")
        procesados_drive, errores_drive_descarga = manager.sincronizar_desde_drive()
        
        print(f"\n=== RESUMEN FINAL ===")
        print(f"Archivos XML locales procesados: {procesados_locales}")
        print(f"Recetas sincronizadas con Drive: {sincronizadas_drive}")
        print(f"Recetas procesadas desde Drive: {procesados_drive}")
        print(f"Total errores: {errores_locales + errores_drive + errores_drive_descarga}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error en sincronización completa: {e}")
        return False
    finally:
        manager.cerrar_sesion()

if __name__ == "__main__":
    sincronizar_recetas_completo()
