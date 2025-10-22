# src/main.py
import asyncio
from datetime import datetime


from config import Config
from src.data.market_data import MarketDataProvider
from src.execution.order_executor import OrderExecutor
from src.strategy.trading_strategy import TradingStrategy
from src.risk.risk_manager import RiskManager, RiskState
from src.utils.logger import setup_logging




async def run_once():
logger = setup_logging(__name__)
cfg = Config()


md = MarketDataProvider(cfg)
ex = OrderExecutor(cfg)
strat = TradingStrategy(cfg)
risk = RiskManager(cfg, RiskState(equity=cfg.INITIAL_CAPITAL))


await md.initialize()
await ex.initialize()


latest = await md.get_latest_data()
if not latest:
logger.error("No se pudieron obtener datos")
return


# Generar señal de la estrategia
signal = strat.generate_signal(latest)
if not signal:
logger.info("Sin señal")
await ex.close(); await md.close()
return


# Kill‑switch diario
if not risk.daily_guard():
logger.warning("Kill‑switch: pérdida diaria máxima alcanzada. No se opera.")
await ex.close(); await md.close()
return


# Sizing + SL/TP
atr = latest['indicators'].get('atr')
full_signal = risk.size_and_protect(signal, atr=atr)


# Ejecutar
res = await ex.execute_order(full_signal)
if res.get('success') and res.get('order'):
logger.info(f"Orden abierta: {res['order']}")
# Aquí podrías esperar condiciones de cierre y llamar a ex.close_position(...)


await ex.close()
await md.close()




if __name__ == "__main__":
asyncio.run(run_once())