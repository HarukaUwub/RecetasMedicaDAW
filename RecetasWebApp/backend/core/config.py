import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    JWT_SECRET: str = os.getenv("JWT_SECRET", "tu_secreto_super_seguro_aqui")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    
    GMAIL_EMAIL: str = os.getenv("GMAIL_EMAIL", "")
    GMAIL_PASSWORD: str = os.getenv("GMAIL_PASSWORD", "")

settings = Settings()
