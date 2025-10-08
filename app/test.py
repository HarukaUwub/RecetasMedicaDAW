# test_insert_xml.py
from database import Session, insert_receta
from xml_utils import parsear_xml_receta

# Cambia aquí la ruta de tu XML
XML_FILE = "receta_Miguel.xml"

def main():
    # Leer el XML
    with open(XML_FILE, "rb") as f:
        xml_bytes = f.read()
    
    # Parsear a diccionario
    receta_obj = parsear_xml_receta(xml_bytes)
    
    # Abrir sesión y probar inserción
    session = Session()
    try:
        receta_id = insert_receta(session, receta_obj)
        print(f"Receta insertada correctamente con id {receta_id}")
    except Exception as e:
        session.rollback()
        print("Error al insertar la receta:", e)
    finally:
        session.close()

if __name__ == "__main__":
    main()
