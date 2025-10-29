import os
import secrets
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.pdfencrypt import StandardEncryption
import smtplib
from email.message import EmailMessage

# Configuración SMTP desde entorno
SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", 587))
SMTP_USER = os.getenv("EMAIL_USERNAME")
SMTP_PASS = os.getenv("EMAIL_PASSWORD")
SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "Recetario")
PDF_PASS_PREFIX = os.getenv("PDF_PASS_PREFIX", "AAAA")


def generate_encrypted_pdf(receta_id: int, paciente_nombre: str, medicamentos: list, out_folder: str = "pdfs"):
    os.makedirs(out_folder, exist_ok=True)
    password = f"{PDF_PASS_PREFIX}-{receta_id}-{datetime.now().strftime('%Y%m%d')}"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"receta_{receta_id}_{ts}.pdf"
    path = os.path.join(out_folder, safe_name)

    user_pwd = password
    owner_pwd = secrets.token_urlsafe(8)
    enc = StandardEncryption(userPassword=user_pwd, ownerPassword=owner_pwd,
                             canPrint=1, canModify=0, canCopy=0, canAnnotate=0)
    c = canvas.Canvas(path, pagesize=A4, encrypt=enc)
    width, height = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 60, f"Receta ID: {receta_id}")
    c.setFont("Helvetica", 12)
    if paciente_nombre:
        c.drawString(50, height - 80, f"Paciente: {paciente_nombre}")
    c.drawString(50, height - 100, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    y = height - 140
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Medicamento")
    c.drawString(300, y, "Dosis")
    c.drawString(420, y, "Frecuencia")
    y -= 18
    c.setFont("Helvetica", 11)

    for med in medicamentos:
        if isinstance(med, str):
            parts = med.split('|')
            med = {"nombre": parts[0], "dosis": parts[1], "frecuencia": parts[2]}
        elif not isinstance(med, dict):
            continue
        if y < 80:
            c.showPage()
            y = height - 80
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Medicamento")
            c.drawString(300, y, "Dosis")
            c.drawString(420, y, "Frecuencia")
            y -= 18
            c.setFont("Helvetica", 11)
        c.drawString(50, y, med.get("nombre",""))
        c.drawString(300, y, med.get("dosis",""))
        c.drawString(420, y, med.get("frecuencia",""))
        y -= 18

    c.save()
    return path, password


def generate_pdf_with_password(receta_id, paciente=None, medico=None, medicamentos=None):
    paciente_nombre = paciente.get("nombre","") if isinstance(paciente, dict) else getattr(paciente,"nombre","")
    meds = medicamentos or []
    return generate_encrypted_pdf(receta_id, paciente_nombre, meds)


def send_email_with_attachment(smtp_server: str, smtp_port: int, username: str, password: str,
                               sender: str, recipient: str, subject: str, body: str, attachment_path: str = None):
    if not all([smtp_server, smtp_port, username, password]):
        raise RuntimeError("Credenciales SMTP no configuradas en variables de entorno")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)
    if attachment_path:
        with open(attachment_path, "rb") as f:
            data = f.read()
        msg.add_attachment(data, maintype="application", subtype="pdf", filename=os.path.basename(attachment_path))
    with smtplib.SMTP(smtp_server, smtp_port) as s:
        s.starttls()
        s.login(username, password)
        s.send_message(msg)
