@echo off
REM ===============================
REM Bot de Trading - Inicio Rápido
REM ===============================

cd /d "%~dp0"

echo.
echo ===============================
echo 🚀 Iniciando Bot de Trading...
echo ===============================
echo.

REM Activar entorno virtual
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ❌ Error: No se encontró el entorno virtual.
    echo Por favor, crea el entorno virtual primero con: python -m venv venv
    pause
    exit /b 1
)

REM Ejecutar el bot principal
python main.py

REM Desactivar entorno virtual al finalizar
deactivate

pause

