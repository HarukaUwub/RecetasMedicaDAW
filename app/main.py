import sys
import os
from lxml import etree
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QMessageBox, QInputDialog
)
from apscheduler.schedulers.background import BackgroundScheduler

# --- Utils ---
from drive_utils import (
    get_drive_service, get_or_create_folder, upload_file_bytes,
    list_files_in_folder, download_file_bytes
)
from xml_utils import generar_xml_receta, generar_pdf_receta, parse_xml_receta, validar_receta_xml
from med_pdf_mailer import generate_pdf_with_password, send_email_with_attachment

# --- DB opcional ---
DB_AVAILABLE = False
try:
    from database import Session, insert_receta
    from models import Receta, Paciente, Medico
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    print("DB no disponible:", e)

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
        self.recetas_memoria = []
        self.next_id = 1
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

        try:
            # --- XML y PDF (con validación y checksum integrados) ---
            xml_bytes, xml_filename = generar_xml_receta(data)
            xml_path = os.path.join(XML_FOLDER, xml_filename)
            with open(xml_path, 'wb') as f: f.write(xml_bytes)

        except etree.DocumentInvalid as e:
            # Captura el error de validación XSD y muestra un mensaje detallado
            error_str = "\n".join(str(error) for error in e.error_log)
            QMessageBox.critical(self, "Error de Validación XML", f"La receta no cumple con la estructura requerida (XSD) y no será procesada.\n\nDetalles:\n{error_str}")
            return # Detiene el proceso si el XML es inválido

        # --- Si el XML es válido, proceder a generar PDF, subir a Drive y guardar en BD ---
        generar_pdf_receta(data)
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

    # ====================== RECUPERAR ======================
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

                es_valido, errores = validar_receta_xml(xml_bytes, 'receta.xsd')
                if not es_valido:
                    error_str = "\n".join(errores)
                    print(f"[ERROR] Falló la validación del archivo {f['name']}\nMotivo: {error_str}\nAcción tomada: Receta rechazada, no insertada en BD.")
                    QMessageBox.warning(self, "Receta Inválida", f"El archivo {f['name']} es inválido y no se procesará.\n\nDetalles:\n{error_str}")
                    continue

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

    # ====================== MEMORIA LOCAL ======================
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

    # ====================== ENVIAR CORREO ======================
    def on_enviar_correo(self):
        # Pedir al usuario el ID de la receta
        receta_id, ok = QInputDialog.getInt(self, "Enviar receta", "Ingrese ID de la receta:")
        if not ok:
            return

        # Buscar receta en memoria local
        receta = next((r for r in self.recetas_memoria if r.get("id") == receta_id), None)

        # Si DB está disponible, buscar allí también
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

        QMessageBox.information(self, "Correo enviado", f"Receta ID {receta_id} enviada a {correo} (PDF protegido).")


# ====================== JOB SYNC ======================
def start_sync_job(window, minutes=15):
    sched = BackgroundScheduler()
    sched.add_job(lambda: window.on_recuperar(), 'interval', minutes=minutes)
    sched.start()
    print(f"Sync job iniciado cada {minutes} minutos.")


# ====================== MAIN ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    start_sync_job(window, minutes=15)
    sys.exit(app.exec_())
