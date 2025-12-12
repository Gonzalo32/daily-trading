@echo off
REM ===============================
REM Bot de Trading - Inicio Rápido
REM ===============================

echo.
echo ╔════════════════════════════════════════════╗
echo ║   🚀 Iniciando Bot de Trading...           ║
echo ╚════════════════════════════════════════════╝
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0daily-trading"

REM Verificar que el directorio existe
if not exist "main.py" (
    echo ❌ Error: No se encontró el archivo main.py
    echo Verifica que estás en el directorio correcto
    pause
    exit /b 1
)

REM Activar entorno virtual
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✅ Entorno virtual activado
    echo.
) else (
    echo ⚠️  Advertencia: No se encontró el entorno virtual
    echo Intentando ejecutar con Python del sistema...
    echo.
)

REM Ejecutar el bot principal
echo ═══════════════════════════════════════════
echo 📡 Ejecutando Bot de Trading...
echo ═══════════════════════════════════════════
echo.

python main.py

REM Desactivar entorno virtual si estaba activado
if defined VIRTUAL_ENV (
    deactivate
)

echo.
echo ═══════════════════════════════════════════
echo ✅ Programa finalizado
echo ═══════════════════════════════════════════
echo.
pause

