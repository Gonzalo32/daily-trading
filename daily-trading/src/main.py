# src/main.py

import asyncio
from datetime import datetime

from config import Config
from src.data.market_data import MarketDataProvider
from src.execution.order_executor import OrderExecutor
from src.strategy.trading_strategy import TradingStrategy
from src.risk.risk_manager import RiskManager, RiskState
from src.risk.advanced_position_manager import AdvancedPositionManager
from src.utils.logging_setup import setup_logging


async def main_loop():

    cfg = Config()
    logger = setup_logging(__name__, logfile=cfg.LOG_FILE,
                           log_level=cfg.LOG_LEVEL)

    market = MarketDataProvider(cfg)
    executor = OrderExecutor(cfg)
    strategy = TradingStrategy(cfg)
    risk = RiskManager(cfg, RiskState(equity=cfg.INITIAL_CAPITAL))
    position_manager = AdvancedPositionManager(cfg)

    # ✅ INICIALIZAR CONEXIONES
    await market.initialize()
    await executor.initialize()

    logger.info("🚀 Bot iniciado")

    try:
        while True:

            # =========================
            # 📡 OBTENER DATOS MERCADO
            # =========================
            market_data = await market.get_latest_data()
            if not market_data:
                await asyncio.sleep(cfg.POLL_INTERVAL)
                continue

            logger.info(
                f"📊 {market_data['symbol']} @ {market_data['price']}"
            )

            # ==================================
            # 🧠 BUSCAR NUEVA ENTRADA
            # ==================================
            signal = await strategy.generate_signal(market_data)

            if signal:

                # ✅ EVITAR MULTI-POSICIONES (NO STACK)
                if executor.positions:
                    logger.info("⏸️ Hay una posición abierta → no se abre trade nuevo")
                    await asyncio.sleep(cfg.POLL_INTERVAL)
                    continue

                if risk._check_daily_limits():

                    signal = risk.size_and_protect(
                        signal, atr=market_data["indicators"].get("atr")
                    )

                    if risk.validate_trade(signal, executor.positions):

                        result = await executor.execute_order(signal)

                        if result.get("success"):

                            opened = result["order"]

                            position = {
                                "id": opened["id"],
                                "symbol": opened["symbol"],
                                "side": opened["side"],
                                "entry_price": opened["entry_price"],
                                "quantity": opened["size"],
                                "stop_loss": signal["stop_loss"],
                                "take_profit": signal["take_profit"],
                                "open_time": datetime.utcnow()
                            }

                            executor.positions.append(position)

                            logger.info(
                                f"✅ ABIERTA → {position['symbol']} {position['side']} "
                                f"@ {position['entry_price']}"
                            )

            # ==================================
            # 🛠️ GESTIONAR POSICIONES ABIERTAS
            # ==================================
            for position in executor.positions.copy():

                decision = await position_manager.manage_position(
                    position=position,
                    current_price=market_data["price"],
                    market_data=market_data,
                    mvp_mode=False,   # ⬅️ MVP DESACTIVADO
                    executor=executor,
                    risk_manager=risk,
                    positions_list=executor.positions
                )

                # Si fue cerrada realmente → eliminar de lista
                if decision.get("closed"):
                    executor.positions.remove(position)

            # =========================
            # 💤 ESPERA
            # =========================
            await asyncio.sleep(cfg.POLL_INTERVAL)

    finally:
        await executor.close()
        await market.close()
        logger.info("🛑 Bot detenido")


if __name__ == "__main__":
    asyncio.run(main_loop())
