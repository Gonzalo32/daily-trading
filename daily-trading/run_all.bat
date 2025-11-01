@echo off
echo ===============================
echo Generando datos de entrenamiento...
echo ===============================
python src\ml\generate_training_data.py

echo.
echo ===============================
echo Entrenando modelo ML...
echo ===============================
python src\ml\train_model.py

echo.
echo ===============================
echo Proceso completado.
pause
