#!/usr/bin/env python3
"""
Aplicación de Escritorio con Sincronización de Pacientes.
Extiende la aplicación existente con funcionalidades de sincronización.
"""

import logging
import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QPushButton, QListWidget, QMessageBox, QInputDialog,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from apscheduler.schedulers.background import BackgroundScheduler

# --- Utils existentes ---
from .drive_utils import (
    get_drive_service, get_or_create_folder, upload_file_bytes,
    list_files_in_folder, download_file_bytes
)
from .xml_utils import generar_xml_receta, generar_pdf_receta, parse_xml_receta
from .med_pdf_mailer import generate_pdf_with_password, send_email_with_attachment

# --- Nuevas utilidades ---
from .sync_pacientes import PacienteSyncManager, sincronizar_pacientes_manual
from .paciente_xml_utils import crear_paciente_desde_formulario, generar_y_subir_paciente_xml, validar_xml_con_xsd, parse_xml_paciente
from dotenv import load_dotenv
load_dotenv()

# --- Configuración de Logging ---
from .logger_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# --- DB opcional ---
DB_AVAILABLE = False
try:
    from .database import Session, insert_receta
    from .models import Receta, Paciente, Medico, PacienteLocal, SyncArchivos
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    logger.warning(f"Base de datos no disponible: {e}")

