# 📋 Recetario Médico - Sistema Integral Web + Desktop

Sistema completo de gestión de recetas médicas con generación de XML, validación XSD, PDF protegido y envío automático por correo.

## 🎯 Características

### Módulo Web
- ✅ Gestión de pacientes y médicos
- ✅ Generación de recetas en XML
- ✅ Validación contra XSD
- ✅ Checksum SHA-256
- ✅ Subida automática a Google Drive
- ✅ Base de datos web normalizada

### Módulo Local/Desktop
- ✅ Recepción automática desde Drive
- ✅ Validación XSD + Checksum
- ✅ Generación de PDF protegido con contraseña
- ✅ Envío automático por Gmail/Outlook
- ✅ Almacenamiento en BD local
- ✅ Gestión de archivos procesados/errores

## 📦 Tecnologías

- **Backend:** FastAPI + SQLAlchemy
- **Frontend:** React + Material-UI
- **BD:** SQLite
- **PDF:** ReportLab + PyPDF2
- **Email:** SMTP (Gmail/Outlook)
- **Drive:** Google Drive API
- **Validación:** lxml (XSD)

## 🚀 Instalación

### Requisitos
- Python 3.9+
- Node.js 14+
- pip
- npm

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### Frontend

```bash
cd client
npm install
```

## ⚙️ Configuración

### Backend (.env)

```
GOOGLE_DRIVE_FOLDER_ID=tu_id_aqui
GOOGLE_DRIVE_FOLDER_ID_MEDICOS=tu_id_aqui
GOOGLE_DRIVE_FOLDER_ID_PACIENTES=tu_id_aqui

GMAIL_EMAIL=tu_email@gmail.com
GMAIL_PASSWORD=tu_contraseña_app
OUTLOOK_EMAIL=tu_email@outlook.com
OUTLOOK_PASSWORD=tu_contraseña

JWT_SECRET=tu_secreto_jwt_aqui
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### Frontend (.env)

```
REACT_APP_API_URL=http://localhost:8000
```

## 🏃 Ejecutar

### Inicializar BD

```bash
python backend/scripts/init_db.py
```

### Backend

```bash
cd backend
python app.py
```

Accesible en: `http://localhost:8000`

API Docs: `http://localhost:8000/docs`

### Frontend

```bash
cd client
npm start
```

Accesible en: `http://localhost:3000`

## 📂 Estructura de Carpetas

```
backend/
├── database/
│   ├── base.py (SQLAlchemy setup)
│   ├── web_models.py (Tablas web)
│   └── local_models.py (Tablas locales)
├── services/
│   ├── xsd_validator.py (Validación XSD)
│   ├── xml_generator.py (Parser XML)
│   ├── pdf_generator.py (Generador PDF)
│   ├── pdf_protect.py (Protección con contraseña)
│   ├── email_sender.py (Envío correos)
│   └── drive_service.py (Google Drive API)
├── jobs/
│   ├── receiver_job.py (JOB recepción)
│   └── sender_job.py (JOB envío)
├── web/
│   └── routers/ (Endpoints FastAPI)
├── xsd/
│   ├── paciente.xsd
│   └── receta.xsd
├── data/
│   ├── drive_inbox/ (XMLs del Drive)
│   ├── drive_outbox/ (XMLs a enviar)
│   ├── procesados_inbox/ (XMLs procesados ✅)
│   ├── errores_inbox/ (XMLs con error ❌)
│   ├── pdfs/ (PDFs generados)
│   └── *.db (Bases de datos)
└── app.py (Punto de entrada)

client/
├── src/
│   ├── pages/ (Páginas React)
│   ├── components/ (Componentes reutilizables)
│   ├── layout/ (Layout)
│   └── api.js (Cliente HTTP)
└── package.json
```

## 🔄 Flujo de Trabajo

### 1. Crear Receta (Web)

```
Usuario → Formulario → XML generado → Checksum → Drive → BD Web
```

### 2. Procesar Receta (Desktop/Local)

```
Drive → JOB Receiver → Validación XSD → Checksum OK
→ PDF Generado → PDF Protegido → Email Enviado
→ BD Local → Archivos Procesados
```

## 📧 Flujo de Correos

1. **Correo 1:** PDF de receta adjunto (protegido)
2. **Pausa de 2 segundos**
3. **Correo 2:** Contraseña del PDF en texto plano

## 🗄️ Base de Datos

### BD Web (web.db)

```sql
-- Tablas
pacientes_web (id, nombre, apellido, fecha_nacimiento, sexo, telefono, correo)
medicos_web (id, nombre, cedula, correo)
recetas_web (id_receta, paciente_id, medico_id, diagnostico, indicaciones, xml_path, pdf_path, checksum, fecha_emision, origen, created_at)
```

### BD Local (local.db)

```sql
-- Tablas
recetas_local (id_receta, paciente_id, medico_id, diagnostico, indicaciones, xml_path, pdf_path, checksum, fecha_emision, origen, created_at)
```

## 📄 Estructura XML

### Receta

```xml
<?xml version="1.0" encoding="UTF-8"?>
<receta xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="receta.xsd">
    <id_receta>uuid-1234</id_receta>
    <paciente_id>1</paciente_id>
    <medico_id>1</medico_id>
    <diagnostico>Gripe A</diagnostico>
    <indicaciones>1 pastilla cada 8 horas</indicaciones>
    <metadatos>
        <fecha_emision>2025-12-02T20:00:00</fecha_emision>
        <checksum>abc123def456...</checksum>
        <origen>WEB</origen>
    </metadatos>
</receta>
```

## 🔐 Seguridad

- ✅ Validación XSD estricta
- ✅ Checksum SHA-256
- ✅ PDF protegido con contraseña
- ✅ Contraseña enviada en correo separado
- ✅ JWT para autenticación
- ✅ HTTPS recomendado

## 📊 Logs

Los logs están en `backend/app.log` con niveles:
- INFO: Operaciones normales
- WARNING: Advertencias
- ERROR: Errores procesables
- DEBUG: Información detallada

## 🧪 Pruebas

### Validar XML

```bash
python scripts/validator.py data/recetas_web/*.xml
```

### Generar Receta XML

```bash
python scripts/gen_xml_receta.py
```

## 📸 Evidencias

Documentar con pantallazos:
1. Sistema Web funcionando
2. Sistema Local recibiendo
3. JOB automático procesando
4. Correos recibidos
5. PDFs protegidos
6. Logs del sistema
7. BD Web y Local

## 🤝 Contribuyentes

- [Tu nombre]
- [Compañeros]

## 📝 Licencia

MIT

---

**Última actualización:** 2025-12-02



