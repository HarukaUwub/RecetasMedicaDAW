from lxml import etree
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
import hashlib
import xml.etree.ElementTree as ET
PDF_FOLDER = "pdfs"
os.makedirs(PDF_FOLDER, exist_ok=True)

XSD_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "receta.xsd")

def validar_xml_con_xsd(xml_bytes, xsd_path):
    """
    Valida un XML en formato de bytes contra un esquema XSD.
    Lanza una excepción si no es válido.
    """
    try:
        schema_root = etree.parse(xsd_path)
        schema = etree.XMLSchema(schema_root)
        xml_doc = etree.fromstring(xml_bytes)
        schema.assertValid(xml_doc)
        print("LOG: El XML es estructuralmente válido según el esquema XSD.")
        return True
    except etree.DocumentInvalid as e:
        print(f"ERROR DE VALIDACIÓN XSD: {e}")
        raise


def parse_xml_receta(xml_content: bytes):
    """Convierte un XML de receta a un diccionario igual al usado en insert_receta."""
    root = ET.fromstring(xml_content)

    def safe_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    data = {
        "paciente": {
            "nombre": root.findtext("paciente/nombre"),
            "edad": safe_int(root.findtext("paciente/edad")),
            "genero": root.findtext("paciente/genero"),
            "correo": root.findtext("paciente/correo")
        },
        "medico": {
            "nombre": root.findtext("medico/nombre"),
            "cedula": root.findtext("medico/cedula"),
            "especialidad": root.findtext("medico/especialidad")
        },
        "diagnostico": root.findtext("diagnostico"),
        "medicamentos": []
    }

    for med_el in root.findall("medicamentos/medicamento"):
        data["medicamentos"].append({
            "nombre": med_el.findtext("nombre"),
            "dosis": med_el.findtext("dosis"),
            "frecuencia": med_el.findtext("frecuencia")
        })

    return data

def agregar_checksum_a_xml(xml_bytes: bytes) -> bytes:
    """
    Calcula el checksum SHA-256 del XML y lo añade como un nuevo elemento.
    """
    # Calcular checksum del XML original
    checksum = hashlib.sha256(xml_bytes).hexdigest()

    # Parsear el XML para añadir el nuevo nodo
    root = etree.fromstring(xml_bytes)
    
    # Añadir el elemento checksum al final
    etree.SubElement(root, "checksum").text = checksum
    
    # Devolver el nuevo XML como bytes
    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')

def generar_xml_receta(data):
    # Añadir referencia al XSD en el elemento raíz
    xsi_namespace = "http://www.w3.org/2001/XMLSchema-instance"
    root = etree.Element(
        "receta",
        attrib={f"{{{xsi_namespace}}}noNamespaceSchemaLocation": "receta.xsd"},
        nsmap={'xsi': xsi_namespace}
    )

    paciente = etree.SubElement(root, "paciente")
    etree.SubElement(paciente, "nombre").text = data['paciente']['nombre']
    etree.SubElement(paciente, "edad").text = str(data['paciente'].get('edad',''))
    etree.SubElement(paciente, "genero").text = data['paciente'].get('genero','')
    etree.SubElement(paciente, "correo").text = data['paciente'].get('correo','')

    medico = etree.SubElement(root, "medico")
    etree.SubElement(medico, "nombre").text = data['medico']['nombre']
    etree.SubElement(medico, "cedula").text = data['medico'].get('cedula','')
    etree.SubElement(medico, "especialidad").text = data['medico'].get('especialidad','')

    etree.SubElement(root, "diagnostico").text = data.get('diagnostico','')

    meds = etree.SubElement(root, "medicamentos")
    for m in data.get('medicamentos', []):
        med = etree.SubElement(meds, "medicamento")
        etree.SubElement(med, "nombre").text = m['nombre']
        etree.SubElement(med, "dosis").text = m.get('dosis','')
        etree.SubElement(med, "frecuencia").text = m.get('frecuencia','')

    xml_bytes_sin_checksum = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    
    try:
        # --- Paso 1: Validación con XSD ---
        # Si la validación falla, `validar_xml_con_xsd` lanzará `etree.DocumentInvalid`.
        print("LOG: Iniciando validación del XML con el esquema XSD...")
        validar_xml_con_xsd(xml_bytes_sin_checksum, XSD_SCHEMA_PATH)
    except etree.DocumentInvalid:
        raise # Relanzar la excepción para que sea manejada por la UI en main.py

    # --- Paso 2: Añadir Checksum (solo si la validación fue exitosa) ---
    xml_bytes_con_checksum = agregar_checksum_a_xml(xml_bytes_sin_checksum)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in data['paciente']['nombre'] if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
    filename = f"receta_{safe_name}_{ts}.xml"
    return xml_bytes_con_checksum, filename
