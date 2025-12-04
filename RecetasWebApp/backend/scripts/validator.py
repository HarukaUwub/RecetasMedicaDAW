from services.xsd_validator import validar_xml_receta

xml = open("archivo.xml").read()
validar_xml_receta(xml)
print("XML válido")
