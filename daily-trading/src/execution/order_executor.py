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
    # 🔁 CIERRE DE POSICIONES
    # ======================================================
    async def close_position(self, position: dict) -> dict:
        """
        Cierra una posición y calcula el PnL.
        Funciona tanto en PAPER como en REAL (usa el ticker del exchange si hay).
        """
        try:
            symbol = position["symbol"]
            side = str(position["side"]).upper()
            # Tus posiciones se crean con "size", no con "quantity"
            size = position.get("size") or position.get("quantity")
            entry = float(position["entry_price"])

            if not size:
                raise ValueError(
                    f"size/quantity no definido en posición: {position}")

            # Precio de salida
            exit_price: float
            if self.config.MARKET == "CRYPTO" and self.exchange:
                ticker = await self.exchange.fetch_ticker(symbol)
                exit_price = float(ticker["last"])
            else:
                # Fallback: cerramos al último precio conocido o al entry
                exit_price = float(position.get("current_price", entry))

            # PnL
            if side == "BUY":
                pnl = (exit_price - entry) * size
            else:  # SELL
                pnl = (entry - exit_price) * size

            # Marcar posición como cerrada
            position["status"] = "closed"
            position["exit_price"] = exit_price
            position["exit_time"] = datetime.utcnow()
            position["pnl"] = pnl

            # Sacarla de la lista interna de posiciones activas
            if position in self.positions:
                self.positions.remove(position)

            self.logger.info(
                f"💸 Posición cerrada {symbol} | {side} | "
                f"Entry={entry:.2f} Exit={exit_price:.2f} PnL={pnl:.2f}"
            )

            return {
                "success": True,
                "exit_price": exit_price,
                "pnl": pnl,
                "position": position,
            }

        except Exception as e:
            self.logger.exception(f"❌ Error cerrando posición: {e}")
            return {
                "success": False,
                "error": str(e)
            }

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

    # src/execution/order_executor.py

    async def close_position(self, position: dict) -> dict:
        try:
            symbol = position["symbol"]
            side = position["side"]
            size = position["quantity"]
            entry = position["entry_price"]

            ticker = await self.exchange.fetch_ticker(symbol)
            exit_price = ticker["last"]

            # PnL
            if side.upper() == "BUY":
                pnl = (exit_price - entry) * size
            else:
                pnl = (entry - exit_price) * size

            # Remover de posiciones activas
            if position in self.positions:
                self.positions.remove(position)

            # LOG
            self.logger.info(
                f"💸 Posición cerrada {symbol} | "
                f"{side} | Entry={entry:.2f} "
                f"Exit={exit_price:.2f} "
                f"PnL={pnl:.2f}"
            )

            return {
                "success": True,
                "exit_price": exit_price,
                "pnl": pnl,
            }

        except Exception as e:
            self.logger.error(f"❌ Error cerrando posición: {e}")
            return {
                "success": False,
                "error": str(e)
            }
