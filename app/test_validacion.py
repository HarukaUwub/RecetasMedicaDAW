import unittest
import os
from xml_utils import validar_receta_xml

class TestRecetaValidation(unittest.TestCase):

    # Construir rutas absolutas para que las pruebas funcionen desde cualquier directorio
    XSD_PATH = os.path.join(os.path.dirname(__file__), 'receta.xsd')
    RECETA_VALIDA_PATH = os.path.join(os.path.dirname(__file__), 'receta_valida.xml')
    RECETA_INVALIDA_PATH = os.path.join(os.path.dirname(__file__), 'receta_invalida.xml')

    def test_receta_valida(self):
        """Prueba que un XML válido pase la validación."""
        with open(self.RECETA_VALIDA_PATH, 'rb') as f:
            xml_valido = f.read()
        es_valido, errores = validar_receta_xml(xml_valido, self.XSD_PATH)
        self.assertTrue(es_valido, f"La validación debió pasar, pero falló con: {errores}")
        self.assertEqual(len(errores), 0)

    def test_receta_invalida_xsd(self):
        """Prueba que un XML que no cumple el XSD sea rechazado."""
        with open(self.RECETA_INVALIDA_PATH, 'rb') as f:
            xml_invalido_bytes = f.read()
        
        es_valido, errores = validar_receta_xml(xml_invalido_bytes, self.XSD_PATH)
        self.assertFalse(es_valido, "La validación debió fallar, pero pasó.")
        self.assertGreater(len(errores), 0, "Debería haber al menos un error de validación.")
        # El validador indica que esperaba 'diagnostico' pero encontró 'medicamentos'.
        self.assertIn("Expected is ( diagnostico )", "".join(errores))

    def test_xml_mal_formado(self):
        """Prueba que un XML con sintaxis incorrecta sea rechazado."""
        xml_mal_formado = b"<receta><paciente><nombre>Test</nombre></paciente><receta>" # Tag sin cerrar
        es_valido, errores = validar_receta_xml(xml_mal_formado, self.XSD_PATH)
        self.assertFalse(es_valido, "La validación de sintaxis debió fallar.")
        self.assertTrue(any("Error de sintaxis XML" in e for e in errores))

if __name__ == '__main__':
    unittest.main()

