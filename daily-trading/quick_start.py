"""
Script de inicio rápido para el Bot de Day Trading
Configuración automática y primera ejecución
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_banner():
    """Mostrar banner de bienvenida"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    🤖 BOT DE DAY TRADING                     ║
    ║                      INICIO RÁPIDO                           ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

def check_requirements():
    """Verificar requisitos del sistema"""
    print("🔍 Verificando requisitos del sistema...")
    
    # Verificar Python
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {sys.version}")
        return False
        
    print(f"✅ Python {sys.version.split()[0]} detectado")
    
    # Verificar pip
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', '--version'], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ pip detectado")
    except subprocess.CalledProcessError:
        print("❌ Error: pip no está disponible")
        return False
        
    return True

def install_dependencies():
    """Instalar dependencias básicas"""
    print("📦 Instalando dependencias básicas...")
    
    basic_deps = [
        'pandas',
        'numpy',
        'requests',
        'python-dotenv'
    ]
    
    for dep in basic_deps:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"   ✅ {dep}")
        except subprocess.CalledProcessError:
            print(f"   ❌ Error instalando {dep}")
            return False
            
    return True

def create_basic_config():
    """Crear configuración básica"""
    print("⚙️ Creando configuración básica...")
    
    # Crear archivo .env básico
    env_content = """# Configuración básica del Bot de Day Trading
TRADING_MODE=PAPER
MARKET=CRYPTO
SYMBOL=BTC/USDT
TIMEFRAME=1m

# Configuración de estrategia
FAST_MA_PERIOD=5
SLOW_MA_PERIOD=20
RSI_PERIOD=14
RSI_OVERBOUGHT=70
RSI_OVERSOLD=30

# Configuración de riesgo
MAX_POSITIONS=3
MAX_DAILY_LOSS=0.03
MAX_DAILY_GAIN=0.05
RISK_PER_TRADE=0.02

# Configuración de logging
LOG_LEVEL=INFO
LOG_FILE=logs/trading_bot.log

# Configuración de dashboard
ENABLE_DASHBOARD=True
DASHBOARD_PORT=8000

# Configuración de notificaciones
ENABLE_NOTIFICATIONS=False
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
        
    print("   ✅ Archivo .env creado")
    
    # Crear directorios necesarios
    directories = ['logs', 'models', 'data']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✅ Directorio {directory}/ creado")
        
    return True

def run_demo():
    """Ejecutar demostración del bot"""
    print("🚀 Iniciando demostración del bot...")
    print("   ⚠️  Esta es una demostración con datos simulados")
    print("   ⚠️  No se realizarán operaciones reales")
    print("   ⚠️  Presiona Ctrl+C para detener")
    print()
    
    try:
        # Ejecutar el bot en modo demo
        subprocess.run([sys.executable, 'main.py'])
    except KeyboardInterrupt:
        print("\n🛑 Demostración detenida por el usuario")
    except Exception as e:
        print(f"❌ Error en la demostración: {e}")

def show_next_steps():
    """Mostrar próximos pasos"""
    print("""
    🎉 ¡Configuración básica completada!
    
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
       # O usa: python quick_start.py --run
    
    4. 📊 Monitorea el dashboard:
       http://localhost:8000
    
    ⚠️  IMPORTANTE:
    - Siempre prueba primero en modo PAPER
    - Nunca uses dinero que no puedas permitirte perder
    - Monitorea regularmente el bot
    
    📚 Documentación completa en README.md
    """)

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Inicio rápido del Bot de Day Trading')
    parser.add_argument('--run', action='store_true', help='Ejecutar el bot después de la configuración')
    parser.add_argument('--demo', action='store_true', help='Ejecutar demostración')
    
    args = parser.parse_args()
    
    print_banner()
    
    # Verificar requisitos
    if not check_requirements():
        print("❌ Error en los requisitos del sistema")
        sys.exit(1)
    
    # Instalar dependencias básicas
    if not install_dependencies():
        print("❌ Error instalando dependencias")
        sys.exit(1)
    
    # Crear configuración básica
    if not create_basic_config():
        print("❌ Error creando configuración")
        sys.exit(1)
    
    if args.demo:
        # Ejecutar demostración
        run_demo()
    elif args.run:
        # Ejecutar el bot
        print("🚀 Iniciando bot...")
        try:
            subprocess.run([sys.executable, 'main.py'])
        except KeyboardInterrupt:
            print("\n🛑 Bot detenido por el usuario")
    else:
        # Mostrar próximos pasos
        show_next_steps()

if __name__ == "__main__":
    import argparse
    main()
