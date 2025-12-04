# backend/services/pdf_protect.py
import os
from PyPDF2 import PdfWriter, PdfReader
from core.logger import logger

def proteger_pdf_con_contrasena(pdf_path: str, contrasena: str, output_path: str = None) -> str:
    """
    Protege un PDF con contraseña.
    
    Args:
        pdf_path: ruta del PDF original
        contrasena: contraseña para proteger
        output_path: ruta de salida (si None, sobrescribe original)
    
    Returns:
        ruta del PDF protegido
    """
    if output_path is None:
        output_path = pdf_path.replace(".pdf", "_protegido.pdf")
    
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            writer.add_page(page)
        
        writer.encrypt(user_password=contrasena, owner_password=None, permissions_flag=-1)
        
        with open(output_path, "wb") as f:
            writer.write(f)
        
        logger.info(f"[PDF PROTECT] ✅ PDF protegido: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"[PDF PROTECT] ❌ Error: {e}", exc_info=True)
        raise

# Alias para compatibilidad
encrypt_pdf = proteger_pdf_con_contrasena
