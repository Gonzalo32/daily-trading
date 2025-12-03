"""
Ejecutor de órdenes de trading
Maneja la ejecución, cierre y cancelación de órdenes en distintos mercados.
Compatible con Binance (Testnet o Live) y preparado para Alpaca (acciones).
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import ccxt.async_support as ccxt
from config import Config
from src.utils.logging_setup import setup_logging


class OrderExecutor:
    """Ejecutor de órdenes para diferentes exchanges"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(
            __name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        self.exchange: Optional[ccxt.binance] = None
        self.is_initialized = False
        self.executed_orders: List[Dict[str, Any]] = []
        self.positions: List[Dict[str, Any]] = []

    # ======================================================
    # 🔧 INICIALIZACIÓN
    # ======================================================
    async def initialize(self):
        try:
            if self.config.MARKET == "CRYPTO":
                await self._initialize_crypto_exchange()
            elif self.config.MARKET == "STOCK":
                await self._initialize_stock_api()
            else:
                raise ValueError(f"Mercado no soportado: {self.config.MARKET}")

            self.is_initialized = True
            self.logger.info(
                "✅ Ejecutor de órdenes inicializado correctamente")
        except Exception as e:
            self.logger.exception(
                f"❌ Error inicializando ejecutor de órdenes: {e}")
            raise

    async def _initialize_crypto_exchange(self):
        try:
            self.exchange = ccxt.binance({
                "apiKey": self.config.BINANCE_API_KEY,
                "secret": self.config.BINANCE_SECRET_KEY,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                    "adjustForTimeDifference": True
                },
            })

            if self.config.BINANCE_TESTNET:
                self.exchange.set_sandbox_mode(True)

            await self.exchange.load_markets()
            self.logger.info(
                "✅ Conexión con Binance establecida (modo testnet: %s)", self.config.BINANCE_TESTNET)

        except Exception as e:
            self.logger.exception(f"❌ Error conectando con Binance: {e}")
            raise

    async def _initialize_stock_api(self):
        self.logger.info("ℹ️ API de acciones inicializada (modo simulado)")

    # ======================================================
    # 🚀 EJECUCIÓN
    # ======================================================
    async def execute_order(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not self.is_initialized:
                error_msg = "Ejecutor no inicializado"
                self.logger.error(f"❌ {error_msg}")
                raise RuntimeError(error_msg)

            # Log completo de la señal antes de ejecutar
            self.logger.info(
                f"📤 Ejecutando orden: {signal.get('action', 'UNKNOWN')} {signal.get('symbol', 'UNKNOWN')} "
                f"@ {signal.get('price', 0):.2f} | "
                f"Size: {signal.get('position_size', 0):.6f} | "
                f"SL: {signal.get('stop_loss', 0):.2f} | "
                f"TP: {signal.get('take_profit', 0):.2f} | "
                f"Market: {self.config.MARKET} | "
                f"Mode: {self.config.TRADING_MODE}"
            )

            order_data = self._prepare_order(signal)

            if self.config.MARKET == "CRYPTO":
                result = await self._execute_crypto_order(order_data)
            elif self.config.MARKET == "STOCK":
                result = await self._execute_stock_order(order_data)
            else:
                error_msg = f"Mercado no soportado: {self.config.MARKET}"
                self.logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

            if result["success"]:
                self.executed_orders.append(result["order"])
                self.positions.append(result["position"])
                self.logger.info(
                    f"✅ Trade registrado exitosamente: {result['position']['id']} "
                    f"({result['position'].get('symbol', 'N/A')})"
                )
            else:
                error_detail = result.get('error', 'Error desconocido')
                self.logger.error(
                    f"❌ Falló la ejecución de orden: {error_detail} | "
                    f"Signal: {signal.get('action')} {signal.get('symbol')} @ {signal.get('price')}"
                )

            return result

        except Exception as e:
            error_msg = str(e)
            self.logger.exception(
                f"❌ Error ejecutando orden: {error_msg} | "
                f"Signal: {signal.get('action', 'UNKNOWN')} {signal.get('symbol', 'UNKNOWN')} @ {signal.get('price', 0)}"
            )
            return {"success": False, "order": None, "position": None, "error": error_msg}

    def _prepare_order(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "symbol": signal["symbol"],
            "type": "market",
            "side": signal["action"].lower(),
            "amount": signal["position_size"],
            "price": signal["price"],
            "stop_loss": signal["stop_loss"],
            "take_profit": signal["take_profit"],
            "timestamp": signal["timestamp"],
        }

    async def _execute_crypto_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # ========================
            # ✅ MODO PAPER REAL
            # ========================
            if self.config.TRADING_MODE == "PAPER":
                position = self._create_position(order_data, fake=True)
                return {
                    "success": True,
                    "order": position,
                    "position": position,
                    "error": None
                }

            # ========================
            # ⚠️ MODO REAL
            # ========================
            order = await self.exchange.create_order(
                symbol=order_data["symbol"],
                type=order_data["type"],
                side=order_data["side"],
                amount=order_data["amount"],
            )

            ticker = await self.exchange.fetch_ticker(order_data["symbol"])
            entry_price = ticker.get("last")

            position = self._create_position(order_data)
            position["id"] = order["id"]
            position["entry_price"] = entry_price

            await self._place_stop_orders(position)

            self.logger.info(
                f"✅ Orden ejecutada en Binance: {position['id']} @ {entry_price:.2f}")

            return {
                "success": True,
                "order": order,
                "position": position,
                "error": None
            }

        except Exception as e:
            error_msg = str(e)
            self.logger.exception(
                f"❌ Error ejecutando orden crypto: {error_msg} | "
                f"Symbol: {order_data.get('symbol')} | "
                f"Side: {order_data.get('side')} | "
                f"Amount: {order_data.get('amount')} | "
                f"Type: {order_data.get('type')}"
            )
            return {"success": False, "order": None, "position": None, "error": error_msg}

    async def _execute_stock_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            position = self._create_position(order_data, fake=True)
            return {
                "success": True,
                "order": position,
                "position": position,
                "error": None
            }

        except Exception as e:
            error_msg = str(e)
            self.logger.exception(
                f"❌ Error ejecutando orden acciones: {error_msg} | "
                f"Symbol: {order_data.get('symbol')} | "
                f"Side: {order_data.get('side')} | "
                f"Amount: {order_data.get('amount')}"
            )
            return {"success": False, "order": None, "position": None, "error": error_msg}

    def _create_position(self, order_data: Dict[str, Any], fake: bool = False) -> Dict[str, Any]:
        return {
            "id": f"paper_{datetime.utcnow().timestamp()}" if fake else "",
            "symbol": order_data["symbol"],
            "side": order_data["side"].upper(),
            "entry_price": order_data["price"],
            "size": order_data["amount"],
            "stop_loss": order_data["stop_loss"],
            "take_profit": order_data["take_profit"],
            "entry_time": datetime.utcnow(),
            "status": "open",
        }

    async def _place_stop_orders(self, position: Dict[str, Any]):
        return None

    # ======================================================
    # 🔁 CIERRE
    # ======================================================
    async def close_position(self, position: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.config.TRADING_MODE == "PAPER":
                exit_price = position["entry_price"]  # cero PnL simulado
            else:
                close_side = "sell" if position["side"] == "BUY" else "buy"
                await self.exchange.create_order(
                    symbol=position["symbol"],
                    type="market",
                    side=close_side,
                    amount=position["size"],
                )

                ticker = await self.exchange.fetch_ticker(position["symbol"])
                exit_price = ticker.get("last")

            pnl = (
                (exit_price - position["entry_price"]) * position["size"]
                if position["side"] == "BUY"
                else
                (position["entry_price"] - exit_price) * position["size"]
            )

            self.logger.info(
                f"💸 Posición cerrada {position['symbol']} | PnL: {pnl:.2f}")

            return {"success": True, "pnl": pnl, "exit_price": exit_price, "error": None}

        except Exception as e:
            self.logger.exception(f"❌ Error cerrando posición: {e}")
            return {"success": False, "pnl": 0.0, "error": str(e)}

    def get_order_history(self) -> List[Dict[str, Any]]:
        return list(self.executed_orders)

    async def cancel_all_orders(self):
        try:
            if self.exchange:
                await self.exchange.cancel_all_orders()
                self.logger.info("✅ Todas las órdenes canceladas")
        except Exception as e:
            self.logger.exception(f"❌ Error cancelando órdenes: {e}")

    async def close(self):
        try:
            if self.exchange:
                await self.exchange.close()
            self.logger.info("✅ Conexión del ejecutor cerrada")
        except Exception as e:
            self.logger.exception(f"❌ Error al cerrar OrderExecutor: {e}")
