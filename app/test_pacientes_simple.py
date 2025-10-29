#!/usr/bin/env python3
"""
Aplicación simplificada para probar la gestión de pacientes
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QMessageBox
)
from database import Session
from models import PacienteLocal

class TestPacientesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refrescar_pacientes()

    def init_ui(self):
        self.setWindowTitle("Test - Gestión de Pacientes")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()

        # Grupo para listar pacientes locales
        grupo_lista = QGroupBox("Pacientes Sincronizados (BD Local)")
        layout_lista = QVBoxLayout()

        self.tabla_pacientes = QTableWidget()
        self.tabla_pacientes.setColumnCount(8)
        self.tabla_pacientes.setHorizontalHeaderLabels([
            "ID Ext.", "Nombre", "Edad", "Genero", "Correo", "Telefono", "Ciudad", "Sincronizado"
        ])
        self.tabla_pacientes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.btn_refrescar_pacientes = QPushButton("Refrescar Lista")
        self.btn_refrescar_pacientes.clicked.connect(self.refrescar_pacientes)

        layout_lista.addWidget(self.tabla_pacientes)
        layout_lista.addWidget(self.btn_refrescar_pacientes)
        grupo_lista.setLayout(layout_lista)

        layout.addWidget(grupo_lista)
        self.setLayout(layout)

    def refrescar_pacientes(self):
        """Refresca la lista de pacientes locales."""
        try:
            session = Session()
            pacientes = session.query(PacienteLocal).all()
            
            print(f"Refrescando pacientes: {len(pacientes)} encontrados")
            
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
                
                print(f"Paciente {i+1}: {paciente.nombre}")
            
            session.close()
            
            QMessageBox.information(self, "Éxito", f"Lista actualizada con {len(pacientes)} pacientes")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error refrescando pacientes: {str(e)}")
            print(f"Error: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestPacientesWindow()
    window.show()
    sys.exit(app.exec_())


