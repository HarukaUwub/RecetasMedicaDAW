-- Migración: Agrega la columna pdf_path a la tabla recetas_web
-- Ejecutar este script en la base de datos SQLite

-- Verificar si la columna ya existe (SQLite no tiene IF NOT EXISTS para ALTER TABLE)
-- Si la columna ya existe, este comando fallará, lo cual es aceptable

ALTER TABLE recetas_web ADD COLUMN pdf_path VARCHAR;

