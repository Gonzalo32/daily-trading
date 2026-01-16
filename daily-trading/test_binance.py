import asyncio
import sys
import traceback
import ccxt.async_support as ccxt

async def test_connection():
    print('=' * 60)
    print('Probando conexion a Binance...')
    print('=' * 60)
    
    try:
        print('\n1. Probando sin API keys (datos publicos)...')
        exchange = ccxt.binance({
            'apiKey': '',
            'secret': '',
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True
            },
        })
        
        print('   Intentando load_markets()...')
        await exchange.load_markets()
        print('   OK load_markets() exitoso')
        
        print('\n   Intentando fetch_ticker...')
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f'   OK Precio BTC/USDT: {ticker.get(\"last\", \"N/A\")}')
        
        await exchange.close()
        return True
        
    except Exception as e:
        print(f'\n   ERROR: {type(e).__name__}: {e}')
        print('\n   Traceback completo:')
        traceback.print_exc()
        if 'exchange' in locals():
            try:
                await exchange.close()
            except:
                pass
        return False

if __name__ == '__main__':
    try:
        result = asyncio.run(test_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print('\n\nInterrumpido por el usuario')
        sys.exit(1)
