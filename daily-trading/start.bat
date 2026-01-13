@echo off
REM ===============================
REM Bot de Trading - ENTRYPOINT OFICIAL
REM ===============================
REM Ejecuta: daily-trading/main.py

cd /d "%~dp0"

echo.
echo ╔════════════════════════════════════════════╗
echo ║   🚀 Bot de Trading - Modo PAPER          ║
echo ╚════════════════════════════════════════════╝
echo.

REM Verificar que estamos en el directorio correcto
if not exist "daily-trading\main.py" (
    echo ❌ Error: No se encontró daily-trading\main.py
    echo.
    echo Estructura esperada:
    echo   daily-trading\
    echo   ├── main.py          ^<-- ENTRYPOINT
    echo   ├── config.py
    echo   └── src\
    echo.
    pause
    exit /b 1
)

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✅ Virtualenv activado
) else if exist "daily-trading\venv\Scripts\activate.bat" (
    call daily-trading\venv\Scripts\activate.bat
    echo ✅ Virtualenv activado
) else (
    echo ⚠️  No se encontró virtualenv, usando Python del sistema
)

echo.
echo ═══════════════════════════════════════════
echo 📡 Ejecutando bot...
echo ═══════════════════════════════════════════
echo.

REM Cambiar a directorio daily-trading y ejecutar
cd daily-trading
python main.py

REM Volver a raíz
cd ..

REM Desactivar virtualenv si estaba activo
if defined VIRTUAL_ENV (
    deactivate
)

echo.
echo ═══════════════════════════════════════════
echo ✅ Bot finalizado
echo ═══════════════════════════════════════════
echo.
pause

