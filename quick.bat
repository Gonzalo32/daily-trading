@echo off
REM ===============================
REM Ejecución Rápida - Ciclo Único
REM ===============================

cd /d "%~dp0daily-trading"

echo.
echo ⚡ Ejecutando ciclo único...
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python src\main.py

if defined VIRTUAL_ENV (
    deactivate
)

echo.
pause

