@echo off
REM ===============================
REM Configurar PATH del Sistema
REM Este script agrega el directorio actual al PATH del usuario
REM IMPORTANTE: Ejecutar como Administrador
REM ===============================

echo.
echo ===============================
echo 🔧 Configurando PATH del Sistema
echo ===============================
echo.

REM Obtener el directorio actual
set "CURRENT_DIR=%~dp0"
set "CURRENT_DIR=%CURRENT_DIR:~0,-1%"

echo Directorio a agregar: %CURRENT_DIR%
echo.

REM Verificar si ya está en el PATH
echo Verificando si el directorio ya está en el PATH...
echo %PATH% | findstr /C:"%CURRENT_DIR%" >nul
if %errorlevel% equ 0 (
    echo ✅ El directorio ya está en el PATH.
    pause
    exit /b 0
)

REM Agregar al PATH del usuario (permanente)
echo Agregando al PATH del usuario...
setx PATH "%PATH%;%CURRENT_DIR%"

if %errorlevel% equ 0 (
    echo.
    echo ✅ ¡PATH configurado correctamente!
    echo.
    echo 📌 IMPORTANTE:
    echo    - Cierra y vuelve a abrir cualquier ventana de CMD/PowerShell
    echo    - Después podrás ejecutar "start" desde cualquier ubicación
    echo.
) else (
    echo.
    echo ❌ Error al configurar el PATH.
    echo    Intenta ejecutar este script como Administrador.
    echo.
)

pause

