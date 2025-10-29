# Sistema de Integración de Aplicaciones - Sincronización de Pacientes

Este proyecto implementa la integración entre una **Aplicación Web** y una **Aplicación de Escritorio** usando **Google Drive** como puente para sincronizar datos de pacientes en formato XML.

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    XML    ┌─────────────────┐    XML    ┌─────────────────┐
│   Aplicación    │ ────────► │   Google Drive  │ ◄──────── │   Aplicación    │
│      Web        │           │   (Servidor      │           │   Local/Escrit. │
│   (BD Web)      │           │    Proxy)       │           │   (BD Local)    │
└─────────────────┘           └─────────────────┘           └─────────────────┘
```

### Componentes Principales

1. **BD Web**: Almacena pacientes en la aplicación web
2. **BD Local**: Almacena pacientes sincronizados en la aplicación de escritorio
3. **Google Drive**: Carpeta compartida con subcarpetas organizadas
4. **XML**: Formato de intercambio con validación XSD

## 📁 Estructura de Archivos

```
├── paciente.xsd                    # Esquema de validación XML
├── paciente_xml_utils.py          # Utilidades para generar/parsear XML
├── sync_pacientes.py              # Lógica de sincronización
├── web_app_simulator.py           # Simulador de aplicación web
├── main_with_sync.py              # Aplicación de escritorio con sync
├── demo_completo.py               # Script de demostración
├── drive_utils.py                 # Utilidades de Google Drive (extendido)
├── models.py                      # Modelos de BD (actualizado)
└── data_local/                    # Archivos locales de respaldo
    ├── pacientes/                 # XMLs de pacientes locales
    ├── procesados/               # Archivos procesados
    └── errores/                  # Archivos con errores
```

## 🚀 Instalación y Configuración

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar Google Drive API

1. Crear proyecto en [Google Cloud Console](https://console.cloud.google.com/)
2. Habilitar Google Drive API
3. Crear credenciales OAuth 2.0
4. Descargar `credentials.json` al directorio del proyecto

### 3. Configurar Variables de Entorno (Opcional)

```bash
# Para envío de correos
export EMAIL_SMTP_SERVER="smtp.gmail.com"
export EMAIL_SMTP_PORT="587"
export EMAIL_USERNAME="tu_email@gmail.com"
export EMAIL_PASSWORD="tu_contraseña_app"
export EMAIL_SENDER_NAME="Recetario Médico"
```

## 📋 Uso del Sistema

### 1. Demostración Completa

```bash
python demo_completo.py
```

Este script ejecuta todas las funcionalidades del sistema:
- Validación de XML
- Operaciones con Google Drive
- Manejo de errores
- Simulación de aplicación web
- Sincronización local

### 2. Simulador de Aplicación Web

```bash
python web_app_simulator.py
```

**Funcionalidades:**
- ✅ Agregar nuevos pacientes
- ✅ Actualizar pacientes existentes
- ✅ Generar XML automáticamente
- ✅ Subir XML a Google Drive
- ✅ Listar pacientes

**Flujo:**
1. Agregar paciente → Genera XML → Sube a Drive
2. Actualizar paciente → Genera XML → Sube a Drive
3. Los XMLs se almacenan en carpeta `pendientes/`

### 3. Aplicación de Escritorio con Sincronización

```bash
python main_with_sync.py
```

**Funcionalidades:**
- ✅ Interfaz gráfica con pestañas
- ✅ Gestión de recetas (funcionalidad original)
- ✅ Gestión de pacientes
- ✅ Sincronización manual y automática
- ✅ Estadísticas de sincronización
- ✅ Control de errores

**Pestañas:**
- **Recetas Médicas**: Funcionalidad original
- **Gestión de Pacientes**: Agregar pacientes y generar XML
- **Sincronización**: Control de sync y estadísticas

### 4. Sincronización Manual

```python
from sync_pacientes import sincronizar_pacientes_manual

resultado = sincronizar_pacientes_manual()
print(f"Procesados: {resultado['procesados']}")
print(f"Actualizados: {resultado['actualizados']}")
print(f"Errores: {resultado['errores']}")
```

## 🔄 Flujo de Sincronización

### Desde Aplicación Web

1. **Agregar Paciente**:
   ```
   Usuario → Formulario → BD Web → XML → Drive (pendientes/)
   ```

2. **Actualizar Paciente**:
   ```
   Usuario → Formulario → BD Web → XML → Drive (pendientes/)
   ```

### Desde Aplicación Local

1. **Sincronización Manual**:
   ```
   Botón Sync → Drive (pendientes/) → Validar XML → BD Local → Drive (procesados/)
   ```

2. **Sincronización Automática**:
   ```
   Timer (15 min) → Drive (pendientes/) → Validar XML → BD Local → Drive (procesados/)
   ```

## 📊 Estructura de Datos

### Esquema XML de Paciente

```xml
<?xml version="1.0" encoding="UTF-8"?>
<paciente>
  <id>123</id>
  <nombre>Juan Pérez</nombre>
  <edad>35</edad>
  <genero>M</genero>
  <correo>juan.perez@gmail.com</correo>
  <telefono>333-123-4567</telefono>
  <direccion>
    <calle>Pavo 30</calle>
    <colonia>Centro</colonia>
    <ciudad>Guadalajara</ciudad>
    <estado>Jalisco</estado>
    <cp>44100</cp>
  </direccion>
  <metadatos>
    <origen>WEB</origen>
    <fecha_evento>2025-10-20T17:20:00</fecha_evento>
    <operacion>ALTA</operacion>
    <checksum>abc123...</checksum>
  </metadatos>
