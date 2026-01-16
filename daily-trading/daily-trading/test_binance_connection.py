"""Script de prueba para diagnosticar conexión a Binance"""
import asyncio
import sys
import traceback
import ccxt.async_support as ccxt

async def test_connection():
    print("=" * 60)
    print("🔍 Probando conexión a Binance...")
    print("=" * 60)
    
    try:
        # Probar sin API keys (datos públicos)
        print("\n1️⃣ Probando sin API keys (datos públicos)...")
        exchange = ccxt.binance({
            "apiKey": "",
            "secret": "",
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
                "adjustForTimeDifference": True
            },
        })
        
        print("   Intentando load_markets()...")
        await exchange.load_markets()
        print("   ✅ load_markets() exitoso")
        
        print("\n   Intentando fetch_ticker('BTC/USDT')...")
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f"   ✅ Precio BTC/USDT: {ticker.get('last', 'N/A')}")
        
        await exchange.close()
        
    except Exception as e:
        print(f"\n   ❌ ERROR: {type(e).__name__}: {e}")
        print("\n   Traceback completo:")
        traceback.print_exc()
        await exchange.close() if 'exchange' in locals() else None
        return False
    
    try:
        # Probar con API keys (si están disponibles)
        print("\n2️⃣ Probando con API keys...")
        from config import Config
        config = Config()
        
        if config.BINANCE_API_KEY and config.BINANCE_SECRET_KEY:
            print(f"   API Key encontrada: {config.BINANCE_API_KEY[:10]}...")
            exchange2 = ccxt.binance({
                "apiKey": config.BINANCE_API_KEY,
                "secret": config.BINANCE_SECRET_KEY,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                    "adjustForTimeDifference": True
                },
            })
            
            if config.BINANCE_TESTNET:
                exchange2.set_sandbox_mode(True)
                print("   🔧 Usando Binance Testnet")
            else:
                exchange2.set_sandbox_mode(False)
                print("   🔧 Usando Binance Real")
            
            print("   Intentando load_markets()...")
            await exchange2.load_markets()
            print("   ✅ load_markets() exitoso")
            
            print("\n   Intentando fetch_ticker('BTC/USDT')...")
            ticker2 = await exchange2.fetch_ticker('BTC/USDT')
            print(f"   ✅ Precio BTC/USDT: {ticker2.get('last', 'N/A')}")
            
            await exchange2.close()
        else:
            print("   ⚠️ No hay API keys configuradas")
            
    except Exception as e:
        print(f"\n   ❌ ERROR: {type(e).__name__}: {e}")
        print("\n   Traceback completo:")
        traceback.print_exc()
        await exchange2.close() if 'exchange2' in locals() else None
        return False
    
    print("\n" + "=" * 60)
    print("✅ Todas las pruebas completadas")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido por el usuario")
        sys.exit(1)
