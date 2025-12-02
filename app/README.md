# Proyecto Recetario Médico DAW

## Configuración del Entorno

Este proyecto utiliza un entorno virtual para gestionar sus dependencias de forma aislada. Sigue estos pasos para configurarlo:

1.  **Crear el entorno virtual** (solo se hace una vez):
    ```bash
    python3 -m venv .venv
    ```

2.  **Activar el entorno virtual** (haz esto cada vez que vayas a trabajar en el proyecto):
    ```bash
    source .venv/bin/activate
    ```

3.  **Instalar las dependencias**:
    ```bash
    pip install -r app/requirements.txt
    ```

Este proyecto es una aplicación para la gestión de recetas médicas, permitiendo su creación, almacenamiento y compartición de forma segura.

## Funcionalidades Clave

- Generación de recetas en formato XML y PDF.
- Almacenamiento seguro en base de datos.
- Sincronización con Google Drive.
- Cifrado de archivos PDF.
- Verificación de integridad de archivos XML mediante Checksum (SHA-256).
- Validación de la estructura de archivos XML mediante un esquema XSD.

---

## Validación de XML con Esquema XSD

Para garantizar la calidad y consistencia de los datos, todos los archivos XML de recetas generados son validados contra un esquema XSD (`receta.xsd`) antes de ser procesados o almacenados.

### Reglas Impuestas por el XSD (`receta.xsd`)

El esquema define la siguiente estructura obligatoria para cada receta:

1.  **Elemento Raíz**: `<receta>`

2.  **`<paciente>`**: Debe aparecer exactamente una vez.
    -   `<nombre>` (string): Obligatorio.
    -   `<edad>` (entero positivo): Opcional.
    -   `<genero>` (string, 'M' o 'F'): Opcional.
    -   `<correo>` (string): Opcional.

3.  **`<medico>`**: Debe aparecer exactamente una vez.
    -   `<nombre>` (string): Obligatorio.
    -   `<cedula>` (string): Obligatorio.
    -   `<especialidad>` (string): Opcional.

4.  **`<diagnostico>`** (string): Obligatorio.

5.  **`<medicamentos>`**: Debe aparecer exactamente una vez y contener al menos un medicamento.
    -   **`<medicamento>`**: Puede aparecer una o más veces (`unbounded`).
        -   `<nombre>` (string): Obligatorio.
        -   `<dosis>` (string): Opcional.
        -   `<frecuencia>` (string): Opcional.

### ¿Cómo ejecutar la validación?

La validación se ejecuta automáticamente cada vez que se genera un nuevo archivo XML a través de la función `generar_xml_receta` en `app/xml_utils.py`.

Para ejecutar una prueba manual que demuestre el proceso de validación para un caso de éxito y uno de fallo, puedes ejecutar el siguiente script desde la raíz del proyecto:

**Asegúrate de tener el entorno virtual activado (`source .venv/bin/activate`) antes de ejecutar el comando.**

```bash
python3 -m app.test_validation
```

Los resultados de la prueba (logs) se mostrarán directamente en la consola.

# Proyecto Recetario Médico

... (descripción de tu proyecto) ...

## Módulo de Sincronización Automática (JOB)

Este proyecto incluye un sistema automatizado que simula la recepción y procesamiento de recetas médicas en formato XML desde una fuente externa (simulada como un sistema de carpetas locales).

### Cómo Funciona

El sistema consta de dos componentes principales que se ejecutan en segundo plano:

1.  **Simulador de Creación (JOB A):** Cada 20 segundos, este proceso crea un nuevo archivo XML (a veces válido, a veces inválido) en la carpeta `drive_simulation/nuevos/`. Esto simula una aplicación web generando y "subiendo" recetas.
2.  **Procesador de Sincronización (JOB B):** Cada 10 segundos, este proceso principal revisa la carpeta `drive_simulation/nuevos/` en busca de archivos. Por cada archivo encontrado:
    *   Lo valida contra el esquema `receta.xsd`.
    *   Si es válido, inserta los datos en la base de datos local (MySQL o SQLite).
    *   Mueve el archivo a `drive_simulation/procesados/` si tuvo éxito.
    *   Mueve el archivo a `drive_simulation/errores/` si la validación o la inserción en la base de datos fallaron.

### Estructura de Carpetas del JOB

-   `drive_simulation/nuevos/`: Carpeta de entrada para nuevos XML.
-   `drive_simulation/procesados/`: Almacén de archivos procesados correctamente.
-   `drive_simulation/errores/`: Almacén de archivos que fallaron la validación.
-   `logs/sync_job.log`: Archivo de registro detallado de toda la actividad del job.

### Cómo Ejecutar el JOB

1.  Asegúrate de tener todas las dependencias instaladas:
    ```bash
    pip install -r app/requirements.txt
    ```
2.  Ejecuta el script `run_job.py` desde la carpeta `app`:
    ```bash
    python app/run_job.py
    ```
3.  El script se quedará corriendo en tu terminal. Verás mensajes indicando que el planificador ha iniciado. Para detenerlo, presiona `Ctrl+C`.

### Cómo Configurar el Intervalo

Abre el archivo `app/run_job.py` y modifica la siguiente constante:

```python
# El JOB se ejecutará cada 10 segundos
INTERVALO_SEGUNDOS = 10
```

Puedes cambiar el valor `10` por cualquier otro número de segundos que desees.

### Cómo Ver los Logs

Toda la actividad del job (inicio, archivos encontrados, validaciones, errores, resultados) se registra en el archivo:

`logs/sync_job.log`

Puedes abrir este archivo con cualquier editor de texto para ver el historial de ejecuciones en tiempo real.
