import unittest
import os
import logging
from xml_utils import validar_receta_xml

# Configuración de una consola de logs para ver el proceso de las pruebas
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TestRecetaValidation(unittest.TestCase):

    # Construir ruta absoluta para que la prueba funcione desde cualquier directorio
    XSD_PATH = os.path.join(os.path.dirname(__file__), 'receta.xsd')

    # Contenido de los XML para pruebas directas
    XML_VALIDO = """<?xml version='1.0' encoding='UTF-8'?>
<receta>
  <paciente>
    <nombre>Juan Perez</nombre>
    <edad>30</edad>
    <genero>M</genero>
    <correo>juan.perez@example.com</correo>
  </paciente>
  <medico>
    <nombre>Dr. Garcia</nombre>
    <cedula>123456</cedula>
    <especialidad>Cardiología</especialidad>
  </medico>
  <diagnostico>Hipertensión</diagnostico>
  <medicamentos>
    <medicamento>
      <nombre>Lisinopril</nombre>
      <dosis>10 mg</dosis>
      <frecuencia>1 vez al día</frecuencia>
    </medicamento>
  </medicamentos>
</receta>
""".encode('utf-8')

    XML_INVALIDO = """<?xml version='1.0' encoding='UTF-8'?>
<receta>
  <paciente>
    <nombre>Paciente Inválido</nombre>
    <edad>40</edad>
    <genero>M</genero>
    <correo>invalido@example.com</correo>
  </paciente>
  <medico>
    <nombre>Dr. Error</nombre>
    <cedula>000000</cedula>
    <especialidad>Pruebas</especialidad>
  </medico>
  <!-- Falta el diagnóstico obligatorio -->
  <medicamentos>
    <medicamento>
      <nombre>Placebo</nombre>
    </medicamento>
  </medicamentos>
</receta>
""".encode('utf-8')

    def test_receta_valida(self):
        """Prueba que un XML válido pase la validación."""
        logging.info("--- Iniciando prueba: test_receta_valida ---")
        logging.info("Validando un XML que se espera que sea VÁLIDO.")
        es_valido, errores = validar_receta_xml(self.XML_VALIDO, self.XSD_PATH)
        
        if es_valido:
            logging.info("Resultado: El XML ha sido validado como VÁLIDO (Correcto).")
        else:
            logging.error(f"Resultado: El XML ha sido validado como INVÁLIDO (Incorrecto). Errores: {errores}")
            
        self.assertTrue(es_valido, f"La validación debió pasar, pero falló con: {errores}")
        self.assertEqual(len(errores), 0)
        logging.info("--- Prueba finalizada: test_receta_valida ---")

    def test_receta_invalida_xsd(self):
        """Prueba que un XML que no cumple el XSD sea rechazado."""
        logging.info("--- Iniciando prueba: test_receta_invalida_xsd ---")
        logging.info("Validando un XML que se espera que sea INVÁLIDO por incumplimiento de XSD.")
        es_valido, errores = validar_receta_xml(self.XML_INVALIDO, self.XSD_PATH)
        
        if not es_valido:
            logging.info("Resultado: El XML ha sido validado como INVÁLIDO (Correcto).")
            logging.info(f"Errores de validación detectados: {errores}")
        else:
            logging.error("Resultado: El XML ha sido validado como VÁLIDO (Incorrecto).")
            
        self.assertFalse(es_valido, "La validación debió fallar, pero pasó.")
        self.assertGreater(len(errores), 0, "Debería haber al menos un error de validación.")
        self.assertIn("Expected is ( diagnostico )", "".join(errores))
        logging.info("--- Prueba finalizada: test_receta_invalida_xsd ---")

    def test_xml_mal_formado(self):
        """Prueba que un XML con sintaxis incorrecta sea rechazado."""
        logging.info("--- Iniciando prueba: test_xml_mal_formado ---")
        xml_mal_formado = b"<receta><paciente><nombre>Test</nombre></paciente><receta>"  # Tag sin cerrar
        logging.info("Validando un XML con sintaxis incorrecta (mal formado).")
        es_valido, errores = validar_receta_xml(xml_mal_formado, self.XSD_PATH)
        
        if not es_valido:
            logging.info("Resultado: El XML ha sido detectado como mal formado (Correcto).")
            logging.info(f"Errores de sintaxis detectados: {errores}")
        else:
            logging.error("Resultado: El XML mal formado fue considerado válido (Incorrecto).")
            
        self.assertFalse(es_valido, "La validación de sintaxis debió fallar.")
        self.assertTrue(any("Error de sintaxis XML" in e for e in errores))
        logging.info("--- Prueba finalizada: test_xml_mal_formado ---")

if __name__ == '__main__':
    logging.info("======================================================")
    logging.info("   INICIANDO SUITE DE PRUEBAS DE VALIDACIÓN DE XML   ")
    logging.info("======================================================")
    unittest.main(verbosity=2)