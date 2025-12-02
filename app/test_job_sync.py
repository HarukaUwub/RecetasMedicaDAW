import unittest
import os
import shutil
import logging
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Importamos las clases y modelos necesarios
from .job_sync import SyncJob
from .models import Base, Paciente, Receta

# Desactivar los logs del job durante las pruebas para mantener la salida limpia
logging.getLogger('SyncJobLogger').setLevel(logging.CRITICAL)
# Configurar un logger básico para ver los mensajes de las pruebas en la consola
logging.basicConfig(level=logging.INFO, format='%(asctime)s - TEST - %(levelname)s - %(message)s')


class TestSyncJob(unittest.TestCase):

    def setUp(self):
        """
        Se ejecuta antes de cada prueba.
        Configura un entorno de prueba limpio:
        1. Crea una carpeta temporal para simular el 'drive'.
        2. Configura una base de datos SQLite en memoria.
        """
        logging.info("Configurando entorno de prueba...")
        # 1. Configurar directorios de prueba temporales
        self.test_dir = "temp_test_drive"
        self.nuevos_dir = os.path.join(self.test_dir, 'nuevos')
        self.procesados_dir = os.path.join(self.test_dir, 'procesados')
        self.errores_dir = os.path.join(self.test_dir, 'errores')
        
        # Limpiar directorios de pruebas anteriores si existen
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        
        # Crear la estructura de carpetas para la prueba
        os.makedirs(self.nuevos_dir)
        os.makedirs(self.procesados_dir)
        os.makedirs(self.errores_dir)

        # 2. Configurar base de datos en memoria para aislamiento
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # 3. Instanciar el Job con la ruta de prueba
        self.job = SyncJob(base_path=self.test_dir)
        # Sobrescribimos la ruta del XSD para que la encuentre desde la ubicación de la prueba
        self.job.xsd_path = os.path.join(os.path.dirname(__file__), 'receta.xsd')

        # Definimos el XML válido como una variable de instancia para reutilizarlo
        self.xml_valido = """<?xml version='1.0' encoding='UTF-8'?>
<receta>
  <paciente><nombre>Paciente de Prueba</nombre><edad>42</edad><genero>M</genero><correo>test@exito.com</correo></paciente>
  <medico><nombre>Dr. Test</nombre><cedula>112233</cedula><especialidad>Tester</especialidad></medico>
  <diagnostico>Caso de prueba exitoso</diagnostico>
  <medicamentos><medicamento><nombre>Validacina</nombre><dosis>1 pastilla</dosis><frecuencia>Cada prueba</frecuencia></medicamento></medicamentos>
</receta>"""


    def tearDown(self):
        """
        Se ejecuta después de cada prueba.
        Limpia el entorno eliminando la carpeta temporal.
        """
        logging.info("Limpiando entorno de prueba...")
        shutil.rmtree(self.test_dir)

    def test_proceso_exitoso_archivo_valido(self):
        """
        Prueba el "camino feliz": un XML válido se procesa y mueve a 'procesados',
        y los datos se insertan en la BD.
        """
        # Crear el archivo en la carpeta 'nuevos'
        filename = "receta_valida.xml"
        with open(os.path.join(self.nuevos_dir, filename), "w") as f:
            f.write(self.xml_valido)

        # Usamos un 'patch' para asegurarnos de que el Job use nuestra sesión de BD de prueba
        with patch('app.job_sync.Session', self.TestingSessionLocal):
            # Ejecutar el job
            self.job.run()

        # --- Verificaciones ---
        # 1. El archivo fue movido a 'procesados'
        self.assertFalse(os.path.exists(os.path.join(self.nuevos_dir, filename)))
        self.assertTrue(os.path.exists(os.path.join(self.procesados_dir, filename)))
        self.assertEqual(len(os.listdir(self.errores_dir)), 0)

        # 2. Los datos están en la base de datos de prueba
        session = self.TestingSessionLocal()
        paciente = session.query(Paciente).filter_by(correo="test@exito.com").first()
        self.assertIsNotNone(paciente)
        self.assertEqual(paciente.nombre, "Paciente de Prueba")
        receta = session.query(Receta).filter_by(id_paciente=paciente.id).first()
        self.assertIsNotNone(receta)
        self.assertEqual(receta.diagnostico, "Caso de prueba exitoso")
        session.close()

    def test_proceso_fallido_archivo_invalido(self):
        """
        Prueba que un XML que no cumple con el XSD es movido a 'errores'.
        """
        # XML inválido (falta el diagnóstico)
        xml_invalido = """<?xml version='1.0' encoding='UTF-8'?>
<receta>
  <paciente><nombre>Paciente Invalido</nombre><edad>50</edad><genero>F</genero><correo>test@error.com</correo></paciente>
  <medico><nombre>Dr. Falla</nombre><cedula>000</cedula><especialidad>Errores</especialidad></medico>
</receta>"""
        
        filename = "receta_invalida.xml"
        with open(os.path.join(self.nuevos_dir, filename), "w") as f:
            f.write(xml_invalido)

        with patch('app.job_sync.Session', self.TestingSessionLocal):
            self.job.run()

        # --- Verificaciones ---
        # 1. El archivo fue movido a 'errores'
        self.assertFalse(os.path.exists(os.path.join(self.nuevos_dir, filename)))
        self.assertTrue(os.path.exists(os.path.join(self.errores_dir, filename)))
        self.assertEqual(len(os.listdir(self.procesados_dir)), 0)

        # 2. No se insertó nada en la base de datos
        session = self.TestingSessionLocal()
        paciente = session.query(Paciente).filter_by(correo="test@error.com").first()
        self.assertIsNone(paciente)
        session.close()

    @patch('app.job_sync.insert_receta')
    def test_proceso_fallido_por_error_db(self, mock_insert_receta):
        """
        Prueba que si `insert_receta` falla, el archivo se mueve a 'errores'.
        """
        # Simulamos que la función de inserción lanza una excepción
        mock_insert_receta.side_effect = Exception("Error simulado de base de datos")

        # Usamos el mismo XML válido de la primera prueba
        xml_valido_path = os.path.join(self.nuevos_dir, "receta_valida_para_db_error.xml")
        with open(xml_valido_path, "w") as f:
            f.write(self.xml_valido) # Reutilizamos el XML válido definido en setUp

        with patch('app.job_sync.Session', self.TestingSessionLocal):
            self.job.run()

        # El archivo debe moverse a 'errores'
        self.assertTrue(os.path.exists(os.path.join(self.errores_dir, os.path.basename(xml_valido_path))))
        self.assertFalse(os.path.exists(os.path.join(self.procesados_dir, os.path.basename(xml_valido_path))))

if __name__ == '__main__':
    unittest.main(verbosity=2)