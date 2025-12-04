@echo off
echo ============================================
echo   RECETAS WEB - SETUP AUTOMATICO (Windows)
echo ============================================

echo.
echo [1/5] Verificando Python 3.11...
py -3.11 --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python 3.11 no está instalado.
    echo Descargalo desde https://www.python.org/downloads/release/python-3110/
    pause
    exit /b
)

echo.
echo [2/5] Creando entorno virtual...
py -3.11 -m venv venv

echo.
echo [3/5] Activando entorno virtual...
call venv\Scripts\activate

echo.
echo [4/5] Instalando dependencias...
pip install -r requirements.txt

echo.
echo [5/5] Inicializando base de datos...
python - << EOF
from database.base import Base, engine
print("Creando tablas...")
Base.metadata.create_all(bind=engine)
print("Tablas creadas.")
EOF

echo.
echo ============================================
echo  SETUP COMPLETO 🎉
echo.
echo  Para iniciar el servidor:
echo  venv\Scripts\activate
echo  uvicorn app:app --reload
echo ============================================
pause
