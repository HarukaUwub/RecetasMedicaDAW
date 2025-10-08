import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QMessageBox
)
from database import Session, insert_receta, init_db, Receta, Paciente, Medico
from drive_utils import get_drive_service, get_or_create_folder, upload_file_bytes, list_files_in_folder
from xml_utils import generar_xml_receta, generar_pdf_receta

# Crear carpetas locales
XML_FOLDER = "xmls"
PDF_FOLDER = "pdfs"
os.makedirs(XML_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.drive_folder_id = None
        self.service = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Recetario Médico")
        layout = QVBoxLayout()

        # --- Paciente ---
        self.paciente_nombre = QLineEdit()
        self.paciente_nombre.setPlaceholderText("Nombre paciente")
        self.paciente_edad = QLineEdit()
        self.paciente_edad.setPlaceholderText("Edad")
        self.paciente_genero = QLineEdit()
        self.paciente_genero.setPlaceholderText("Género (M/F)")
        self.paciente_correo = QLineEdit()
        self.paciente_correo.setPlaceholderText("Correo paciente")

        # --- Médico ---
        self.medico_nombre = QLineEdit()
        self.medico_nombre.setPlaceholderText("Nombre médico")
        self.medico_cedula = QLineEdit()
        self.medico_cedula.setPlaceholderText("Cédula profesional")
        self.medico_especialidad = QLineEdit()
        self.medico_especialidad.setPlaceholderText("Especialidad")

        # --- Diagnóstico ---
        self.diagnostico = QTextEdit()
        self.diagnostico.setPlaceholderText("Diagnóstico")

        # --- Medicamentos ---
        self.medicamentos_text = QTextEdit()
        self.medicamentos_text.setPlaceholderText("Medicamentos (nombre|dosis|frecuencia por línea)")

        # --- Botones ---
        self.btn_generar = QPushButton("Generar receta y subir a Drive")
        self.btn_generar.clicked.connect(self.on_generar)
        self.btn_recuperar = QPushButton("Recuperar recetas desde Drive")
        self.btn_recuperar.clicked.connect(self.on_recuperar)

        # --- Lista de archivos ---
        self.lista = QListWidget()

        # --- Layout ---
        layout.addWidget(QLabel("Paciente"))
        layout.addWidget(self.paciente_nombre)
        layout.addWidget(self.paciente_edad)
        layout.addWidget(self.paciente_genero)
        layout.addWidget(self.paciente_correo)

        layout.addWidget(QLabel("Médico"))
        layout.addWidget(self.medico_nombre)
        layout.addWidget(self.medico_cedula)
        layout.addWidget(self.medico_especialidad)

        layout.addWidget(QLabel("Diagnóstico"))
        layout.addWidget(self.diagnostico)

        layout.addWidget(QLabel("Medicamentos"))
        layout.addWidget(self.medicamentos_text)

        layout.addWidget(self.btn_generar)
        layout.addWidget(self.btn_recuperar)
        layout.addWidget(QLabel("Archivos en Drive:"))
        layout.addWidget(self.lista)

        self.setLayout(layout)

    def init_drive(self):
        """Inicializa la conexión a Google Drive solo al presionar un botón"""
        if self.service and self.drive_folder_id:
            return
        try:
            self.service = get_drive_service()
            self.drive_folder_id = get_or_create_folder(self.service, "RecetasMedicas")
        except Exception as e:
            QMessageBox.critical(self, "Error Drive", f"No se pudo inicializar Drive:\n{e}")

    def on_generar(self):
        # --- Leer datos ---
        try:
            edad = int(self.paciente_edad.text())
        except ValueError:
            edad = None

        data = {
            "paciente": {
                "nombre": self.paciente_nombre.text(),
                "edad": edad,
                "genero": self.paciente_genero.text().upper() if self.paciente_genero.text().upper() in ['M','F'] else None,
                "correo": self.paciente_correo.text()
            },
            "medico": {
                "nombre": self.medico_nombre.text(),
                "cedula": self.medico_cedula.text(),
                "especialidad": self.medico_especialidad.text()
            },
            "diagnostico": self.diagnostico.toPlainText(),
            "medicamentos": []
        }

        for line in self.medicamentos_text.toPlainText().splitlines():
            if not line.strip():
                continue
            parts = line.split('|')
            data['medicamentos'].append({
                "nombre": parts[0].strip(),
                "dosis": parts[1].strip() if len(parts)>1 else "",
                "frecuencia": parts[2].strip() if len(parts)>2 else ""
            })

        # --- Generar XML y PDF ---
        xml_bytes, xml_filename = generar_xml_receta(data)
        xml_path = os.path.join(XML_FOLDER, xml_filename)
        with open(xml_path, 'wb') as f:
            f.write(xml_bytes)

        pdf_path = generar_pdf_receta(data)

        # --- Subir a Drive ---
        self.init_drive()
        if self.service and self.drive_folder_id:
            try:
                upload_file_bytes(self.service, xml_bytes, xml_filename, folder_id=self.drive_folder_id)
                QMessageBox.information(self, "Éxito", f"Archivo subido: {xml_filename}\nPDF generado: {pdf_path}")
            except Exception as e:
                QMessageBox.warning(self, "Drive", f"No se pudo subir a Drive:\n{e}")
        else:
            QMessageBox.information(self, "Info", f"PDF generado: {pdf_path}\nNo se subió a Drive.")

        # --- Guardar en DB ---
        session = Session()
        try:
            receta_id = insert_receta(session, data)
            QMessageBox.information(self, "DB", f"Receta guardada con id {receta_id}")
        except Exception as e_db:
            session.rollback()
            QMessageBox.warning(self, "DB", f"No se pudo guardar en DB:\n{e_db}")
        finally:
            session.close()

    def on_recuperar(self):
        self.init_drive()
        if not (self.service and self.drive_folder_id):
            QMessageBox.warning(self, "Drive", "No se puede recuperar archivos sin Drive.")
            return

        try:
            files = list_files_in_folder(self.service, self.drive_folder_id)
            self.lista.clear()
            if not files:
                QMessageBox.information(self, "Info", "No hay archivos en Drive")
                return

            session = Session()
            nuevos = 0
            for f in files:
                self.lista.addItem(f"{f['name']} | {f['id']} | {f['modifiedTime']}")
                if not f['name'].lower().endswith(".xml"):
                    continue

                # --- Descargar XML ---
                from drive_utils import download_file_bytes
                xml_bytes = download_file_bytes(self.service, f['id'])
                local_path = os.path.join(XML_FOLDER, f['name'])
                with open(local_path, 'wb') as xf:
                    xf.write(xml_bytes)

                # --- Leer datos desde XML ---
                from xml_utils import parse_xml_receta
                receta_data = parse_xml_receta(xml_bytes)

                # --- Verificar si ya existe ---
                paciente_correo = receta_data["paciente"]["correo"]
                medico_cedula = receta_data["medico"]["cedula"]
                diagnostico = receta_data["diagnostico"]

                existe = session.query(Receta).join(Paciente).join(Medico).filter(
                    Paciente.correo == paciente_correo,
                    Medico.cedula_profesional == medico_cedula,
                    Receta.diagnostico == diagnostico
                ).first()

                if not existe:
                    insert_receta(session, receta_data)
                    nuevos += 1

            session.close()
            QMessageBox.information(self, "Recuperación completa", f"Se insertaron {nuevos} nuevas recetas en la base de datos.")

        except Exception as e:
            QMessageBox.critical(self, "Drive", f"No se pudo recuperar o insertar archivos:\n{e}")



if __name__ == "__main__":
    try:
        print("Iniciando aplicación...")
        init_db()
        print("Base de datos inicializada.")
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print("Error crítico:", e)
