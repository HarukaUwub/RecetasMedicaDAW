#!/usr/bin/env python3
"""
Simulador de Aplicación Web para gestión de pacientes.
Este script simula la funcionalidad de una aplicación web que:
1. Permite agregar/actualizar pacientes
2. Genera XML de pacientes
3. Sube XML a Google Drive
"""

import os
import sys
from datetime import datetime
from database import init_db
from models import Paciente
from paciente_xml_utils import generar_y_subir_paciente_xml, crear_paciente_desde_formulario
from drive_utils import get_drive_service

class WebAppSimulator:
    """Simulador de aplicación web para gestión de pacientes."""
    
    def __init__(self):
        self.Session = init_db()
        self.service = get_drive_service()
        
    def agregar_paciente(self, nombre, edad, genero, correo, telefono, 
                        calle, colonia, ciudad, estado, cp):
        """
        Agrega un nuevo paciente a la BD Web y genera XML para Drive.
        
        Returns:
            dict: Resultado de la operación
        """
        session = self.Session()
        try:
            # Crear paciente en BD Web
            nuevo_paciente = Paciente(
                nombre=nombre,
                edad=int(edad) if edad else None,
                genero=genero.upper() if genero else "",
                correo=correo,
                telefono=telefono,
                calle=calle,
                colonia=colonia,
                ciudad=ciudad,
                estado=estado,
                cp=cp,
                updated_at=datetime.now()
            )
            
            session.add(nuevo_paciente)
            session.commit()
            
            # Generar datos para XML
            paciente_data = {
                "id": nuevo_paciente.id,
                "nombre": nuevo_paciente.nombre,
                "edad": nuevo_paciente.edad,
                "genero": nuevo_paciente.genero,
                "correo": nuevo_paciente.correo,
                "telefono": nuevo_paciente.telefono,
                "calle": nuevo_paciente.calle,
                "colonia": nuevo_paciente.colonia,
                "ciudad": nuevo_paciente.ciudad,
                "estado": nuevo_paciente.estado,
                "cp": nuevo_paciente.cp
            }
            
            # Generar y subir XML
            file_id, filename = generar_y_subir_paciente_xml(
                self.service, paciente_data, "ALTA"
            )
            
            return {
                "success": True,
                "paciente_id": nuevo_paciente.id,
                "filename": filename,
                "file_id": file_id,
                "message": f"Paciente agregado exitosamente. XML: {filename}"
            }
            
        except Exception as e:
            session.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": f"Error agregando paciente: {str(e)}"
            }
        finally:
            session.close()
    
    def actualizar_paciente(self, paciente_id, **kwargs):
        """
        Actualiza un paciente existente en la BD Web y genera XML para Drive.
        
        Args:
            paciente_id: ID del paciente a actualizar
            **kwargs: Campos a actualizar
        
        Returns:
            dict: Resultado de la operación
        """
        session = self.Session()
        try:
            # Buscar paciente
            paciente = session.query(Paciente).filter_by(id=paciente_id).first()
            if not paciente:
                return {
                    "success": False,
                    "error": "Paciente no encontrado",
                    "message": f"Paciente con ID {paciente_id} no encontrado"
                }
            
            # Actualizar campos
            for campo, valor in kwargs.items():
                if hasattr(paciente, campo):
                    setattr(paciente, campo, valor)
            
            paciente.updated_at = datetime.now()
            session.commit()
            
            # Generar datos para XML
            paciente_data = {
                "id": paciente.id,
                "nombre": paciente.nombre,
                "edad": paciente.edad,
                "genero": paciente.genero,
                "correo": paciente.correo,
                "telefono": paciente.telefono,
                "calle": paciente.calle,
                "colonia": paciente.colonia,
                "ciudad": paciente.ciudad,
                "estado": paciente.estado,
                "cp": paciente.cp
            }
            
            # Generar y subir XML
            file_id, filename = generar_y_subir_paciente_xml(
                self.service, paciente_data, "ACTUALIZACION"
            )
            
            return {
                "success": True,
                "paciente_id": paciente.id,
                "filename": filename,
                "file_id": file_id,
                "message": f"Paciente actualizado exitosamente. XML: {filename}"
            }
            
        except Exception as e:
            session.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": f"Error actualizando paciente: {str(e)}"
            }
        finally:
            session.close()
    
    def listar_pacientes(self):
        """Lista todos los pacientes de la BD Web."""
        session = self.Session()
        try:
            pacientes = session.query(Paciente).all()
            return [
                {
                    "id": p.id,
                    "nombre": p.nombre,
                    "edad": p.edad,
                    "genero": p.genero,
                    "correo": p.correo,
                    "telefono": p.telefono,
                    "ciudad": p.ciudad,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None
                }
                for p in pacientes
            ]
        finally:
            session.close()
    
    def obtener_paciente(self, paciente_id):
        """Obtiene un paciente específico por ID."""
        session = self.Session()
        try:
            paciente = session.query(Paciente).filter_by(id=paciente_id).first()
            if paciente:
                return {
                    "id": paciente.id,
                    "nombre": paciente.nombre,
                    "edad": paciente.edad,
                    "genero": paciente.genero,
                    "correo": paciente.correo,
                    "telefono": paciente.telefono,
                    "calle": paciente.calle,
                    "colonia": paciente.colonia,
                    "ciudad": paciente.ciudad,
                    "estado": paciente.estado,
                    "cp": paciente.cp,
                    "updated_at": paciente.updated_at.isoformat() if paciente.updated_at else None
                }
            return None
        finally:
            session.close()

