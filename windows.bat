@echo off
set VENV_DIR=venv

:: Crear entorno virtual si no existe
if not exist %VENV_DIR%\ (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
)

:: Activar entorno virtual
call %VENV_DIR%\Scripts\activate.bat

:: Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

:: Ejecutar el programa
python LecturaSeedlink.py

:: Mostrar archivos
dir
