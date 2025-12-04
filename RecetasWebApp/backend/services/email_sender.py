import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from core.logger import logger

class EmailSender:
    """Envía correos con PDF adjunto."""
    
    def __init__(self, provider: str = "gmail"):
        self.provider = provider.lower()
        
        if self.provider == "gmail":
            self.smtp_server = "smtp.gmail.com"
            self.smtp_port = 587
        elif self.provider == "outlook":
            self.smtp_server = "smtp-mail.outlook.com"
            self.smtp_port = 587
        else:
            raise ValueError(f"Provider no soportado: {provider}")
        
        self.email = os.getenv(f"{self.provider.upper()}_EMAIL", "wariom935@gmail.com").strip()
        self.password = os.getenv(f"{self.provider.upper()}_PASSWORD", "wstf fovr jcho wvgb").strip()
        
        logger.info(f"[EMAIL] Configurando {self.provider}: {self.email}")
        
        if not self.email or not self.password:
            logger.warning(f"[EMAIL] ⚠️ Credenciales incompletas para {self.provider}")
    
    def enviar_receta_pdf(self, 
                         email_destino: str, 
                         pdf_path: str, 
                         contrasena_pdf: str,
                         paciente_nombre: str,
                         medico_nombre: str) -> bool:
        """Envía el PDF de receta al paciente."""
        try:
            logger.info(f"[EMAIL] Verificando PDF: {pdf_path}")
            
            # Verificar que el PDF existe
            if not os.path.exists(pdf_path):
                logger.error(f"[EMAIL] ❌ PDF NO EXISTE: {pdf_path}")
                return False
            
            logger.info(f"[EMAIL] ✅ PDF encontrado: {os.path.getsize(pdf_path)} bytes")
            
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = email_destino
            msg['Subject'] = f"📋 Receta Médica - {paciente_nombre}"
            
            body = f"""
Estimado/a {paciente_nombre},

Le adjuntamos su receta médica del Dr/Dra. {medico_nombre}.

**IMPORTANTE:** El PDF está protegido con contraseña por seguridad.
Recibirá la contraseña en un segundo correo.

Por favor, NO comparta esta contraseña con terceros.

Saludos cordiales,
Sistema de Recetario Médico
            """.strip()
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Adjuntar PDF
            logger.info(f"[EMAIL] Adjuntando PDF...")
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                filename_only = os.path.basename(pdf_path)
                part.add_header('Content-Disposition', f'attachment; filename="{filename_only}"')
                msg.attach(part)
            
            logger.info(f"[EMAIL] Conectando a {self.smtp_server}:{self.smtp_port}...")
            
            # Enviar
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                logger.info(f"[EMAIL] TLS iniciado")
                server.login(self.email, self.password)
                logger.info(f"[EMAIL] Autenticado")
                server.send_message(msg)
                logger.info(f"[EMAIL] Mensaje enviado")
            
            logger.info(f"[EMAIL] ✅ PDF enviado a {email_destino}")
            return True
        
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[EMAIL] ❌ Error de autenticación: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"[EMAIL] ❌ Error SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"[EMAIL] ❌ Error: {e}", exc_info=True)
            return False
    
    def enviar_contrasena_pdf(self, 
                             email_destino: str, 
                             contrasena: str,
                             paciente_nombre: str) -> bool:
        """Envía la contraseña del PDF."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = email_destino
            msg['Subject'] = "🔐 Contraseña de Receta Médica"
            
            body = f"""
Estimado/a {paciente_nombre},

Como se indicó en el correo anterior, le enviamos la contraseña para acceder a su receta médica.

**Contraseña:** {contrasena}

⚠️ SEGURIDAD:
- No comparta esta contraseña
- Use la contraseña solo para acceder a su receta
- Si recibe esta información de forma sospechosa, contacte inmediatamente

Saludos cordiales,
Sistema de Recetario Médico
            """.strip()
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            logger.info(f"[EMAIL] Enviando contraseña a {email_destino}...")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            logger.info(f"[EMAIL] ✅ Contraseña enviada a {email_destino}")
            return True
        
        except Exception as e:
            logger.error(f"[EMAIL] ❌ Error enviando contraseña: {e}", exc_info=True)
            return False

def enviar_receta_completa(email_paciente: str, 
                          pdf_path: str, 
                          contrasena: str,
                          paciente_nombre: str,
                          medico_nombre: str,
                          provider: str = "gmail") -> bool:
    """Envía PDF + contraseña en dos correos separados."""
    
    if not email_paciente:
        logger.warning("[EMAIL] ⚠️ Email del paciente vacío")
        return False
    
    sender = EmailSender(provider)
    
    # Enviar PDF
    logger.info(f"[EMAIL] 📧 Enviando PDF...")
    pdf_ok = sender.enviar_receta_pdf(
        email_paciente, pdf_path, contrasena, paciente_nombre, medico_nombre
    )
    
    if not pdf_ok:
        logger.warning("[EMAIL] ⚠️ No se pudo enviar PDF")
        return False
    
    # Pausa
    logger.info("[EMAIL] ⏳ Esperando 3 segundos...")
    time.sleep(3)
    
    # Enviar contraseña
    logger.info(f"[EMAIL] 🔐 Enviando contraseña...")
    contrasena_ok = sender.enviar_contrasena_pdf(
        email_paciente, contrasena, paciente_nombre
    )
    
    return contrasena_ok
