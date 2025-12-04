import os
from lxml import etree
from typing import Tuple
from core.logger import logger

def get_xsd_path(xsd_filename: str) -> str:
    """Obtiene la ruta absoluta del XSD relativa al backend."""
    backend_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    xsd_path = os.path.join(backend_dir, "xsd", xsd_filename)
    logger.debug(f"[XSD Path] Buscando: {xsd_path}")
    if not os.path.exists(xsd_path):
        logger.error(f"[XSD Path] NO EXISTE: {xsd_path}")
    return xsd_path

def validate_xml_against_xsd(xml_path: str, xsd_filename: str = None) -> Tuple[bool, str]:
    """
    Valida un archivo XML contra su XSD.
    
    Args:
        xml_path: ruta al archivo XML
        xsd_filename: nombre del archivo XSD (ej: "paciente.xsd")
                     Si es None, intenta deducirlo del nombre del XML
    
    Returns:
        Tupla (es_valido, mensaje_de_error)
        - es_valido: True si es válido, False si no
        - mensaje_de_error: "" si es válido, descripción del error si no
    """
    try:
        # Si xsd_filename es una ruta completa antigua, extraer solo el nombre
        if xsd_filename and os.path.sep in xsd_filename:
            xsd_filename = os.path.basename(xsd_filename)
        
        # Si no se proporciona XSD, deducir del nombre del XML
        if not xsd_filename:
            basename = os.path.basename(xml_path)
            if "paciente" in basename:
                xsd_filename = "paciente.xsd"
            elif "medico" in basename:
                xsd_filename = "medico.xsd"
            elif "receta" in basename:
                xsd_filename = "receta.xsd"
            else:
                return False, f"No se puede deducir XSD para {basename}"
        
        xsd_path = get_xsd_path(xsd_filename)
        
        if not os.path.exists(xsd_path):
            return False, f"Archivo XSD no encontrado: {xsd_path}"
        
        # Parsear el XSD
        with open(xsd_path, "r", encoding="utf-8") as f:
            xsd_doc = etree.parse(f)
        xsd_schema = etree.XMLSchema(xsd_doc)
        
        # Parsear el XML
        with open(xml_path, "r", encoding="utf-8") as f:
            xml_doc = etree.parse(f)
        
        # Validar
        is_valid = xsd_schema.validate(xml_doc)
        
        if is_valid:
            logger.info(f"[XSD] VALID: {os.path.basename(xml_path)}")
            return True, ""
        else:
            # Obtener mensaje de error detallado
            error_log = xsd_schema.error_log
            errors = "\n".join([str(e) for e in error_log])
            logger.error(f"[XSD] INVALID: {os.path.basename(xml_path)} - {errors}")
            return False, errors
    
    except FileNotFoundError as e:
        msg = f"Archivo no encontrado: {e}"
        logger.error(f"[XSD] {msg}")
        return False, msg
    except etree.XMLSyntaxError as e:
        msg = f"Error de sintaxis XML: {e}"
        logger.error(f"[XSD] {msg}")
        return False, msg
    except etree.XPathEvalError as e:
        msg = f"Error en XPath: {e}"
        logger.error(f"[XSD] {msg}")
        return False, msg
    except Exception as e:
        msg = f"Error de validación: {str(e)}"
        logger.error(f"[XSD] {msg}", exc_info=True)
        return False, msg


def validate_xml_string(xml_string: str, xsd_filename: str) -> Tuple[bool, str]:
    """
    Valida una cadena XML contra un XSD.
    
    Args:
        xml_string: contenido XML como string
        xsd_filename: nombre del archivo XSD (ej: "paciente.xsd")
    
    Returns:
        Tupla (es_valido, mensaje_de_error)
    """
    try:
        xsd_path = get_xsd_path(xsd_filename)
        
        if not os.path.exists(xsd_path):
            return False, f"Archivo XSD no encontrado: {xsd_path}"
        
        # Parsear el XSD
        with open(xsd_path, "r", encoding="utf-8") as f:
            xsd_doc = etree.parse(f)
        xsd_schema = etree.XMLSchema(xsd_doc)
        
        # Parsear el XML desde string
        xml_doc = etree.fromstring(xml_string.encode("utf-8"))
        
        # Validar
        is_valid = xsd_schema.validate(xml_doc)
        
        if is_valid:
            return True, ""
        else:
            error_log = xsd_schema.error_log
            errors = "\n".join([str(e) for e in error_log])
            return False, errors
    
    except Exception as e:
        msg = f"Error de validación: {str(e)}"
        logger.error(f"[XSD] {msg}", exc_info=True)
        return False, msg
