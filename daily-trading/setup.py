"""
Script de instalación y configuración del Bot de Day Trading
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_banner():
    """Mostrar banner de bienvenida"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    🤖 BOT DE DAY TRADING                     ║
    ║                   Configuración Automática                   ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

def check_python_version():
    """Verificar versión de Python"""
    print("🔍 Verificando versión de Python...")
    
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {sys.version}")
        return False
        
    print(f"✅ Python {sys.version.split()[0]} detectado")
    return True

def create_directories():
    """Crear directorios necesarios"""
    print("📁 Creando directorios...")
    
    directories = [
        'logs',
        'models',
        'data',
        'backups'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✅ {directory}/")
        
def install_dependencies():
    """Instalar dependencias de Python"""
    print("📦 Instalando dependencias...")
    
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        return False

def create_env_file():
    """Crear archivo .env si no existe"""
    print("⚙️ Configurando variables de entorno...")
    
    if os.path.exists('.env'):
        print("   ✅ Archivo .env ya existe")
        return True
        
    if os.path.exists('env.example'):
        shutil.copy('env.example', '.env')
        print("   ✅ Archivo .env creado desde env.example")
        print("   ⚠️  Recuerda configurar tus API keys en .env")
        return True
    else:
        print("   ❌ Archivo env.example no encontrado")
        return False

def setup_logging():
    """Configurar sistema de logging"""
    print("📝 Configurando sistema de logging...")
    
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Crear archivo de log inicial
    log_file = log_dir / 'trading_bot.log'
    with open(log_file, 'w') as f:
        f.write(f"# Log del Bot de Day Trading\n")
        f.write(f"# Iniciado: {os.popen('date').read().strip()}\n\n")
    
    print("   ✅ Sistema de logging configurado")

def test_imports():
    """Probar importaciones de módulos principales"""
    print("🧪 Probando importaciones...")
    
    try:
        import pandas
        import numpy
        import ccxt
        import requests
        print("   ✅ Módulos principales importados correctamente")
        return True
    except ImportError as e:
        print(f"   ❌ Error importando módulos: {e}")
        return False

def create_startup_scripts():
    """Crear scripts de inicio"""
    print("🚀 Creando scripts de inicio...")
    
    # Script para Windows
    windows_script = """@echo off
echo Iniciando Bot de Day Trading...
python main.py
pause
"""
    
    with open('start_bot.bat', 'w') as f:
        f.write(windows_script)
    
    # Script para Linux/Mac
    unix_script = """#!/bin/bash
echo "Iniciando Bot de Day Trading..."
python3 main.py
"""
    
    with open('start_bot.sh', 'w') as f:
        f.write(unix_script)
    
    # Hacer ejecutable en Unix
    if os.name != 'nt':
        os.chmod('start_bot.sh', 0o755)
    
    print("   ✅ Scripts de inicio creados")

def show_next_steps():
    """Mostrar próximos pasos"""
    print("""
    🎉 ¡Configuración completada!
    
    📋 Próximos pasos:
    
    1. 📝 Configura tu archivo .env con tus API keys:
       - BINANCE_API_KEY (para criptomonedas)
       - BINANCE_SECRET_KEY
       - TELEGRAM_BOT_TOKEN (opcional)
       - TELEGRAM_CHAT_ID (opcional)
    
    2. 🧪 Prueba el bot en modo simulación:
       python backtest.py --start-date 2023-01-01 --end-date 2023-12-31
    
    3. 🚀 Inicia el bot:
       python main.py
       # O usa los scripts:
       # Windows: start_bot.bat
       # Linux/Mac: ./start_bot.sh
    
    4. 📊 Monitorea el dashboard:
       http://localhost:8000
    
    ⚠️  IMPORTANTE:
    - Siempre prueba primero en modo PAPER
    - Nunca uses dinero que no puedas permitirte perder
    - Monitorea regularmente el bot
    
    📚 Documentación completa en README.md
    """)

def main():
    """Función principal de configuración"""
    print_banner()
    
    # Verificar Python
    if not check_python_version():
        sys.exit(1)
    
    # Crear directorios
    create_directories()
    
    # Instalar dependencias
    if not install_dependencies():
        print("❌ Error en la instalación. Revisa los errores anteriores.")
        sys.exit(1)
    
    # Crear archivo .env
    if not create_env_file():
        print("❌ Error creando archivo .env")
        sys.exit(1)
    
    # Configurar logging
    setup_logging()
    
    # Probar importaciones
    if not test_imports():
        print("❌ Error en las importaciones. Reinstala las dependencias.")
        sys.exit(1)
    
    # Crear scripts de inicio
    create_startup_scripts()
    
    # Mostrar próximos pasos
    show_next_steps()

if __name__ == "__main__":
    main()
