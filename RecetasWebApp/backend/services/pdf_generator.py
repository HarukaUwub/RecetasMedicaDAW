from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfgen import canvas
from datetime import datetime
from core.logger import logger
import os

def generate_receta_pdf(receta_data: dict, output_path: str) -> str:
    """
    Genera un PDF de receta a partir de un dict de datos.
    
    Args:
        receta_data: dict con id_receta, paciente_id, medico_id, diagnostico, indicaciones, etc
        output_path: ruta donde guardar el PDF
    
    Returns:
        Path del archivo generado
    """
    try:
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Crear PDF
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("RECETA MÉDICA", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Información básica
        info_data = [
            ["ID RECETA:", receta_data.get('id_receta', 'N/A')],
            ["FECHA EMISIÓN:", receta_data.get('fecha_emision', datetime.utcnow().isoformat())],
            ["PACIENTE ID:", receta_data.get('paciente_id', 'N/A')],
            ["MÉDICO ID:", receta_data.get('medico_id', 'N/A')],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3.5*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8e8e8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.4*inch))
        
        # Diagnóstico
        story.append(Paragraph("<b>DIAGNÓSTICO:</b>", styles['Heading2']))
        diagnostico = receta_data.get('diagnostico', 'No especificado')
        story.append(Paragraph(diagnostico, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Indicaciones
        story.append(Paragraph("<b>INDICACIONES/MEDICAMENTOS:</b>", styles['Heading2']))
        indicaciones = receta_data.get('indicaciones', 'No especificadas')
        story.append(Paragraph(indicaciones, styles['Normal']))
        story.append(Spacer(1, 0.5*inch))
        
        # Pie de página
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=1
        )
        story.append(Paragraph(
            f"Documento generado el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br/>Checksum: {receta_data.get('checksum', 'N/A')[:16]}...",
            footer_style
        ))
        
        # Construir PDF
        doc.build(story)
        logger.info(f"[PDF] ✅ PDF generado: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"[PDF] ❌ Error generando PDF: {e}", exc_info=True)
        raise
