@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    py -m venv .venv
    if errorlevel 1 (echo Error al crear el entorno virtual. & exit /b 1)
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (echo Error instalando dependencias. & exit /b 1)
if not exist .env (echo Falta tu archivo .env existente. & exit /b 1)
if errorlevel 1 exit /b 1
echo Entorno listo. Configura .env y ejecuta run.bat.
pause
