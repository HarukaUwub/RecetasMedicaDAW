import os
import hashlib
from datetime import datetime
from lxml import etree
from lxml.etree import Element, SubElement, tostring

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATIENT_XSD_FILE_PATH = os.path.join(BASE_DIR, 'paciente.xsd')

def generar_xml_paciente(paciente_data, operacion="ALTA"):
    """
    Genera XML de paciente según el esquema definido.
    
    Args:
        paciente_data: Diccionario con datos del paciente
        operacion: "ALTA" o "ACTUALIZACION"
    
    Returns:
        tuple: (xml_bytes, filename)
    """
    # Crear elemento raíz
    paciente = Element("paciente")
    
    # Datos básicos
    paciente_id = paciente_data.get("id")
    if paciente_id is None:
        # Generar ID temporal único si no existe
        import time
        paciente_id = int(time.time() * 1000) % 100000
    SubElement(paciente, "id").text = str(paciente_id)
    SubElement(paciente, "nombre").text = paciente_data.get("nombre", "")
    SubElement(paciente, "edad").text = str(paciente_data.get("edad", ""))
    SubElement(paciente, "genero").text = paciente_data.get("genero", "")
    SubElement(paciente, "correo").text = paciente_data.get("correo", "")
    SubElement(paciente, "telefono").text = paciente_data.get("telefono", "")
    
    # Dirección
    direccion = SubElement(paciente, "direccion")
    SubElement(direccion, "calle").text = paciente_data.get("calle", "")
    SubElement(direccion, "colonia").text = paciente_data.get("colonia", "")
    SubElement(direccion, "ciudad").text = paciente_data.get("ciudad", "")
    SubElement(direccion, "estado").text = paciente_data.get("estado", "")
    SubElement(direccion, "cp").text = paciente_data.get("cp", "")
    
    # Metadatos
    metadatos = SubElement(paciente, "metadatos")
    SubElement(metadatos, "origen").text = "WEB"
    SubElement(metadatos, "fecha_evento").text = datetime.now().isoformat()
    SubElement(metadatos, "operacion").text = operacion
    SubElement(metadatos, "checksum").text = ""  # Placeholder
    
    # Generar XML inicial
    xml_str = tostring(paciente, encoding='utf-8', xml_declaration=True, pretty_print=True)
    
    # Calcular checksum
    checksum = hashlib.md5(xml_str).hexdigest()
    metadatos.find("checksum").text = checksum
    
    # Regenerar XML con checksum
    xml_str = tostring(paciente, encoding='utf-8', xml_declaration=True, pretty_print=True)
    
    # Generar nombre de archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"paciente_{paciente_id}_{timestamp}.xml"
    
    return xml_str, filename

def validar_xml_con_xsd(xml_bytes, xsd_path=PATIENT_XSD_FILE_PATH):
    """
    Valida XML contra el esquema XSD.
    
    Args:
        xml_bytes: Contenido XML en bytes
        xsd_path: Ruta al archivo XSD
    
    Returns:
        tuple: (es_valido, errores)
    """
    try:
        # Cargar esquema XSD
        if not os.path.exists(xsd_path):
            return False, [f"Archivo XSD no encontrado: {xsd_path}"]
        
        with open(xsd_path, 'rb') as f:
            xsd_doc = etree.parse(f)
        
        schema = etree.XMLSchema(xsd_doc)
        
        # Parsear XML
        xml_doc = etree.fromstring(xml_bytes)
        
        # Validar
        schema.assertValid(xml_doc)
        return True, []
        
    except etree.XMLSyntaxError as e:
        return False, [f"Error de sintaxis XML: {e}"]
    except etree.DocumentInvalid as e:
        return False, [f"Error de validación XSD: {e}"]
    except Exception as e:
        return False, [f"Error inesperado: {e}"]

def parse_xml_paciente(xml_bytes):
    """
    Parsea XML de paciente y extrae los datos.
    
    Args:
        xml_bytes: Contenido XML en bytes
    
    Returns:
        dict: Datos del paciente parseados
    """
    try:
        root = etree.fromstring(xml_bytes)
        
        # Extraer datos básicos
        paciente_data = {
            "id": int(root.find("id").text) if root.find("id") is not None and root.find("id").text else None,
            "nombre": root.find("nombre").text if root.find("nombre") is not None else "",
            "edad": int(root.find("edad").text) if root.find("edad") is not None and root.find("edad").text else None,
            "genero": root.find("genero").text if root.find("genero") is not None else "",
            "correo": root.find("correo").text if root.find("correo") is not None else "",
            "telefono": root.find("telefono").text if root.find("telefono") is not None else "",
        }
        
        # Extraer dirección
        direccion = root.find("direccion")
        if direccion is not None:
            paciente_data.update({
                "calle": direccion.find("calle").text if direccion.find("calle") is not None else "",
                "colonia": direccion.find("colonia").text if direccion.find("colonia") is not None else "",
                "ciudad": direccion.find("ciudad").text if direccion.find("ciudad") is not None else "",
                "estado": direccion.find("estado").text if direccion.find("estado") is not None else "",
                "cp": direccion.find("cp").text if direccion.find("cp") is not None else "",
            })
        
        # Extraer metadatos
        metadatos = root.find("metadatos")
        if metadatos is not None:
            paciente_data.update({
                "origen": metadatos.find("origen").text if metadatos.find("origen") is not None else "",
                "fecha_evento": metadatos.find("fecha_evento").text if metadatos.find("fecha_evento") is not None else "",
                "operacion": metadatos.find("operacion").text if metadatos.find("operacion") is not None else "",
                "checksum": metadatos.find("checksum").text if metadatos.find("checksum") is not None else "",
            })
        
        return paciente_data
        
    except Exception as e:
        print(f"Error parseando XML de paciente: {e}")
        return {}

def crear_paciente_desde_formulario(nombre, edad, genero, correo, telefono, 
                                   calle, colonia, ciudad, estado, cp):
    """
    Crea un diccionario de paciente desde datos de formulario.
    
    Returns:
        dict: Datos del paciente estructurados
    """
    # Generar ID temporal único basado en timestamp
    import time
    id_temporal = int(time.time() * 1000) % 100000  # ID de 5 dígitos
    
    return {
        "id": id_temporal,  # ID temporal único
        "nombre": nombre,
        "edad": int(edad) if edad else None,
        "genero": genero.upper() if genero else "",
        "correo": correo,
        "telefono": telefono,
        "calle": calle,
        "colonia": colonia,
        "ciudad": ciudad,
        "estado": estado,
        "cp": cp
    }

def generar_y_subir_paciente_xml(service, paciente_data, operacion="ALTA"):
    """
    Genera XML de paciente y lo sube a Drive.
    
    Args:
        service: Servicio de Google Drive
        paciente_data: Datos del paciente
        operacion: "ALTA" o "ACTUALIZACION"
    
    Returns:
        tuple: (file_id, filename) o (None, filename) si falla
    """
    try:
        # Generar XML
        xml_bytes, filename = generar_xml_paciente(paciente_data, operacion)
        
        # Validar XML
        es_valido, errores = validar_xml_con_xsd(xml_bytes)
        if not es_valido:
            print(f"XML inválido: {errores}")
            return None, filename
        
        # Subir a Drive
        from drive_utils import upload_paciente_xml
        file_id = upload_paciente_xml(service, xml_bytes, filename)
        
        return file_id, filename
        
    except Exception as e:
        print(f"Error generando y subiendo XML de paciente: {e}")
        return None, filename
