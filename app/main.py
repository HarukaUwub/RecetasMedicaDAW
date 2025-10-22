import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QMessageBox, QInputDialog
)
from apscheduler.schedulers.background import BackgroundScheduler

# --- Utils ---
from drive_utils import get_drive_service, get_or_create_folder, upload_file_bytes, list_files_in_folder, download_file_bytes
from xml_utils import generar_xml_receta, generar_pdf_receta, parse_xml_receta
from med_pdf_mailer import generate_pdf_with_password, send_email_with_attachment

# --- DB opcional ---
DB_AVAILABLE = False
try:
    # Prefer direct names if available
    from database import Session, insert_receta, Receta, Paciente, Medico
    DB_AVAILABLE = True
except Exception as e:
    # Fallback to importing module and extracting attributes if present
    try:
        import database as _db
        Session = getattr(_db, 'Session')
        insert_receta = getattr(_db, 'insert_receta')
        Receta = getattr(_db, 'Receta', None)
        Paciente = getattr(_db, 'Paciente', None)
        Medico = getattr(_db, 'Medico', None)
        DB_AVAILABLE = True
    except Exception as e2:
        print("DB no disponible:", e2)
        DB_AVAILABLE = False

# --- Carpetas locales ---
XML_FOLDER = "xmls"
PDF_FOLDER = "pdfs"
os.makedirs(XML_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.drive_folder_id = None
        self.service = None

        self.medicamentos = []
        self.recetas_memoria = []  # Para usar si DB falla
        self.next_id = 1  # ID para memoria

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Recetario Médico")
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

        self.setLayout(layout)

    # ====================== MÉTODOS ======================
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

    # ====================== GENERAR ======================
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
    # ====================== RECUPERAR ======================
    def on_recuperar(self):
        """Recupera recetas desde Google Drive y sincroniza memoria y DB."""
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

            nuevos = 0
            actualizados = 0
            deleted_count = 0

            # IDs actuales en Drive
            drive_ids = [f['id'] for f in files if f['name'].lower().endswith('.xml')]

            # Preparar sesión si la DB está disponible
            session = None
            recetas_en_db = []
            if DB_AVAILABLE:
                try:
                    session = Session()
                    # --- Sincronizar DB ---
                    # Eliminar recetas que ya no existen en Drive
                    recetas_en_db = session.query(Receta).all()
                    for receta in recetas_en_db:
                        if getattr(receta, 'drive_file_id', None) and receta.drive_file_id not in drive_ids:
                            session.delete(receta)
                    session.commit()
                    # calcular eliminadas hasta ahora
                    try:
                        remaining = session.query(Receta).count()
                        deleted_count = len(recetas_en_db) - remaining
                    except Exception:
                        deleted_count = 0
                except Exception as e:
                    if session:
                        session.rollback()
                        session.close()
                    session = None
                    print("Error preparando DB para sincronización:", e)

            # --- Descargar y actualizar/insertar ---
            for f in files:
                self.lista.addItem(f"{f['name']} | {f['id']} | {f.get('modifiedTime','')}")
                if not f['name'].lower().endswith(".xml"):
                    continue

                xml_bytes = download_file_bytes(self.service, f['id'])
                local_path = os.path.join(XML_FOLDER, f['name'])
                with open(local_path, 'wb') as xf:
                    xf.write(xml_bytes)

                receta_data = parse_xml_receta(xml_bytes)
                receta_data['drive_file_id'] = f['id']  # guardar ID de Drive para seguimiento

                # --- Verificar si ya existe ---
                if DB_AVAILABLE and session is not None:
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
                            # Sobrescribir datos existentes
                            existe.diagnostico = diagnostico
                            existe.medicamentos = receta_data.get("medicamentos", [])
                            existe.drive_file_id = f['id']
                            actualizados += 1
                        else:
                            insert_receta(session, receta_data)
                            nuevos += 1
                    except Exception as e:
                        session.rollback()
                        print("Error actualizando/insertando en DB:", e)
                else:
                    # Guardar en memoria si no hay DB
                    receta_data["id"] = self.next_id
                    self.recetas_memoria.append(receta_data)
                    self.next_id += 1
                    nuevos += 1

            if session:
                try:
                    session.commit()
                except Exception:
                    session.rollback()
                finally:
                    session.close()

            QMessageBox.information(
                self,
                "Recuperación completa",
                f"Se insertaron {nuevos} nuevas recetas y se actualizaron {actualizados} existentes.\n"
                f"Recetas eliminadas de DB: {deleted_count}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Drive", f"No se pudo recuperar o sincronizar archivos:\n{e}")


    # ====================== ENVIAR CORREO ======================
    def on_enviar_correo(self):
        QMessageBox.information(self, "Info", "Función de envío de correo (PDF protegido) pendiente.")


# ====================== JOB SYNC ======================
def start_sync_job(window, minutes=15):
    try:
        sched = BackgroundScheduler()
        sched.add_job(lambda: window.on_recuperar(), 'interval', minutes=minutes)
        sched.start()
        print(f"Sync job iniciado cada {minutes} minutos.")
    except Exception as e:
        print("No se pudo iniciar el job de sincronización:", e)


# ====================== MAIN ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    start_sync_job(window, minutes=15)
    sys.exit(app.exec_())