def main():
    """Función principal para demostrar la aplicación web."""
    print("=== Simulador de Aplicación Web - Gestión de Pacientes ===\n")
    
    app = WebAppSimulator()
    
    while True:
        print("\nOpciones disponibles:")
        print("1. Agregar nuevo paciente")
        print("2. Actualizar paciente existente")
        print("3. Listar pacientes")
        print("4. Ver paciente específico")
        print("5. Salir")
        
        opcion = input("\nSeleccione una opción (1-5): ").strip()
        
        if opcion == "1":
            print("\n--- Agregar Nuevo Paciente ---")
            nombre = input("Nombre: ").strip()
            edad = input("Edad (opcional): ").strip()
            genero = input("Género (M/F, opcional): ").strip()
            correo = input("Correo: ").strip()
            telefono = input("Teléfono (opcional): ").strip()
            calle = input("Calle (opcional): ").strip()
            colonia = input("Colonia (opcional): ").strip()
            ciudad = input("Ciudad (opcional): ").strip()
            estado = input("Estado (opcional): ").strip()
            cp = input("Código Postal (opcional): ").strip()
            
            resultado = app.agregar_paciente(
                nombre, edad, genero, correo, telefono,
                calle, colonia, ciudad, estado, cp
            )
            
            if resultado["success"]:
                print(f"✅ {resultado['message']}")
            else:
                print(f"❌ {resultado['message']}")
        
        elif opcion == "2":
            print("\n--- Actualizar Paciente ---")
            paciente_id = input("ID del paciente: ").strip()
            
            if not paciente_id.isdigit():
                print("❌ ID debe ser un número")
                continue
            
            paciente_id = int(paciente_id)
            
            # Mostrar datos actuales
            paciente_actual = app.obtener_paciente(paciente_id)
            if not paciente_actual:
                print(f"❌ Paciente con ID {paciente_id} no encontrado")
                continue
            
            print(f"\nDatos actuales del paciente {paciente_id}:")
            for campo, valor in paciente_actual.items():
                if campo != "id":
                    print(f"  {campo}: {valor}")
            
            print("\nIngrese nuevos valores (dejar vacío para mantener el actual):")
            nombre = input(f"Nombre [{paciente_actual['nombre']}]: ").strip()
            edad = input(f"Edad [{paciente_actual['edad']}]: ").strip()
            genero = input(f"Género [{paciente_actual['genero']}]: ").strip()
            correo = input(f"Correo [{paciente_actual['correo']}]: ").strip()
            telefono = input(f"Teléfono [{paciente_actual['telefono']}]: ").strip()
            calle = input(f"Calle [{paciente_actual['calle']}]: ").strip()
            colonia = input(f"Colonia [{paciente_actual['colonia']}]: ").strip()
            ciudad = input(f"Ciudad [{paciente_actual['ciudad']}]: ").strip()
            estado = input(f"Estado [{paciente_actual['estado']}]: ").strip()
            cp = input(f"Código Postal [{paciente_actual['cp']}]: ").strip()
            
            # Preparar datos de actualización
            datos_actualizacion = {}
            if nombre: datos_actualizacion["nombre"] = nombre
            if edad: datos_actualizacion["edad"] = int(edad)
            if genero: datos_actualizacion["genero"] = genero.upper()
            if correo: datos_actualizacion["correo"] = correo
            if telefono: datos_actualizacion["telefono"] = telefono
            if calle: datos_actualizacion["calle"] = calle
            if colonia: datos_actualizacion["colonia"] = colonia
            if ciudad: datos_actualizacion["ciudad"] = ciudad
            if estado: datos_actualizacion["estado"] = estado
            if cp: datos_actualizacion["cp"] = cp
            
            if datos_actualizacion:
                resultado = app.actualizar_paciente(paciente_id, **datos_actualizacion)
                if resultado["success"]:
                    print(f"✅ {resultado['message']}")
                else:
                    print(f"❌ {resultado['message']}")
            else:
                print("❌ No se ingresaron cambios")
        
        elif opcion == "3":
            print("\n--- Lista de Pacientes ---")
            pacientes = app.listar_pacientes()
            if pacientes:
                for p in pacientes:
                    print(f"ID: {p['id']} | {p['nombre']} | {p['edad']} años | {p['genero']} | {p['correo']}")
            else:
                print("No hay pacientes registrados")
        
        elif opcion == "4":
            print("\n--- Ver Paciente Específico ---")
            paciente_id = input("ID del paciente: ").strip()
            
            if not paciente_id.isdigit():
                print("❌ ID debe ser un número")
                continue
            
            paciente = app.obtener_paciente(int(paciente_id))
            if paciente:
                print(f"\nDatos del paciente {paciente_id}:")
                for campo, valor in paciente.items():
                    print(f"  {campo}: {valor}")
            else:
                print(f"❌ Paciente con ID {paciente_id} no encontrado")
        
        elif opcion == "5":
            print("¡Hasta luego!")
            break
        
        else:
            print("❌ Opción inválida")

if __name__ == "__main__":
    main()

