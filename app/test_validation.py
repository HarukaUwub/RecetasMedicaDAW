import unittest
import os
from xml_utils import validar_receta_xml

class TestRecetaValidation(unittest.TestCase):

    XSD_PATH = 'receta.xsd'

    def test_receta_valida(self):
        """Prueba que un XML válido pase la validación."""
        xml_valido_str = """<?xml version='1.0' encoding='UTF-8'?>
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
"""
        xml_valido = xml_valido_str.encode('utf-8')
        es_valido, errores = validar_receta_xml(xml_valido, self.XSD_PATH)
        self.assertTrue(es_valido, f"La validación debió pasar, pero falló con: {errores}")
        self.assertEqual(len(errores), 0)

    def test_receta_invalida_xsd(self):
        """Prueba que un XML que no cumple el XSD sea rechazado."""
        with open('receta_invalida.xml', 'rb') as f:
            xml_invalido_bytes = f.read()
        
        es_valido, errores = validar_receta_xml(xml_invalido_bytes, self.XSD_PATH)
        self.assertFalse(es_valido, "La validación debió fallar, pero pasó.")
        self.assertGreater(len(errores), 0, "Debería haber al menos un error de validación.")
        print(f"\nErrores de 'receta_invalida.xml': {errores}")

    def test_xml_mal_formado(self):
        """Prueba que un XML con sintaxis incorrecta sea rechazado."""
        xml_mal_formado = b"<receta><paciente><nombre>Test</nombre></paciente><receta>" # Tag sin cerrar
        es_valido, errores = validar_receta_xml(xml_mal_formado, self.XSD_PATH)
        self.assertFalse(es_valido, "La validación de sintaxis debió fallar.")
        self.assertIn("Error de sintaxis XML", errores[0])

if __name__ == '__main__':
    unittest.main()