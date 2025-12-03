import unittest
import os
import shutil
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base, RecetaLocal, PacienteLocal, MedicoLocal
from .sync_recetas import RecetaSyncManager

class TestRecetaSyncManager(unittest.TestCase):

    def setUp(self):
        """Configura un entorno de prueba limpio."""
        # Base de datos en memoria
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Mockear la sesión de la base de datos en el manager
        self.patcher_session = patch('app.sync_recetas.Session', self.TestingSessionLocal)
        self.patcher_session.start()

        # Mockear el servicio de Google Drive
        self.patcher_drive = patch('app.sync_recetas.get_drive_service')
        self.mock_get_drive_service = self.patcher_drive.start()
        self.mock_drive_service = MagicMock()
        self.mock_get_drive_service.return_value = self.mock_drive_service

        # Crear instancia del manager
        self.manager = RecetaSyncManager()
        self.manager.drive_service = self.mock_drive_service # Asignar servicio mockeado

        # XML de prueba
        self.xml_valido = b"""<?xml version='1.0' encoding='UTF-8'?>
<receta>
  <paciente><nombre>Paciente Receta Valida</nombre><edad>40</edad><genero>F</genero><correo>receta@valida.com</correo></paciente>
  <medico><nombre>Dr. Receta</nombre><cedula>REC001</cedula><especialidad>General</especialidad></medico>
  <diagnostico>Prueba de receta</diagnostico>
  <medicamentos/>
</receta>"""

        self.xml_invalido = b"<receta><paciente/></receta>"

    def tearDown(self):
        """Limpia el entorno después de cada prueba."""
        self.patcher_session.stop()
        self.patcher_drive.stop()

    def test_sincronizar_receta_valida_desde_drive(self):
        """Prueba el procesamiento exitoso de una receta válida desde Drive."""
        # Configurar mocks de Drive
        self.mock_drive_service.files().list().execute.return_value = {
            'files': [{'id': 'file123', 'name': 'receta_valida.xml'}]
        }
        self.mock_drive_service.files().get_media().execute.return_value = self.xml_valido

        # Mockear la descarga de bytes
        with patch('app.sync_recetas.download_file_bytes', return_value=self.xml_valido):
            # Ejecutar sincronización
            procesados, errores = self.manager.sincronizar_desde_drive()

        # Verificaciones
        self.assertEqual(procesados, 1)
        self.assertEqual(errores, 0)

        # Verificar en la BD
        session = self.TestingSessionLocal()
        paciente = session.query(PacienteLocal).filter_by(correo="receta@valida.com").first()
        self.assertIsNotNone(paciente)
        self.assertEqual(paciente.nombre, "Paciente Receta Valida")

        receta = session.query(RecetaLocal).filter_by(id_paciente_local=paciente.id).first()
        self.assertIsNotNone(receta)
        self.assertEqual(receta.diagnostico, "Prueba de receta")
        session.close()

        # Verificar que se movió el archivo
        self.manager.drive_service.files().update.assert_called()

    def test_sincronizar_receta_invalida_desde_drive(self):
        """Prueba que una receta inválida se marque como error."""
        # Configurar mocks de Drive
        self.mock_drive_service.files().list().execute.return_value = {
            'files': [{'id': 'file456', 'name': 'receta_invalida.xml'}]
        }

        # Mockear la descarga de bytes
        with patch('app.sync_recetas.download_file_bytes', return_value=self.xml_invalido):
            # Ejecutar sincronización
            procesados, errores = self.manager.sincronizar_desde_drive()

        # Verificaciones
        self.assertEqual(procesados, 0)
        self.assertEqual(errores, 1)

        # Verificar que no se insertó nada en la BD
        session = self.TestingSessionLocal()
        count = session.query(RecetaLocal).count()
        self.assertEqual(count, 0)
        session.close()

        # Verificar que se movió el archivo a la carpeta de errores
        self.manager.drive_service.files().update.assert_called()

if __name__ == '__main__':
    unittest.main(verbosity=2)