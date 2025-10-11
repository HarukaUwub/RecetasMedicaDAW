# med_pdf_mailer.py
"""
Módulo para:
 - recuperar de la BD una receta (solo medicamentos y posología),
 - crear un PDF con esos datos,
 - protegerlo con contraseña (PDF cifrado),
 - enviar por correo el PDF y en un segundo correo la contraseña.

Requisitos pip:
  pip install reportlab python-dotenv

Variables de entorno (no incluir en control de versiones):
  EMAIL_SMTP_SERVER    (ej. smtp.gmail.com or smtp.office365.com)
  EMAIL_SMTP_PORT      (ej. 587)
  EMAIL_USERNAME       (usuario/email desde el que se envía)
  EMAIL_PASSWORD       (contraseña o app-password)
  EMAIL_SENDER_NAME    (opcional, texto "Mi Clinica")
  PDF_PASS_METHOD      ('deterministic' o 'random') - opcional. default 'deterministic'
  PDF_PASS_PREFIX      (opcional, por defecto 'AAAA')
"""

import os
import smtplib
import secrets
from datetime import datetime
from email.message import EmailMessage
from typing import Tuple

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.pdfencrypt import StandardEncryption

from database import Session  # Session factory
from models import Receta, Medicamento, Paciente  # usa tus modelos

# Optional helper for .env files
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---------------------------
# Config desde entorno
# ---------------------------
SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
SMTP_USER = os.getenv("EMAIL_USERNAME")
SMTP_PASS = os.getenv("EMAIL_PASSWORD")
SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "Recetario")
PDF_PASS_METHOD = os.getenv("PDF_PASS_METHOD", "deterministic").lower()
PDF_PASS_PREFIX = os.getenv("PDF_PASS_PREFIX", "AAAA")

# ---------------------------
# Funciones auxiliares
# ---------------------------
def build_password(receta_id: int) -> str:
    if PDF_PASS_METHOD == "random":
        return secrets.token_urlsafe(12)
    ts = datetime.now().strftime("%Y%m%d")
    return f"{PDF_PASS_PREFIX}-{receta_id}-{ts}"

def fetch_med_posologia(receta_id: int) -> Tuple[str, list]:
    session = Session()
    try:
        receta = session.query(Receta).filter_by(id=receta_id).first()
        if not receta:
            raise ValueError(f"Receta id={receta_id} no encontrada")
        paciente_email = getattr(receta.paciente, "correo", None) if receta.paciente else None
        meds = []
        for m in getattr(receta, "medicamentos", []):
            meds.append({
                "nombre": getattr(m, "nombre", ""),
                "dosis": getattr(m, "dosis", ""),
                "frecuencia": getattr(m, "frecuencia", "")
            })
        return paciente_email, meds
    finally:
        session.close()

def generate_encrypted_pdf(receta_id: int, paciente_nombre: str, medicamentos: list, out_folder: str = "pdfs"):
    """
    Genera un PDF con la lista de medicamentos y lo cifra con contraseña.
    Devuelve (pdf_path, password).

    medicamentos: puede ser:
        - lista de diccionarios con keys: 'nombre', 'dosis', 'frecuencia'
        - lista de strings con formato: "nombre|dosis|frecuencia"
    """
    import secrets
    from datetime import datetime
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.pdfencrypt import StandardEncryption
    import os

    os.makedirs(out_folder, exist_ok=True)

    # Generar contraseña determinística
    password = f"AAAA-{receta_id}-{datetime.now().strftime('%Y%m%d')}"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"receta_{receta_id}_{ts}.pdf"
    path = os.path.join(out_folder, safe_name)

    # Preparar cifrado
    user_pwd = password
    owner_pwd = secrets.token_urlsafe(8)
    enc = StandardEncryption(userPassword=user_pwd, ownerPassword=owner_pwd,
                             canPrint=1, canModify=0, canCopy=0, canAnnotate=0)

    # Crear canvas cifrado
    c = canvas.Canvas(path, pagesize=A4, encrypt=enc)
    width, height = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 60, f"Receta ID: {receta_id}")
    c.setFont("Helvetica", 12)
    if paciente_nombre:
        c.drawString(50, height - 80, f"Paciente: {paciente_nombre}")
    c.drawString(50, height - 100, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Encabezado medicamentos
    y = height - 140
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Medicamento")
    c.drawString(300, y, "Dosis")
    c.drawString(420, y, "Frecuencia")
    y -= 18
    c.setFont("Helvetica", 11)

    for med in medicamentos:
        # Convertir string a diccionario si es necesario
        if isinstance(med, str):
            parts = med.split('|')
            med = {
                "nombre": parts[0].strip() if len(parts) > 0 else "",
                "dosis": parts[1].strip() if len(parts) > 1 else "",
                "frecuencia": parts[2].strip() if len(parts) > 2 else ""
            }
        elif not isinstance(med, dict):
            # ignorar si no es dict ni str
            continue

        if y < 80:
            c.showPage()
            y = height - 80
            # repetir encabezado
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Medicamento")
            c.drawString(300, y, "Dosis")
            c.drawString(420, y, "Frecuencia")
            y -= 18
            c.setFont("Helvetica", 11)

        c.drawString(50, y, med.get("nombre", ""))
        c.drawString(300, y, med.get("dosis", ""))
        c.drawString(420, y, med.get("frecuencia", ""))
        y -= 18

    c.save()
    return path, password



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
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(username, password)
        s.send_message(msg)

# ---------------------------
# Función principal (API)
# ---------------------------
def send_receta_pdf_by_email(receta_id: int, recipient_email: str = None, send_password_in_second_email: bool = True):
    paciente_email, meds = fetch_med_posologia(receta_id)
    if recipient_email is None:
        if not paciente_email:
            raise ValueError("No se indicó recipient_email y la receta no tiene correo del paciente.")
        recipient_email = paciente_email

    session = Session()
    paciente_nombre = ""
    try:
        receta = session.query(Receta).filter_by(id=receta_id).first()
        if receta and receta.paciente:
            paciente_nombre = getattr(receta.paciente, "nombre", "") or ""
    finally:
        session.close()

    pdf_path, pdf_password = generate_encrypted_pdf(receta_id, paciente_nombre, meds)

    sender_str = f"{SENDER_NAME} <{SMTP_USER}>" if SMTP_USER else SENDER_NAME
    subject1 = f"Receta médica (ID {receta_id})"
    body1 = "Adjuntamos su receta médica en formato PDF. Por seguridad la contraseña se enviará en un correo separado."
    send_email_with_attachment(SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS,
                               sender_str, recipient_email, subject1, body1, attachment_path=pdf_path)

    if send_password_in_second_email:
        subject2 = f"Contraseña para abrir su receta (ID {receta_id})"
        body2 = f"La contraseña para abrir su PDF es:\n\n{pdf_password}\n\nPor favor, no comparta esta contraseña."
        send_email_with_attachment(SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS,
                                   sender_str, recipient_email, subject2, body2, attachment_path=None)

    return pdf_path, pdf_password

# === Compatibilidad con GUI anterior ===
def generate_pdf_with_password(receta_id, paciente=None, medico=None, medicamentos=None, pdf_path=None, password=None):
    paciente_nombre = ""
    if isinstance(paciente, dict):
        paciente_nombre = paciente.get("nombre", "") or ""
    elif hasattr(paciente, "nombre"):
        paciente_nombre = getattr(paciente, "nombre", "") or ""

    meds = medicamentos or []
    return generate_encrypted_pdf(receta_id, paciente_nombre, meds)
