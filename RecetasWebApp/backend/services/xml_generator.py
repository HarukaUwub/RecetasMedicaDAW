# backend/services/xml_generator.py
import uuid
from lxml import etree
from datetime import datetime
from core.logger import logger
import hashlib

XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

def generar_receta_xml_bytes(paciente_id, medico: dict, diagnostico: str, medicamentos: list, indicaciones: str = "", origen: str = "WEB", paciente_data: dict = None):
    receta = etree.Element("receta", nsmap={})
    # paciente
    paciente = etree.SubElement(receta, "paciente")
    etree.SubElement(paciente, "id").text = str(paciente_id)
    # Si hay datos completos del paciente, incluirlos
    if paciente_data:
        etree.SubElement(paciente, "nombre").text = paciente_data.get("nombre", "")
        etree.SubElement(paciente, "apellido").text = paciente_data.get("apellido", "")
        if paciente_data.get("fecha_nacimiento"):
            etree.SubElement(paciente, "fecha_nacimiento").text = paciente_data.get("fecha_nacimiento")
        if paciente_data.get("sexo"):
            etree.SubElement(paciente, "sexo").text = paciente_data.get("sexo")
        if paciente_data.get("telefono"):
            etree.SubElement(paciente, "telefono").text = paciente_data.get("telefono")
        if paciente_data.get("correo"):
            etree.SubElement(paciente, "correo").text = paciente_data.get("correo")
    # medico
    med = etree.SubElement(receta, "medico")
    for k in ("id","nombre","cedula","correo"):
        el = etree.SubElement(med, k)
        el.text = medico.get(k,"")
    # diagnostico
    etree.SubElement(receta, "diagnostico").text = diagnostico
    # medicamentos
    meds = etree.SubElement(receta, "medicamentos")
    for m in medicamentos:
        mm = etree.SubElement(meds, "medicamento")
        etree.SubElement(mm, "nombre").text = m.get("nombre","")
        etree.SubElement(mm, "dosis").text = m.get("dosis","")
        etree.SubElement(mm, "frecuencia").text = m.get("frecuencia","")
        etree.SubElement(mm, "duracion").text = m.get("duracion","")
    # indicaciones
    etree.SubElement(receta, "indicaciones").text = indicaciones
    # metadatos
    meta = etree.SubElement(receta, "metadatos")
    etree.SubElement(meta, "fecha_emision").text = datetime.utcnow().isoformat()
    checksum_el = etree.SubElement(meta, "checksum"); checksum_el.text = ""  # empty for checksum calc
    etree.SubElement(meta, "id_receta").text = str(uuid.uuid4())
    etree.SubElement(meta, "origen").text = origen

    # add xsi attr
    receta.set("{%s}noNamespaceSchemaLocation" % XSI_NS, "receta.xsd")
    receta.nsmap['xsi'] = XSI_NS

    # compute checksum (serialize with empty checksum)
    xml_bytes = etree.tostring(receta, pretty_print=True, xml_declaration=True, encoding="utf-8")
    checksum = hashlib.sha256(xml_bytes).hexdigest()
    checksum_el.text = checksum

    xml_bytes = etree.tostring(receta, pretty_print=True, xml_declaration=True, encoding="utf-8")
    return xml_bytes

def parse_receta_xml(xml_path: str) -> dict:
    """
    Parsea un archivo XML de receta y extrae los datos.
    """
    try:
        tree = etree.parse(xml_path)
        root = tree.getroot()

        # Extraer datos según estructura REAL del XML
        data = {
            "id_receta": root.findtext("metadatos/id_receta", "").strip(),
            "paciente_id": root.findtext("paciente/id", "").strip(),
            "medico_id": root.findtext("medico/id", "").strip(),
            "diagnostico": root.findtext("diagnostico", "").strip(),
            "indicaciones": root.findtext("indicaciones", "").strip(),
            "fecha_emision": root.findtext("metadatos/fecha_emision", datetime.utcnow().isoformat()).strip(),
            "checksum": root.findtext("metadatos/checksum", "").strip(),
        }

        # Validar campos obligatorios
        required = ["id_receta", "paciente_id", "medico_id"]
        for field in required:
            if not data[field]:
                raise ValueError(f"Campo obligatorio faltante: {field}")

        logger.info(f"[XML PARSE] ✅ Receta parseada: {data['id_receta']}")
        return data

    except Exception as e:
        logger.error(f"[XML PARSE] Error parseando {xml_path}: {e}")
        raise

def generar_receta_xml_bytes(
    paciente_id,
    medico: dict,
    diagnostico: str,
    medicamentos: list,
    indicaciones: str = "",
    origen: str = "WEB",
    paciente_data: dict = None
):

    # Crear raíz correctamente con namespace y schema
    receta = etree.Element(
        "receta",
        attrib={"{%s}noNamespaceSchemaLocation" % XSI_NS: "receta.xsd"},
        nsmap={"xsi": XSI_NS}
    )

    # --- PACIENTE ---
    paciente = etree.SubElement(receta, "paciente")
    etree.SubElement(paciente, "id").text = str(paciente_id)

    if paciente_data:
        for key in ["nombre", "apellido", "fecha_nacimiento", "sexo", "telefono", "correo"]:
            if paciente_data.get(key):
                etree.SubElement(paciente, key).text = paciente_data.get(key, "")

    # --- MEDICO ---
    med = etree.SubElement(receta, "medico")
    for k in ("id", "nombre", "cedula", "correo"):
        etree.SubElement(med, k).text = medico.get(k, "")

    # --- DIAGNOSTICO ---
    etree.SubElement(receta, "diagnostico").text = diagnostico

    # --- MEDICAMENTOS ---
    meds = etree.SubElement(receta, "medicamentos")
    for m in medicamentos:
        mm = etree.SubElement(meds, "medicamento")
        etree.SubElement(mm, "nombre").text = m.get("nombre", "")
        etree.SubElement(mm, "dosis").text = m.get("dosis", "")
        etree.SubElement(mm, "frecuencia").text = m.get("frecuencia", "")
        etree.SubElement(mm, "duracion").text = m.get("duracion", "")

    # --- INDICACIONES ---
    etree.SubElement(receta, "indicaciones").text = indicaciones

    # --- METADATOS ---
    meta = etree.SubElement(receta, "metadatos")
    etree.SubElement(meta, "fecha_emision").text = datetime.utcnow().isoformat()

    checksum_el = etree.SubElement(meta, "checksum")
    checksum_el.text = ""  # se rellena luego

    idr = etree.SubElement(meta, "id_receta")
    idr.text = str(uuid.uuid4())

    etree.SubElement(meta, "origen").text = origen

    # --- CHECKSUM sobre XML sin checksum ---
    xml_bytes_tmp = etree.tostring(
        receta, pretty_print=True, xml_declaration=True, encoding="utf-8"
    )

    checksum = hashlib.sha256(xml_bytes_tmp).hexdigest()
    checksum_el.text = checksum

    # XML final
    xml_bytes = etree.tostring(
        receta, pretty_print=True, xml_declaration=True, encoding="utf-8"
    )

    return xml_bytes
