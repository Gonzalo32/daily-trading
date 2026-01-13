@echo off
REM ============================================
REM Setup Automático - Trading Bot
REM ============================================
echo.
echo ╔═══════════════════════════════════════════════════╗
echo ║  🚀 Setup Automático - Bot de Trading           ║
echo ╚═══════════════════════════════════════════════════╝
echo.

REM Configurar UTF-8
chcp 65001 >nul 2>&1

REM Verificar Python
echo [1/5] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado. Instala Python 3.11+ desde python.org
    pause
    exit /b 1
)
python --version
echo ✅ Python encontrado
echo.

REM Crear entorno virtual
echo [2/5] Creando entorno virtual...
if exist "venv" (
    echo ⚠️  venv ya existe, saltando...
) else (
    python -m venv venv
    echo ✅ Entorno virtual creado
)
echo.

REM Activar entorno virtual
echo [3/5] Activando entorno virtual...
call venv\Scripts\activate.bat
echo ✅ Entorno virtual activado
echo.

REM Instalar dependencias
echo [4/5] Instalando dependencias...
cd daily-trading
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd ..
echo ✅ Dependencias instaladas
echo.

REM Crear estructura de directorios
echo [5/5] Creando estructura de directorios...
if not exist "daily-trading\logs" mkdir "daily-trading\logs"
if not exist "daily-trading\models" mkdir "daily-trading\models"
echo ✅ Estructura lista
echo.

REM Copiar archivo de configuración ejemplo
if not exist ".env" (
    if exist "env.example" (
        echo 📝 Copiando env.example a .env...
        copy env.example .env >nul
        echo ✅ Archivo .env creado (edítalo con tus configuraciones)
    )
)
echo.

echo ╔═══════════════════════════════════════════════════╗
echo ║  ✅ SETUP COMPLETADO                             ║
echo ╚═══════════════════════════════════════════════════╝
echo.
echo 📝 Próximos pasos:
echo    1. Edita .env con tu configuración (opcional)
echo    2. Ejecuta: start.bat
echo    3. Monitorea: http://localhost:8000
echo.
echo 🧪 Para verificar:
echo    python -c "import main; print('OK')"
echo.
pause