</paciente>
```

### Convención de Nombres de Archivos

```
paciente_[idPaciente]_[AAAAMMDD_HHMMSS].xml
```

**Ejemplos:**
- `paciente_123_20251021_143022.xml`
- `paciente_456_20251021_143022_OK.xml` (procesado)
- `paciente_789_20251021_143022_ERR.xml` (error)

### Estructura de Carpetas en Drive

```
PacientesSync/
├── pendientes/          # XMLs nuevos por procesar
├── procesados/          # XMLs procesados exitosamente
└── errores/             # XMLs con errores
```

## 🛡️ Seguridad y Validación

### Validación XSD

- ✅ Campos obligatorios
- ✅ Tipos de datos correctos
- ✅ Valores enum (M/F para género)
- ✅ Estructura XML válida

### Control de Integridad

- ✅ Checksum MD5 para verificar integridad
- ✅ Validación de duplicados
- ✅ Control de archivos procesados
- ✅ Manejo de errores robusto

### Fallback Local

- ✅ Funciona sin conexión a Drive
- ✅ Archivos locales como respaldo
- ✅ Sincronización cuando se restaura conexión

## 📈 Monitoreo y Estadísticas

### Tabla de Control (`sync_archivos`)

```sql
CREATE TABLE sync_archivos (
    id INTEGER PRIMARY KEY,
    nombre_archivo VARCHAR(200) NOT NULL,
    fecha_procesado DATETIME DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL,  -- PROCESADO, ERROR
    detalle_error TEXT,
    checksum VARCHAR(64)
);
```

### Estadísticas Disponibles

- Total de pacientes locales
- Archivos procesados exitosamente
- Archivos con errores
- Última sincronización

## 🔧 Configuración Avanzada

### Sincronización Automática

```python
# Cambiar intervalo de sincronización
self.sync_timer.start(30 * 60 * 1000)  # 30 minutos
```

### Limpieza de Archivos Antiguos

```python
from sync_pacientes import PacienteSyncManager

manager = PacienteSyncManager()
eliminados = manager.limpiar_archivos_procesados(dias_antiguedad=30)
print(f"Registros eliminados: {eliminados}")
```

### Configuración de Base de Datos

El sistema soporta:
- ✅ MySQL (producción)
- ✅ SQLite (desarrollo/local)
- ✅ Fallback automático

## 🐛 Solución de Problemas

### Error: "Drive no disponible"

**Causa**: Credenciales de Google Drive no configuradas
**Solución**: 
1. Verificar `credentials.json`
2. Ejecutar autenticación OAuth
3. Verificar `token.json`

### Error: "XML inválido"

**Causa**: XML no cumple esquema XSD
**Solución**:
1. Verificar estructura XML
2. Validar tipos de datos
3. Revisar campos obligatorios

### Error: "Base de datos no disponible"

**Causa**: Problemas de conexión a BD
**Solución**:
1. Verificar conexión MySQL
2. Usar SQLite como fallback
3. Verificar permisos de BD

## 📝 Logs y Debugging

### Habilitar Logs Detallados

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Verificar Estado de Sincronización

```python
from sync_pacientes import PacienteSyncManager

manager = PacienteSyncManager()
stats = manager.obtener_estadisticas_sync()
print(stats)
```

## 🚀 Próximas Mejoras

- [ ] Interfaz web real (Flask/Django)
- [ ] API REST para sincronización
- [ ] Cifrado de XMLs sensibles
- [ ] Dashboard de monitoreo
- [ ] Notificaciones por correo
- [ ] Sincronización bidireccional
- [ ] Resolución de conflictos automática

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs de error
2. Ejecutar `demo_completo.py` para diagnóstico
3. Verificar configuración de Drive API
4. Comprobar conectividad de base de datos

---

**Nota**: Este sistema está diseñado para funcionar tanto con Google Drive como con archivos locales, garantizando disponibilidad incluso sin conexión a internet.