# --- Carpetas locales ---
XML_FOLDER = "xmls"
PDF_FOLDER = "pdfs"
PACIENTES_FOLDER = "data_local/pacientes"
os.makedirs(XML_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(PACIENTES_FOLDER, exist_ok=True)

class SyncThread(QThread):
    """Thread para sincronización en segundo plano."""
    sync_completed = pyqtSignal(dict)
    sync_progress = pyqtSignal(str)
    
    def run(self):
        try:
            logger.info("Iniciando hilo de sincronización...")
            manager = PacienteSyncManager()
            resultado = manager.sincronizar_pacientes()
            self.sync_completed.emit(resultado)
        except Exception as e:
            self.sync_completed.emit({"error": str(e)})

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.drive_folder_id = None
        self.service = None
        self.medicamentos = []
        self.recetas_memoria = []
        self.next_id = 1
        self.sync_manager = PacienteSyncManager() if DB_AVAILABLE else None
        self.init_ui()
        self.init_sync_timer()

    def init_ui(self):
        self.setWindowTitle("Recetario Médico - Con Sincronización de Pacientes")
        self.setGeometry(100, 100, 1200, 800)
        
        # Crear pestañas
        tab_widget = QTabWidget()
        
        # Pestaña de Recetas (funcionalidad original)
        recetas_tab = self.create_recetas_tab()
        tab_widget.addTab(recetas_tab, "Recetas Médicas")
        
        # Pestaña de Pacientes
        pacientes_tab = self.create_pacientes_tab()
        tab_widget.addTab(pacientes_tab, "Gestión de Pacientes")
        
        # Pestaña de Recetas Offline
        recetas_offline_tab = self.create_recetas_offline_tab()
        tab_widget.addTab(recetas_offline_tab, "Recetas Offline")
        
        # Pestaña de Sincronización
        sync_tab = self.create_sync_tab()
        tab_widget.addTab(sync_tab, "Sincronización")
        
        layout = QVBoxLayout()
        layout.addWidget(tab_widget)
        self.setLayout(layout)

    def create_recetas_tab(self):
        """Crea la pestaña de recetas (funcionalidad original)."""
        widget = QWidget()
        layout = QVBoxLayout()

        # --- Paciente ---
        self.paciente_nombre = QLineEdit(); self.paciente_nombre.setPlaceholderText("Nombre paciente")
        self.paciente_edad = QLineEdit(); self.paciente_edad.setPlaceholderText("Edad")
        self.paciente_genero = QLineEdit(); self.paciente_genero.setPlaceholderText("Género (M/F)")
        self.paciente_correo = QLineEdit(); self.paciente_correo.setPlaceholderText("Correo paciente")

        # --- Médico ---
        self.medico_nombre = QLineEdit(); self.medico_nombre.setPlaceholderText("Nombre médico")
        self.medico_cedula = QLineEdit(); self.medico_cedula.setPlaceholderText("Cédula profesional")
        self.medico_especialidad = QLineEdit(); self.medico_especialidad.setPlaceholderText("Especialidad")

        # --- Diagnóstico ---
        self.diagnostico = QTextEdit(); self.diagnostico.setPlaceholderText("Diagnóstico")

        # --- Medicamentos ---
        self.medicamento_nombre = QLineEdit(); self.medicamento_nombre.setPlaceholderText("Nombre medicamento")
        self.medicamento_dosis = QLineEdit(); self.medicamento_dosis.setPlaceholderText("Dosis")
        self.medicamento_frecuencia = QLineEdit(); self.medicamento_frecuencia.setPlaceholderText("Frecuencia")
        self.btn_agregar_medicamento = QPushButton("Agregar medicamento")
        self.btn_agregar_medicamento.clicked.connect(self.agregar_medicamento)
        self.lista_medicamentos = QListWidget()

        # --- Botones ---
        self.btn_generar = QPushButton("Generar receta y subir a Drive"); self.btn_generar.clicked.connect(self.on_generar)
        self.btn_recuperar = QPushButton("Recuperar recetas desde Drive"); self.btn_recuperar.clicked.connect(self.on_recuperar)
        self.btn_enviar_correo = QPushButton("Enviar receta por correo"); self.btn_enviar_correo.clicked.connect(self.on_enviar_correo)
        self.lista = QListWidget()

        # --- Layout ---
        layout.addWidget(QLabel("Paciente"))
        layout.addWidget(self.paciente_nombre); layout.addWidget(self.paciente_edad)
        layout.addWidget(self.paciente_genero); layout.addWidget(self.paciente_correo)

        layout.addWidget(QLabel("Médico"))
        layout.addWidget(self.medico_nombre); layout.addWidget(self.medico_cedula)
        layout.addWidget(self.medico_especialidad)

        layout.addWidget(QLabel("Diagnóstico")); layout.addWidget(self.diagnostico)

        layout.addWidget(QLabel("Medicamento individual"))
        layout.addWidget(self.medicamento_nombre); layout.addWidget(self.medicamento_dosis)
        layout.addWidget(self.medicamento_frecuencia); layout.addWidget(self.btn_agregar_medicamento)
        layout.addWidget(QLabel("Medicamentos agregados:")); layout.addWidget(self.lista_medicamentos)

        layout.addWidget(self.btn_generar); layout.addWidget(self.btn_recuperar)
        layout.addWidget(self.btn_enviar_correo)
        layout.addWidget(QLabel("Archivos en Drive:")); layout.addWidget(self.lista)

        widget.setLayout(layout)
        return widget

    def create_pacientes_tab(self):
        """Crea la pestaña de gestión de pacientes."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Grupo para agregar paciente
        grupo_agregar = QGroupBox("Agregar Nuevo Paciente")
        layout_agregar = QVBoxLayout()

        # Campos del paciente
        self.paciente_nombre_nuevo = QLineEdit(); self.paciente_nombre_nuevo.setPlaceholderText("Nombre completo")
        self.paciente_edad_nuevo = QLineEdit(); self.paciente_edad_nuevo.setPlaceholderText("Edad")
        self.paciente_genero_nuevo = QLineEdit(); self.paciente_genero_nuevo.setPlaceholderText("Género (M/F)")
        self.paciente_correo_nuevo = QLineEdit(); self.paciente_correo_nuevo.setPlaceholderText("Correo electrónico")
        self.paciente_telefono_nuevo = QLineEdit(); self.paciente_telefono_nuevo.setPlaceholderText("Teléfono")
        
        # Dirección
        self.paciente_calle = QLineEdit(); self.paciente_calle.setPlaceholderText("Calle")
        self.paciente_colonia = QLineEdit(); self.paciente_colonia.setPlaceholderText("Colonia")
        self.paciente_ciudad = QLineEdit(); self.paciente_ciudad.setPlaceholderText("Ciudad")
        self.paciente_estado = QLineEdit(); self.paciente_estado.setPlaceholderText("Estado")
        self.paciente_cp = QLineEdit(); self.paciente_cp.setPlaceholderText("Código Postal")

        self.btn_agregar_paciente = QPushButton("Agregar Paciente y Generar XML")
        self.btn_agregar_paciente.clicked.connect(self.agregar_paciente_nuevo)

        layout_agregar.addWidget(QLabel("Datos Personales:"))
        layout_agregar.addWidget(self.paciente_nombre_nuevo)
        layout_agregar.addWidget(self.paciente_edad_nuevo)
        layout_agregar.addWidget(self.paciente_genero_nuevo)
        layout_agregar.addWidget(self.paciente_correo_nuevo)
        layout_agregar.addWidget(self.paciente_telefono_nuevo)
        
        layout_agregar.addWidget(QLabel("Dirección:"))
        layout_agregar.addWidget(self.paciente_calle)
        layout_agregar.addWidget(self.paciente_colonia)
        layout_agregar.addWidget(self.paciente_ciudad)
        layout_agregar.addWidget(self.paciente_estado)
        layout_agregar.addWidget(self.paciente_cp)
        
        layout_agregar.addWidget(self.btn_agregar_paciente)
        grupo_agregar.setLayout(layout_agregar)

        # Grupo para listar pacientes locales
        grupo_lista = QGroupBox("Pacientes Sincronizados (BD Local)")
        layout_lista = QVBoxLayout()

        self.tabla_pacientes = QTableWidget()
        self.tabla_pacientes.setColumnCount(8)
        self.tabla_pacientes.setHorizontalHeaderLabels([
            "ID Ext.", "Nombre", "Edad", "Género", "Correo", "Teléfono", "Ciudad", "Sincronizado"
        ])
        self.tabla_pacientes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.btn_refrescar_pacientes = QPushButton("Refrescar Lista")
        self.btn_refrescar_pacientes.clicked.connect(self.refrescar_pacientes)
        
        self.btn_procesar_locales = QPushButton("Procesar Archivos Locales")
        self.btn_procesar_locales.clicked.connect(self.procesar_archivos_locales)

        layout_lista.addWidget(self.tabla_pacientes)
        layout_lista.addWidget(self.btn_refrescar_pacientes)
        layout_lista.addWidget(self.btn_procesar_locales)
        grupo_lista.setLayout(layout_lista)

        layout.addWidget(grupo_agregar)
        layout.addWidget(grupo_lista)

        widget.setLayout(layout)
        return widget

    def create_recetas_offline_tab(self):
        """Crea la pestaña de gestión de recetas offline."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Grupo de procesamiento de archivos XML
        grupo_xml = QGroupBox("Procesar Archivos XML Locales")
        layout_xml = QVBoxLayout()

        self.btn_procesar_xml = QPushButton("Procesar Archivos XML Locales")
        self.btn_procesar_xml.clicked.connect(self.procesar_xml_locales)
        
        self.btn_sincronizar_recetas = QPushButton("Sincronizar Recetas con Drive")
        self.btn_sincronizar_recetas.clicked.connect(self.sincronizar_recetas_drive)
        
        self.btn_sincronizar_desde_drive = QPushButton("Sincronizar Recetas desde Drive")
        self.btn_sincronizar_desde_drive.clicked.connect(self.sincronizar_recetas_desde_drive)

        layout_xml.addWidget(self.btn_procesar_xml)
        layout_xml.addWidget(self.btn_sincronizar_recetas)
        layout_xml.addWidget(self.btn_sincronizar_desde_drive)
        grupo_xml.setLayout(layout_xml)

        # Grupo de lista de recetas offline
        grupo_lista = QGroupBox("Recetas Offline")
        layout_lista = QVBoxLayout()

        self.tabla_recetas_offline = QTableWidget()
        self.tabla_recetas_offline.setColumnCount(6)
        self.tabla_recetas_offline.setHorizontalHeaderLabels([
            "ID", "Paciente", "Médico", "Diagnóstico", "Fecha", "Estado"
        ])
        self.tabla_recetas_offline.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.btn_refrescar_recetas_offline = QPushButton("Refrescar Lista")
        self.btn_refrescar_recetas_offline.clicked.connect(self.refrescar_recetas_offline)

        layout_lista.addWidget(self.tabla_recetas_offline)
        layout_lista.addWidget(self.btn_refrescar_recetas_offline)
        grupo_lista.setLayout(layout_lista)

        # Grupo de acciones
        grupo_acciones = QGroupBox("Acciones")
        layout_acciones = QHBoxLayout()

        self.btn_enviar_receta_offline = QPushButton("Enviar Receta por Correo")
        self.btn_enviar_receta_offline.clicked.connect(self.enviar_receta_offline)
        
        self.btn_ver_detalles_offline = QPushButton("Ver Detalles")
        self.btn_ver_detalles_offline.clicked.connect(self.ver_detalles_receta_offline)

        layout_acciones.addWidget(self.btn_enviar_receta_offline)
        layout_acciones.addWidget(self.btn_ver_detalles_offline)
        grupo_acciones.setLayout(layout_acciones)

        layout.addWidget(grupo_xml)
        layout.addWidget(grupo_lista)
        layout.addWidget(grupo_acciones)

        widget.setLayout(layout)
        return widget

    def create_sync_tab(self):
        """Crea la pestaña de sincronización."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Grupo de sincronización manual
        grupo_sync = QGroupBox("Sincronización Manual")
        layout_sync = QVBoxLayout()

        self.btn_sincronizar = QPushButton("Sincronizar Pacientes Ahora")
        self.btn_sincronizar.clicked.connect(self.sincronizar_manual)
        
        self.texto_sync = QTextEdit()
        self.texto_sync.setReadOnly(True)
        self.texto_sync.setMaximumHeight(200)

        layout_sync.addWidget(self.btn_sincronizar)
        layout_sync.addWidget(QLabel("Log de Sincronización:"))
        layout_sync.addWidget(self.texto_sync)
        grupo_sync.setLayout(layout_sync)

        # Grupo de estadísticas
        grupo_stats = QGroupBox("Estadísticas de Sincronización")
        layout_stats = QVBoxLayout()

        self.label_stats = QLabel("Cargando estadísticas...")
        self.btn_refrescar_stats = QPushButton("Refrescar Estadísticas")
        self.btn_refrescar_stats.clicked.connect(self.refrescar_estadisticas)

        layout_stats.addWidget(self.label_stats)
        layout_stats.addWidget(self.btn_refrescar_stats)
        grupo_stats.setLayout(layout_stats)

        # Grupo de configuración
        grupo_config = QGroupBox("Configuración de Sincronización")
        layout_config = QVBoxLayout()

        self.label_auto_sync = QLabel("Sincronización automática: ACTIVADA (cada 15 minutos)")
        self.btn_toggle_auto_sync = QPushButton("Desactivar Sincronización Automática")
        self.btn_toggle_auto_sync.clicked.connect(self.toggle_auto_sync)
        self.auto_sync_enabled = True

        layout_config.addWidget(self.label_auto_sync)
        layout_config.addWidget(self.btn_toggle_auto_sync)
        grupo_config.setLayout(layout_config)

        layout.addWidget(grupo_sync)
        layout.addWidget(grupo_stats)
        layout.addWidget(grupo_config)

        widget.setLayout(layout)
        return widget

    def init_sync_timer(self):
        """Inicializa el timer para sincronización automática."""
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sincronizar_automatica)
        self.sync_timer.start(15 * 60 * 1000)  # 15 minutos

    def agregar_paciente_nuevo(self):
        """Agrega un nuevo paciente y genera XML."""
        try:
            # Validar campos obligatorios
            nombre = self.paciente_nombre_nuevo.text().strip()
            correo = self.paciente_correo_nuevo.text().strip()
            
            if not nombre or not correo:
                QMessageBox.warning(self, "Error", "Nombre y correo son obligatorios")
                return

            # Crear datos del paciente
            paciente_data = crear_paciente_desde_formulario(
                nombre,
                self.paciente_edad_nuevo.text(),
                self.paciente_genero_nuevo.text(),
                correo,
                self.paciente_telefono_nuevo.text(),
                self.paciente_calle.text(),
                self.paciente_colonia.text(),
                self.paciente_ciudad.text(),
                self.paciente_estado.text(),
                self.paciente_cp.text()
            )

            # Inicializar Drive
            self.init_drive()
            
            # Generar y subir XML
            file_id, filename = generar_y_subir_paciente_xml(
                self.service, paciente_data, "ALTA"
            )

            if file_id:
                QMessageBox.information(
                    self, "Éxito", 
                    f"Paciente agregado exitosamente.\nXML generado: {filename}\nSubido a Drive con ID: {file_id}"
                )
            else:
                QMessageBox.information(
                    self, "Éxito (Local)", 
                    f"Paciente agregado localmente.\nXML generado: {filename}\n(Drive no disponible)"
                )

            # Limpiar formulario
            self.limpiar_formulario_paciente()
            
            # Refrescar lista
            self.refrescar_pacientes()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error agregando paciente: {str(e)}")

    def limpiar_formulario_paciente(self):
        """Limpia el formulario de paciente."""
        self.paciente_nombre_nuevo.clear()
        self.paciente_edad_nuevo.clear()
        self.paciente_genero_nuevo.clear()
        self.paciente_correo_nuevo.clear()
        self.paciente_telefono_nuevo.clear()
        self.paciente_calle.clear()
        self.paciente_colonia.clear()
        self.paciente_ciudad.clear()
        self.paciente_estado.clear()
        self.paciente_cp.clear()

    def refrescar_pacientes(self):
        """Refresca la lista de pacientes locales."""
        logger.info("Refrescando la lista de pacientes locales...")
        
        if not DB_AVAILABLE:
            logger.warning("No se puede refrescar pacientes, la base de datos no está disponible.")
            self.tabla_pacientes.setRowCount(0)
            QMessageBox.warning(self, "Error", "Base de datos no disponible")
            return

        try:
            # Usar Session directamente en lugar de sync_manager
            from .database import Session
            from .models import PacienteLocal
            
            session = Session()
            pacientes = session.query(PacienteLocal).all()
            
            logger.info(f"Se encontraron {len(pacientes)} pacientes en la BD local.")
            
            self.tabla_pacientes.setRowCount(len(pacientes))
            
            for i, paciente in enumerate(pacientes):
                self.tabla_pacientes.setItem(i, 0, QTableWidgetItem(str(paciente.id_externo)))
                self.tabla_pacientes.setItem(i, 1, QTableWidgetItem(paciente.nombre))
                self.tabla_pacientes.setItem(i, 2, QTableWidgetItem(str(paciente.edad) if paciente.edad else ""))
                self.tabla_pacientes.setItem(i, 3, QTableWidgetItem(paciente.genero))
                self.tabla_pacientes.setItem(i, 4, QTableWidgetItem(paciente.correo))
                self.tabla_pacientes.setItem(i, 5, QTableWidgetItem(paciente.telefono))
                self.tabla_pacientes.setItem(i, 6, QTableWidgetItem(paciente.ciudad))
                self.tabla_pacientes.setItem(i, 7, QTableWidgetItem(
                    paciente.synced_at.strftime("%Y-%m-%d %H:%M") if paciente.synced_at else ""
                ))
            
            session.close()
            
            QMessageBox.information(self, "Éxito", f"Lista actualizada con {len(pacientes)} pacientes")
            
        except Exception as e:
            logger.error(f"Error al refrescar la lista de pacientes: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Error refrescando pacientes: {str(e)}")

    def procesar_archivos_locales(self):
        """Procesa archivos XML locales cuando no hay conexión."""
        print("Procesando archivos locales...")
        
        if not DB_AVAILABLE:
            QMessageBox.warning(self, "Error", "Base de datos no disponible")
            return
        
        try:
            import os
            from datetime import datetime
            
            # Buscar archivos XML en data_local
            archivos_locales = []
            data_local_dir = "data_local"
            
            if os.path.exists(data_local_dir):
                for archivo in os.listdir(data_local_dir):
                    if archivo.endswith('.xml') and not archivo.endswith('_OK.xml') and not archivo.endswith('_ERR.xml'):
                        archivos_locales.append(os.path.join(data_local_dir, archivo))
            
            if not archivos_locales:
                QMessageBox.information(self, "Info", "No hay archivos XML locales para procesar")
                return
            
            session = Session()
            procesados = 0
            errores = 0
            
            for archivo_path in archivos_locales:
                archivo_name = os.path.basename(archivo_path)
                print(f"Procesando: {archivo_name}")
                
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
            
            session.commit()
            session.close()
            
            mensaje = f"Archivos locales procesados:\n- Procesados: {procesados}\n- Errores: {errores}"
            QMessageBox.information(self, "Procesamiento Completado", mensaje)
            
            # Refrescar la lista
            self.refrescar_pacientes()
            
        except Exception as e:
            print(f"Error procesando archivos locales: {e}")
            QMessageBox.warning(self, "Error", f"Error procesando archivos locales: {str(e)}")

    def procesar_xml_locales(self):
        """Procesa archivos XML locales de recetas."""
        if not DB_AVAILABLE:
            QMessageBox.warning(self, "Error", "Base de datos no disponible")
            return
        
        try:
            from .sync_recetas import RecetaSyncManager
            manager = RecetaSyncManager()
            procesados, errores = manager.procesar_archivos_xml_locales()
            manager.cerrar_sesion()
            
            mensaje = f"Archivos XML procesados:\n- Procesados: {procesados}\n- Errores: {errores}"
            QMessageBox.information(self, "Procesamiento Completado", mensaje)
            
            # Refrescar la lista
            self.refrescar_recetas_offline()
            
        except Exception as e:
            print(f"Error procesando XML locales: {e}")
            QMessageBox.warning(self, "Error", f"Error procesando XML locales: {str(e)}")

    def sincronizar_recetas_drive(self):
        """Sincroniza recetas locales con Google Drive."""
        if not DB_AVAILABLE:
            QMessageBox.warning(self, "Error", "Base de datos no disponible")
            return
        
        try:
            from .sync_recetas import RecetaSyncManager
            manager = RecetaSyncManager()
            sincronizadas, errores = manager.sincronizar_con_drive()
            manager.cerrar_sesion()
            
            mensaje = f"Recetas sincronizadas con Drive:\n- Sincronizadas: {sincronizadas}\n- Errores: {errores}"
            QMessageBox.information(self, "Sincronización Completada", mensaje)
            
        except Exception as e:
            print(f"Error sincronizando con Drive: {e}")
            QMessageBox.warning(self, "Error", f"Error sincronizando con Drive: {str(e)}")

    def sincronizar_recetas_desde_drive(self):
        """Sincroniza recetas desde Google Drive."""
        if not DB_AVAILABLE:
            QMessageBox.warning(self, "Error", "Base de datos no disponible")
            return
        
        try:
            from .sync_recetas import RecetaSyncManager
            manager = RecetaSyncManager()
            procesadas, errores = manager.sincronizar_desde_drive()
            manager.cerrar_sesion()
            
            mensaje = f"Recetas sincronizadas desde Drive:\n- Procesadas: {procesadas}\n- Errores: {errores}"
            QMessageBox.information(self, "Sincronización Completada", mensaje)
            
            # Refrescar la lista
            self.refrescar_recetas_offline()
            
        except Exception as e:
            print(f"Error sincronizando desde Drive: {e}")
            QMessageBox.warning(self, "Error", f"Error sincronizando desde Drive: {str(e)}")

    def refrescar_recetas_offline(self):
        """Refresca la lista de recetas offline."""
        if not DB_AVAILABLE:
            QMessageBox.warning(self, "Error", "Base de datos no disponible")
            return
        
        try:
            from .models import RecetaLocal
            session = Session()
            recetas = session.query(RecetaLocal).all()
            
            self.tabla_recetas_offline.setRowCount(len(recetas))
            
            for i, receta in enumerate(recetas):
                estado = "Sincronizado" if receta.drive_file_id else "Local"
                
                self.tabla_recetas_offline.setItem(i, 0, QTableWidgetItem(str(receta.id)))
                self.tabla_recetas_offline.setItem(i, 1, QTableWidgetItem(receta.paciente_local.nombre))
                self.tabla_recetas_offline.setItem(i, 2, QTableWidgetItem(receta.medico_local.nombre))
                self.tabla_recetas_offline.setItem(i, 3, QTableWidgetItem(receta.diagnostico[:50] + "..." if len(receta.diagnostico) > 50 else receta.diagnostico))
                self.tabla_recetas_offline.setItem(i, 4, QTableWidgetItem(receta.fecha.strftime("%d/%m/%Y %H:%M")))
                self.tabla_recetas_offline.setItem(i, 5, QTableWidgetItem(estado))
            
            session.close()
            
            QMessageBox.information(self, "Éxito", f"Lista actualizada con {len(recetas)} recetas offline")
            
        except Exception as e:
            print(f"Error refrescando recetas offline: {e}")
            QMessageBox.warning(self, "Error", f"Error refrescando recetas offline: {str(e)}")

    def enviar_receta_offline(self):
        """Envía una receta offline por correo."""
        current_row = self.tabla_recetas_offline.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Error", "Seleccione una receta de la lista")
            return
        
        receta_id = int(self.tabla_recetas_offline.item(current_row, 0).text())
        
        # Usar la función de envío existente que ya busca en recetas locales
        self.on_enviar_correo()

    def ver_detalles_receta_offline(self):
        """Muestra los detalles de una receta offline."""
        current_row = self.tabla_recetas_offline.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Error", "Seleccione una receta de la lista")
            return
        
        receta_id = int(self.tabla_recetas_offline.item(current_row, 0).text())
        
        try:
            from .models import RecetaLocal
            session = Session()
            receta = session.query(RecetaLocal).filter_by(id=receta_id).first()
            
            if receta:
                detalles = f"""
ID: {receta.id}
Paciente: {receta.paciente_local.nombre}
Correo: {receta.paciente_local.correo}
Médico: {receta.medico_local.nombre}
Especialidad: {receta.medico_local.especialidad}
Diagnóstico: {receta.diagnostico}
Fecha: {receta.fecha.strftime("%d/%m/%Y %H:%M")}
Estado: {'Sincronizado' if receta.drive_file_id else 'Local'}

Medicamentos:
"""
                for med in receta.medicamentos_local:
                    detalles += f"- {med.nombre}: {med.dosis} ({med.frecuencia})\n"
                
                QMessageBox.information(self, "Detalles de la Receta", detalles)
            else:
                QMessageBox.warning(self, "Error", "Receta no encontrada")
            
            session.close()
            
        except Exception as e:
            print(f"Error obteniendo detalles: {e}")
            QMessageBox.warning(self, "Error", f"Error obteniendo detalles: {str(e)}")

    def sincronizar_manual(self):
        """Inicia sincronización manual."""
        if not DB_AVAILABLE:
            QMessageBox.warning(self, "Error", "Base de datos no disponible")
            return

        self.btn_sincronizar.setEnabled(False)
        self.texto_sync.append(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando sincronización manual...")
        
        # Crear y ejecutar thread de sincronización
        self.sync_thread = SyncThread()
        self.sync_thread.sync_completed.connect(self.on_sync_completed)
        self.sync_thread.sync_progress.connect(self.on_sync_progress)
        self.sync_thread.start()

    def on_sync_progress(self, mensaje):
        """Maneja progreso de sincronización."""
        self.texto_sync.append(f"[{datetime.now().strftime('%H:%M:%S')}] {mensaje}")

    def on_sync_completed(self, resultado):
        """Maneja finalización de sincronización."""
        self.btn_sincronizar.setEnabled(True)
        
        if "error" in resultado:
            self.texto_sync.append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {resultado['error']}")
            QMessageBox.critical(self, "Error de Sincronización", resultado["error"])
        else:
            mensaje = f"✅ Sincronización completada:\n"
            mensaje += f"- Archivos procesados: {resultado['procesados']}\n"
            mensaje += f"- Pacientes actualizados: {resultado['actualizados']}\n"
            mensaje += f"- Errores: {resultado['errores']}"
            
            self.texto_sync.append(f"[{datetime.now().strftime('%H:%M:%S')}] {mensaje}")
            
            for detalle in resultado.get('detalles', []):
                self.texto_sync.append(f"  {detalle}")
            
            QMessageBox.information(self, "Sincronización Completada", mensaje)
            
            # Refrescar datos
            self.refrescar_pacientes()
            self.refrescar_estadisticas()

    def sincronizar_automatica(self):
        """Sincronización automática."""
        if not self.auto_sync_enabled or not DB_AVAILABLE or not self.sync_manager:
            return

        try:
            resultado = self.sync_manager.sincronizar_pacientes()
            if resultado['procesados'] > 0:
                self.texto_sync.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Sync automático: {resultado['procesados']} archivos procesados")
                self.refrescar_pacientes()
                self.refrescar_estadisticas()
        except Exception as e:
            self.texto_sync.append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error sync automático: {str(e)}")

    def refrescar_estadisticas(self):
        """Refresca las estadísticas de sincronización."""
        if not DB_AVAILABLE or not self.sync_manager:
            self.label_stats.setText("Base de datos no disponible")
            return

        try:
            stats = self.sync_manager.obtener_estadisticas_sync()
            texto = f"Total pacientes locales: {stats['total_pacientes_local']}\n"
            texto += f"Archivos procesados: {stats['archivos_procesados']}\n"
            texto += f"Archivos con error: {stats['archivos_error']}"
            self.label_stats.setText(texto)
        except Exception as e:
            self.label_stats.setText(f"Error cargando estadísticas: {str(e)}")

    def toggle_auto_sync(self):
        """Activa/desactiva sincronización automática."""
        self.auto_sync_enabled = not self.auto_sync_enabled
        
        if self.auto_sync_enabled:
            self.sync_timer.start(15 * 60 * 1000)  # 15 minutos
            self.label_auto_sync.setText("Sincronización automática: ACTIVADA (cada 15 minutos)")
            self.btn_toggle_auto_sync.setText("Desactivar Sincronización Automática")
        else:
            self.sync_timer.stop()
            self.label_auto_sync.setText("Sincronización automática: DESACTIVADA")
            self.btn_toggle_auto_sync.setText("Activar Sincronización Automática")

    # ====================== MÉTODOS ORIGINALES (sin cambios) ======================
    def agregar_medicamento(self):
        nombre, dosis, frecuencia = self.medicamento_nombre.text().strip(), self.medicamento_dosis.text().strip(), self.medicamento_frecuencia.text().strip()
        if not nombre: 
            QMessageBox.warning(self, "Error", "Nombre del medicamento obligatorio")
            return
        self.medicamentos.append({"nombre": nombre, "dosis": dosis, "frecuencia": frecuencia})
        self.lista_medicamentos.addItem(f"{nombre} | {dosis} | {frecuencia}")
        self.medicamento_nombre.clear(); self.medicamento_dosis.clear(); self.medicamento_frecuencia.clear()

    def init_drive(self):
        if self.service and self.drive_folder_id: return
        try:
            self.service = get_drive_service()
            self.drive_folder_id = get_or_create_folder(self.service, "RecetasMedicas")
        except Exception as e:
            print("Drive no disponible:", e)

    def on_generar(self):
        try:
            edad = int(self.paciente_edad.text()) if self.paciente_edad.text() else None
        except ValueError:
            edad = None

        data = {
            "paciente": {"nombre": self.paciente_nombre.text(), "edad": edad,
                         "genero": self.paciente_genero.text().upper() if self.paciente_genero.text().upper() in ['M','F'] else None,
                         "correo": self.paciente_correo.text()},
            "medico": {"nombre": self.medico_nombre.text(), "cedula": self.medico_cedula.text(),
                       "especialidad": self.medico_especialidad.text()},
            "diagnostico": self.diagnostico.toPlainText(),
            "medicamentos": self.medicamentos
        }

        # --- XML y PDF ---
        xml_bytes, xml_filename = generar_xml_receta(data)
        xml_path = os.path.join(XML_FOLDER, xml_filename)
        with open(xml_path, 'wb') as f: f.write(xml_bytes)
        pdf_path = generar_pdf_receta(data)

        # --- Subir a Drive ---
        self.init_drive()
        if self.service and self.drive_folder_id:
            try:
                upload_file_bytes(self.service, xml_bytes, xml_filename, folder_id=self.drive_folder_id)
                print(f"Archivo subido: {xml_filename}")
            except Exception as e: print("Error subiendo a Drive:", e)

        # --- Guardar DB o memoria ---
        if DB_AVAILABLE:
            session = Session()
            try:
                insert_receta(session, data)
                session.commit()
            except Exception as e:
                session.rollback()
                print("Error guardando DB:", e)
        else:
            # Guardar en memoria local evitando duplicados
            self._update_memoria(data)

    def on_recuperar(self):
        self.init_drive()
        if not (self.service and self.drive_folder_id):
            QMessageBox.warning(self, "Drive", "No se puede recuperar archivos sin Drive.")
            return

        try:
            files = list_files_in_folder(self.service, self.drive_folder_id)
            self.lista.clear()
            if not files:
                QMessageBox.information(self, "Info", "No hay archivos en Drive.")
                return

            nuevos = 0; actualizados = 0

            session = Session() if DB_AVAILABLE else None

            for f in files:
                self.lista.addItem(f"{f['name']} | {f['id']} | {f.get('modifiedTime','')}")
                if not f['name'].lower().endswith(".xml"): continue

                xml_bytes = download_file_bytes(self.service, f['id'])
                local_path = os.path.join(XML_FOLDER, f['name'])
                with open(local_path, 'wb') as xf: xf.write(xml_bytes)

                receta_data = parse_xml_receta(xml_bytes)
                receta_data['drive_file_id'] = f['id']

                # ================= ACTUALIZAR DB =================
                if DB_AVAILABLE and session:
                    try:
                        paciente_correo = receta_data.get("paciente", {}).get("correo")
                        medico_cedula = receta_data.get("medico", {}).get("cedula")
                        diagnostico = receta_data.get("diagnostico")

                        existe = session.query(Receta).join(Paciente).join(Medico).filter(
                            Paciente.correo == paciente_correo,
                            Medico.cedula_profesional == medico_cedula,
                            Receta.diagnostico == diagnostico
                        ).first()

                        if existe:
                            existe.diagnostico = diagnostico
                            existe.medicamentos = receta_data.get("medicamentos", [])
                            existe.drive_file_id = f['id']
                            actualizados += 1
                        else:
                            insert_receta(session, receta_data)
                            nuevos += 1
                    except Exception as e:
                        session.rollback()
                        print("Error DB:", e)
                else:
                    # ================= ACTUALIZAR MEMORIA =================
                    if self._update_memoria(receta_data):
                        actualizados += 1
                    else:
                        nuevos += 1

            if session:
                try: session.commit()
                except Exception: session.rollback()
                finally: session.close()

            QMessageBox.information(
                self,
                "Recuperación completa",
                f"Nuevas recetas: {nuevos}, actualizadas: {actualizados}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Drive", f"No se pudo recuperar:\n{e}")

    def _update_memoria(self, receta_data):
        """Actualiza memoria local evitando duplicados. Retorna True si se actualizó."""
        clave = (
            receta_data.get("paciente", {}).get("correo"),
            receta_data.get("medico", {}).get("cedula"),
            receta_data.get("diagnostico")
        )
        for r in self.recetas_memoria:
            r_clave = (
                r.get("paciente", {}).get("correo"),
                r.get("medico", {}).get("cedula"),
                r.get("diagnostico")
            )
            if clave == r_clave:
                r.update(receta_data)
                return True
        receta_data["id"] = self.next_id
        self.recetas_memoria.append(receta_data)
        self.next_id += 1
        return False

    def on_enviar_correo(self):
        # Pedir al usuario el ID de la receta
        receta_id, ok = QInputDialog.getInt(self, "Enviar receta", "Ingrese ID de la receta:")
        if not ok:
            return

        receta = None
        receta_tipo = ""

        # 1. Buscar receta en memoria local
        receta = next((r for r in self.recetas_memoria if r.get("id") == receta_id), None)
        if receta:
            receta_tipo = "memoria"

        # 2. Si DB está disponible, buscar en recetas principales
        if DB_AVAILABLE and not receta:
            session = Session()
            try:
                receta_obj = session.query(Receta).filter_by(id=receta_id).first()
                if receta_obj:
                    receta = {
                        "paciente": {"nombre": getattr(receta_obj.paciente, "nombre", ""),
                                     "correo": getattr(receta_obj.paciente, "correo", "")},
                        "medico": {"nombre": getattr(receta_obj.medico, "nombre", "")},
                        "diagnostico": getattr(receta_obj, "diagnostico", ""),
                        "medicamentos": [{"nombre": m.nombre, "dosis": m.dosis, "frecuencia": m.frecuencia} 
                                         for m in getattr(receta_obj, "medicamentos", [])]
                    }
                    receta_tipo = "principal"
            finally:
                session.close()

        # 3. Buscar en recetas locales (offline)
        if DB_AVAILABLE and not receta:
            session = Session()
            try:
                from .models import RecetaLocal
                receta_obj = session.query(RecetaLocal).filter_by(id=receta_id).first()
                if receta_obj:
                    receta = {
                        "paciente": {"nombre": getattr(receta_obj.paciente_local, "nombre", ""),
                                     "correo": getattr(receta_obj.paciente_local, "correo", "")},
                        "medico": {"nombre": getattr(receta_obj.medico_local, "nombre", "")},
                        "diagnostico": getattr(receta_obj, "diagnostico", ""),
                        "medicamentos": [{"nombre": m.nombre, "dosis": m.dosis, "frecuencia": m.frecuencia} 
                                         for m in getattr(receta_obj, "medicamentos_local", [])]
                    }
                    receta_tipo = "local"
            finally:
                session.close()

        if not receta or not receta.get("paciente", {}).get("correo"):
            QMessageBox.warning(self, "Error", f"No se encontró receta o correo para ID {receta_id}.")
            return

        correo = receta["paciente"]["correo"]
        
        # Generar PDF cifrado
        pdf_path, password = generate_pdf_with_password(
            receta_id,
            receta.get("paciente"),
            receta.get("medico"),
            receta.get("medicamentos")
        )

        sender_str = f"{os.getenv('EMAIL_SENDER_NAME','Recetario')} <{os.getenv('EMAIL_USERNAME')}>"

        # --- Primer correo: PDF ---
        send_email_with_attachment(
            smtp_server=os.getenv("EMAIL_SMTP_SERVER"),
            smtp_port=int(os.getenv("EMAIL_SMTP_PORT", 587)),
            username=os.getenv("EMAIL_USERNAME"),
            password=os.getenv("EMAIL_PASSWORD"),
            sender=sender_str,
            recipient=correo,
            subject=f"Receta médica (ID {receta_id})",
            body="Adjuntamos su receta médica en formato PDF. Por seguridad la contraseña se enviará en un correo separado.",
            attachment_path=pdf_path
        )

        # --- Segundo correo: contraseña ---
        send_email_with_attachment(
            smtp_server=os.getenv("EMAIL_SMTP_SERVER"),
            smtp_port=int(os.getenv("EMAIL_SMTP_PORT", 587)),
            username=os.getenv("EMAIL_USERNAME"),
            password=os.getenv("EMAIL_PASSWORD"),
            sender=sender_str,
            recipient=correo,
            subject=f"Contraseña para abrir su receta (ID {receta_id})",
            body=f"La contraseña para abrir su PDF es:\n\n{password}\n\nPor favor, no comparta esta contraseña.",
            attachment_path=None
        )

        tipo_desc = {
            "memoria": "memoria local",
            "principal": "base de datos principal", 
            "local": "base de datos local (offline)"
        }
        
        QMessageBox.information(self, "Correo enviado", 
            f"Receta ID {receta_id} ({tipo_desc.get(receta_tipo, 'desconocido')}) enviada a {correo} (PDF protegido).")

# ====================== MAIN ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # Cargar datos iniciales
    window.refrescar_pacientes()
    window.refrescar_estadisticas()
    
    sys.exit(app.exec_())