def parsear_xml_receta(xml_bytes):
    if isinstance(xml_bytes, bytes):
        xml_str = xml_bytes.decode('utf-8').strip()
    else:
        xml_str = str(xml_bytes).strip()

    root = etree.fromstring(xml_str.encode('utf-8'))

    paciente_elem = root.find('paciente')
    medico_elem = root.find('medico')
    diagnostico = root.findtext('diagnostico') or ""

    edad_text = paciente_elem.findtext('edad')
    try:
        edad = int(edad_text) if edad_text else None
    except ValueError:
        edad = None

    genero = (paciente_elem.findtext('genero') or "").upper()
    if genero not in ['M','F']:
        genero = None

    paciente = {
        "nombre": paciente_elem.findtext('nombre') or "",
        "edad": edad,
        "genero": genero,
        "correo": paciente_elem.findtext('correo') or None
    }

    medico = {
        "nombre": medico_elem.findtext('nombre') or "",
        "cedula": medico_elem.findtext('cedula') or None,
        "especialidad": medico_elem.findtext('especialidad') or None
    }

    medicamentos = []
    for m in root.findall('.//medicamento'):
        medicamentos.append({
            "nombre": m.findtext('nombre') or "",
            "dosis": m.findtext('dosis') or "",
            "frecuencia": m.findtext('frecuencia') or ""
        })

    return {
        "paciente": paciente,
        "medico": medico,
        "diagnostico": diagnostico,
        "medicamentos": medicamentos
    }



def generar_pdf_receta(data):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in data['paciente']['nombre'] if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
    filename = f"receta_{safe_name}_{ts}.pdf"
    path = os.path.join(PDF_FOLDER, filename)

    c = canvas.Canvas(path, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(50, 800, f"Receta Médica - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.drawString(50, 780, f"Paciente: {data['paciente']['nombre']} ({data['paciente'].get('edad','')} años, {data['paciente'].get('genero','')})")
    c.drawString(50, 760, f"Correo: {data['paciente'].get('correo','')}")
    c.drawString(50, 740, f"Médico: {data['medico']['nombre']} - {data['medico'].get('especialidad','')} ({data['medico'].get('cedula','')})")
    c.drawString(50, 720, "Diagnóstico:")
    text = c.beginText(50, 700)
    text.textLines(data.get('diagnostico',''))
    c.drawText(text)
    y = 650
    c.drawString(50, y, "Medicamentos:")
    y -= 20
    for m in data.get('medicamentos', []):
        c.drawString(60, y, f"- {m['nombre']} {m.get('dosis','')} {m.get('frecuencia','')}")
        y -= 20
    c.save()
    return path


def validar_receta_xml(xml_content: bytes, xsd_path: str):
    """
    Valida un contenido XML de receta contra un esquema XSD.
    
    Args:
        xml_content: El contenido del archivo XML como bytes.
        xsd_path: La ruta al archivo de esquema XSD.
        
    Returns:
        Un tuple (es_valido, errores), donde es_valido es un booleano
        y errores es una lista de mensajes de error.
    """
    try:
        schema_root = etree.parse(xsd_path)
        schema = etree.XMLSchema(schema_root)
        
        xml_doc = etree.fromstring(xml_content)
        schema.assertValid(xml_doc)
        
        return True, []
        
    except etree.XMLSyntaxError as e:
        return False, [f"Error de sintaxis XML: {e}"]
    except etree.DocumentInvalid as e:
        return False, [str(error) for error in e.error_log]
