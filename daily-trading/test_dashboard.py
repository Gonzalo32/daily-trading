"""Script de prueba para el dashboard"""
import asyncio
import sys
from src.monitoring.dashboard import Dashboard
from config import Config

async def test_dashboard():
    try:
        print("Creando dashboard...")
        config = Config()
        dashboard = Dashboard(config)
        
        print("Iniciando dashboard...")
        await dashboard.start()
        
        print("Dashboard iniciado. Esperando 10 segundos...")
        await asyncio.sleep(10)
        
        print("Deteniendo dashboard...")
        await dashboard.stop()
        
        print("✅ Test completado exitosamente")
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_dashboard())
