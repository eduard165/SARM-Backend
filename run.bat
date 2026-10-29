@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Falta el entorno virtual. Ejecuta setup.bat.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
