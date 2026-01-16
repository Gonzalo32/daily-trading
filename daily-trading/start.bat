@echo off
REM ===============================
REM Bot de Trading - INICIO RAPIDO
REM ===============================
REM Desde: C:\Users\Administrador\Desktop\daily-trading
REM Ejecutar: start
REM ===============================

cd /d "%~dp0"

echo.
echo ╔════════════════════════════════════════════╗
echo ║   🚀 Bot de Trading - Iniciando...        ║
echo ╚════════════════════════════════════════════╝
echo.

REM Verificar que estamos en el directorio correcto
if not exist "daily-trading\main.py" (
    echo ❌ Error: No se encontró daily-trading\main.py
    echo.
    echo Estructura esperada:
    echo   daily-trading\
    echo   ├── main.py
    echo   └── venv\
    echo.
    pause
    exit /b 1
)

REM Verificar que existe el entorno virtual
if not exist "daily-trading\venv\Scripts\python.exe" (
    echo ❌ Error: No se encontró el entorno virtual
    echo.
    echo Por favor ejecuta primero: setup_windows.bat
    echo.
    pause
    exit /b 1
)

echo ✅ Directorio verificado
echo ✅ Entorno virtual encontrado
echo.

REM Cambiar al directorio del bot
cd daily-trading

echo ═══════════════════════════════════════════
echo 📡 Iniciando bot de trading...
echo ═══════════════════════════════════════════
echo.

REM Ejecutar usando Python del venv directamente (más confiable)
.\venv\Scripts\python.exe main.py

REM Si el bot termina, mostrar mensaje
if errorlevel 1 (
    echo.
    echo ═══════════════════════════════════════════
    echo ❌ El bot terminó con un error
    echo ═══════════════════════════════════════════
) else (
    echo.
    echo ═══════════════════════════════════════════
    echo ✅ Bot finalizado correctamente
    echo ═══════════════════════════════════════════
)

echo.
pause

