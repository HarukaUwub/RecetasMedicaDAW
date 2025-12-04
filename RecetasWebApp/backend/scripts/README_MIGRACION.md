# Migración: Agregar columna pdf_path

Esta migración agrega la columna `pdf_path` a la tabla `recetas_web` en la base de datos.

## Opción 1: Ejecutar el script SQL directamente (Recomendado)

```bash
cd backend
sqlite3 web.db < scripts/migrate_add_pdf_path.sql
```

Si el comando `sqlite3` no está disponible, puedes usar Python:

```bash
cd backend
python -c "import sqlite3; conn = sqlite3.connect('web.db'); conn.execute('ALTER TABLE recetas_web ADD COLUMN pdf_path VARCHAR'); conn.commit(); conn.close(); print('Migración completada')"
```

## Opción 2: Ejecutar el script Python

```bash
cd backend
# Activar el entorno virtual primero
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Luego ejecutar:
python scripts/migrate_add_pdf_path.py
```

## Verificar la migración

Puedes verificar que la columna se agregó correctamente:

```bash
cd backend
sqlite3 web.db "PRAGMA table_info(recetas_web);"
```

Deberías ver `pdf_path` en la lista de columnas.

## Nota

Si la columna ya existe, recibirás un error. Esto es normal y significa que la migración ya se ejecutó anteriormente.

