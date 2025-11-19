@echo off
chcp 65001 >nul
REM ===============================
REM Bot de Trading - Menú Principal
REM ===============================

:menu
cls
echo.
echo ╔════════════════════════════════════════════╗
echo ║   🤖 BOT DE TRADING - MENÚ PRINCIPAL       ║
echo ╚════════════════════════════════════════════╝
echo.
echo   [1] 🚀 Iniciar Bot de Trading (main.py)
echo   [2] ⚡ Ejecutar ciclo único (src\main.py)
echo   [3] 📊 Entrenar modelo ML
echo   [4] 📈 Ver logs
echo   [5] 🔧 Configurar PATH (ejecutar desde cualquier lugar)
echo   [6] ❌ Salir
echo.
echo ════════════════════════════════════════════
echo.

set /p opcion="Selecciona una opción (1-6): "

if "%opcion%"=="1" goto bot_principal
if "%opcion%"=="2" goto ciclo_unico
if "%opcion%"=="3" goto entrenar_ml
if "%opcion%"=="4" goto ver_logs
if "%opcion%"=="5" goto configurar_path
if "%opcion%"=="6" goto salir

echo.
echo ❌ Opción inválida. Por favor, selecciona una opción del 1 al 6.
timeout /t 2 >nul
goto menu

:bot_principal
cls
echo.
echo ═══════════════════════════════════════════
echo 🚀 Iniciando Bot de Trading Principal...
echo ═══════════════════════════════════════════
echo.
call venv\Scripts\activate.bat
python main.py
deactivate
echo.
pause
goto menu

:ciclo_unico
cls
echo.
echo ═══════════════════════════════════════════
echo ⚡ Ejecutando ciclo único de trading...
echo ═══════════════════════════════════════════
echo.
call venv\Scripts\activate.bat
python src\main.py
deactivate
echo.
pause
goto menu

:entrenar_ml
cls
echo.
echo ═══════════════════════════════════════════
echo 📊 Entrenando Modelo de Machine Learning...
echo ═══════════════════════════════════════════
echo.
call venv\Scripts\activate.bat
echo.
echo [1/2] Generando datos de entrenamiento...
python src\ml\generate_training_data.py
echo.
echo [2/2] Entrenando modelo...
python src\ml\train_model.py
echo.
echo ✅ Proceso completado.
deactivate
pause
goto menu

:ver_logs
cls
echo.
echo ═══════════════════════════════════════════
echo 📈 Últimas líneas del log (logs\trading_bot.log)
echo ═══════════════════════════════════════════
echo.
if exist "logs\trading_bot.log" (
    powershell -Command "Get-Content logs\trading_bot.log -Tail 30"
) else (
    echo ⚠️ No se encontró el archivo de logs.
)
echo.
pause
goto menu

:configurar_path
cls
echo.
echo ═══════════════════════════════════════════
echo 🔧 Configurando PATH del Sistema
echo ═══════════════════════════════════════════
echo.
echo IMPORTANTE: Este script agregará el directorio actual
echo al PATH del sistema para que puedas ejecutar "start"
echo desde cualquier ubicación.
echo.
set /p confirmar="¿Deseas continuar? (S/N): "

if /i "%confirmar%"=="S" (
    call configurar_path.bat
) else (
    echo.
    echo Operación cancelada.
    timeout /t 2 >nul
)
goto menu

:salir
cls
echo.
echo ═══════════════════════════════════════════
echo 👋 ¡Hasta luego!
echo ═══════════════════════════════════════════
echo.
timeout /t 1 >nul
exit


