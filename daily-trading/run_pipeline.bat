@echo off
echo ===============================
echo  DAILY TRADING - PIPELINE ML
echo ===============================
echo.

REM Activar entorno virtual (si usás uno)
if exist venv (
    echo Activando entorno virtual...
    call venv\Scripts\activate
)

echo Ejecutando pipeline completo...
python run_pipeline.py

echo.
echo ===============================
echo  PIPELINE FINALIZADO
echo ===============================
pause
