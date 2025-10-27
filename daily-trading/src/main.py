# src/main.py

import asyncio
from datetime import datetime

from config import Config
from src.data.market_data import MarketDataProvider
from src.execution.order_executor import OrderExecutor
from src.strategy.trading_strategy import TradingStrategy
from src.risk.risk_manager import RiskManager, RiskState
from src.utils.logging_setup import setup_logging


async def run_once():
    # ==========================
    # 🔧 Setup inicial
    # ==========================
    cfg = Config()
    logger = setup_logging(__name__, logfile=cfg.LOG_FILE, log_level=cfg.LOG_LEVEL)

    market = MarketDataProvider(cfg)
    executor = OrderExecutor(cfg)
    strategy = TradingStrategy(cfg)
    risk = RiskManager(cfg, RiskState(equity=cfg.INITIAL_CAPITAL))

    # ==========================
    # 🌐 Inicializar conexiones
    # ==========================
    await market.initialize()
    await executor.initialize()

    # ==========================
    # 📊 Obtener datos de mercado
    # ==========================
    latest = await market.get_latest_data()
    if not latest:
        logger.error("❌ No se pudieron obtener datos de mercado")
        await executor.close()
        await market.close()
        return

    logger.info(f"📡 Datos recibidos de {latest['symbol']} @ {latest['price']}")

    # ==========================
    # 🧠 Generar señal de trading
    # ==========================
    signal = await strategy.generate_signal(latest)
    if not signal:
        logger.info("ℹ️ Sin señal operable en este tick")
        await executor.close()
        await market.close()
        return

    logger.info(
        f"🎯 Señal bruta: {signal['action']} {signal['symbol']} @ {signal['price']} | "
        f"SL={signal['stop_loss']} TP={signal['take_profit']}"
    )

    # ==========================
    # 🛡 Kill-switch diario / límites
    # ==========================
    if not risk._check_daily_limits():
        logger.warning("⛔ Kill-switch: límite diario de riesgo alcanzado. No se opera.")
        await executor.close()
        await market.close()
        return

    # ==========================
    # 📏 Validación de riesgo antes de entrar
    # ==========================
    open_positions = executor.executed_orders  # lo que ya ejecutamos en esta sesión
    sized_signal = risk.size_and_protect(signal, atr=latest["indicators"].get("atr"))

    # Validar exposición, máximo de posiciones, etc.
    if not risk.validate_trade(sized_signal, open_positions):
        logger.warning("🚫 Trade bloqueado por gestión de riesgo")
        await executor.close()
        await market.close()
        return

    logger.info(
        f"💼 Señal aprobada por riesgo: size={sized_signal['position_size']} "
        f"SL={sized_signal['stop_loss']} TP={sized_signal['take_profit']}"
    )

    # ==========================
    # 🧾 Ejecutar orden
    # ==========================
    res = await executor.execute_order(sized_signal)

    if res.get("success") and res.get("order"):
        opened = res["order"]
        logger.info(
            f"✅ Orden abierta: {opened['id']} "
            f"{opened['side']} {opened['symbol']} size={opened['size']} "
            f"entry={opened['entry_price']}"
        )
    else:
        logger.error(f"❌ Falló la ejecución de la orden: {res.get('error')}")

    # ==========================
    # 🧹 Cierre ordenado
    # ==========================
    await executor.close()
    await market.close()

    logger.info("🏁 Ciclo finalizado")


if __name__ == "__main__":
    asyncio.run(run_once())
