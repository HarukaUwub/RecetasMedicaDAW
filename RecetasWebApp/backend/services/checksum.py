import hashlib
from lxml import etree

def generar_contenido_checksum(root):
    """
    Construye el contenido EXACTO que se usó para generar el checksum.
    Ignora la etiqueta <checksum>.
    """
    partes = []
    for elem in root.iter():
        if elem.tag.endswith("checksum"):
            continue
        if elem.text and elem.text.strip():
            partes.append(elem.text.strip())
    return "".join(partes)


def validar_checksum(xml_path):
    # Cargar XML EXACTAMENTE como está
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(xml_path, parser)
    root = tree.getroot()

    # 1. Extraer checksum original
    checksum_original = root.find(".//checksum").text.strip()

    # 2. Eliminar checksum del árbol
    checksum_node = root.find(".//checksum")
    parent = checksum_node.getparent()
    parent.remove(checksum_node)

    # 3. Serializar SIN pretty print
    xml_bytes = etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=False,
        pretty_print=False
    )

    # 4. Calcular checksum real
    checksum_recalculado = hashlib.sha256(xml_bytes).hexdigest()

    return checksum_recalculado == checksum_original, checksum_recalculado, checksum_original

