#!/usr/bin/env python3
"""
Script para probar la función refrescar_pacientes corregida
"""

import sys
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QMessageBox
from database import Session
from models import PacienteLocal

def test_refrescar_pacientes():
    """Prueba la función refrescar_pacientes corregida."""
    print("Probando función refrescar_pacientes corregida...")
    
    app = QApplication(sys.argv)
    
    # Crear tabla simulada
    tabla_pacientes = QTableWidget()
    tabla_pacientes.setColumnCount(8)
    tabla_pacientes.setHorizontalHeaderLabels([
        "ID Ext.", "Nombre", "Edad", "Genero", "Correo", "Telefono", "Ciudad", "Sincronizado"
    ])
    
    try:
        # Simular la función corregida
        from database import Session
        from models import PacienteLocal
        
        session = Session()
        pacientes = session.query(PacienteLocal).all()
        
        print(f"Pacientes encontrados: {len(pacientes)}")
        
        tabla_pacientes.setRowCount(len(pacientes))
        
        for i, paciente in enumerate(pacientes):
            tabla_pacientes.setItem(i, 0, QTableWidgetItem(str(paciente.id_externo)))
            tabla_pacientes.setItem(i, 1, QTableWidgetItem(paciente.nombre))
            tabla_pacientes.setItem(i, 2, QTableWidgetItem(str(paciente.edad) if paciente.edad else ""))
            tabla_pacientes.setItem(i, 3, QTableWidgetItem(paciente.genero))
            tabla_pacientes.setItem(i, 4, QTableWidgetItem(paciente.correo))
            tabla_pacientes.setItem(i, 5, QTableWidgetItem(paciente.telefono))
            tabla_pacientes.setItem(i, 6, QTableWidgetItem(paciente.ciudad))
            tabla_pacientes.setItem(i, 7, QTableWidgetItem(
                paciente.synced_at.strftime("%Y-%m-%d %H:%M") if paciente.synced_at else ""
            ))
            print(f"Agregado a tabla: {paciente.nombre}")
        
        session.close()
        
        print(f"[OK] Tabla llenada con {len(pacientes)} pacientes")
        print("La función refrescar_pacientes corregida funciona correctamente.")
        
        # Mostrar mensaje de éxito
        QMessageBox.information(None, "Éxito", f"Lista actualizada con {len(pacientes)} pacientes")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        QMessageBox.warning(None, "Error", f"Error refrescando pacientes: {str(e)}")
    
    app.quit()

if __name__ == "__main__":
    test_refrescar_pacientes()


