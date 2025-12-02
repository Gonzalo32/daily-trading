"""
Ejecutor de órdenes de trading
Maneja la ejecución, cierre y cancelación de órdenes en distintos mercados.
Compatible con Binance (Testnet o Live) y preparado para Alpaca (acciones).
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import ccxt.async_support as ccxt  # ✅ versión asíncrona
from config import Config
from src.utils.logging_setup import setup_logging


class OrderExecutor:
    """Ejecutor de órdenes para diferentes exchanges"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(__name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        self.exchange: Optional[ccxt.binance] = None
        self.is_initialized = False
        self.executed_orders: List[Dict[str, Any]] = []
        self.positions: List[Dict[str, Any]] = []

    # ======================================================
    # 🔧 INICIALIZACIÓN
    # ======================================================
    async def initialize(self):
        """Inicializar el ejecutor de órdenes"""
        try:
            if self.config.MARKET == "CRYPTO":
                await self._initialize_crypto_exchange()
            elif self.config.MARKET == "STOCK":
                await self._initialize_stock_api()
            else:
                raise ValueError(f"Mercado no soportado: {self.config.MARKET}")

            self.is_initialized = True
            self.logger.info("✅ Ejecutor de órdenes inicializado correctamente")
        except Exception as e:
            self.logger.exception(f"❌ Error inicializando ejecutor de órdenes: {e}")
            raise

    async def _initialize_crypto_exchange(self):
        """Inicializar conexión con Binance"""
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
            self.logger.info("✅ Conexión con Binance establecida (modo testnet: %s)", self.config.BINANCE_TESTNET)

        except Exception as e:
            self.logger.exception(f"❌ Error conectando con Binance: {e}")
            raise

    async def _initialize_stock_api(self):
        """Inicializar API de acciones (Alpaca o similar)"""
        self.logger.info("ℹ️ API de acciones inicializada (modo simulado)")

    # ======================================================
    # 🚀 EJECUCIÓN DE ÓRDENES
    # ======================================================
    async def execute_order(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar orden de trading según la señal recibida"""
        try:
            if not self.is_initialized:
                raise RuntimeError("Ejecutor de órdenes no inicializado")

            order_data = self._prepare_order(signal)

            if self.config.MARKET == "CRYPTO":
                result = await self._execute_crypto_order(order_data)
            elif self.config.MARKET == "STOCK":
                result = await self._execute_stock_order(order_data)
            else:
                raise ValueError(f"Mercado no soportado: {self.config.MARKET}")

            if result["success"]:
                self.executed_orders.append(result["order"])
                self.logger.info(f"✅ Orden ejecutada: {result['order']['id']}")
            else:
                self.logger.error(f"❌ Falló la ejecución de orden: {result['error']}")

            return result
        except Exception as e:
            self.logger.exception(f"❌ Error ejecutando orden: {e}")
            return {"success": False, "order": None, "error": str(e)}

    def _prepare_order(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Preparar datos de la orden antes de enviarla al exchange"""
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
        """Ejecutar orden en Binance (modo async)"""
        try:
            order = await self.exchange.create_order(
                symbol=order_data["symbol"],
                type=order_data["type"],
                side=order_data["side"],
                amount=order_data["amount"],
            )

            ticker = await self.exchange.fetch_ticker(order_data["symbol"])
            entry_price = ticker.get("last")

            position = {
                "id": order["id"],
                "symbol": order_data["symbol"],
                "side": order_data["side"].upper(),
                "entry_price": entry_price,
                "size": order_data["amount"],
                "stop_loss": order_data["stop_loss"],
                "take_profit": order_data["take_profit"],
                "entry_time": datetime.now(),
                "status": "open",
            }

            await self._place_stop_orders(position)

            self.executed_orders.append(position)
            self.logger.info(f"✅ Orden ejecutada: {position['id']} a {entry_price:.4f}")
            return {
    "success": True,
    "order": position,
    "position": position,
    "error": None
}

        except Exception as e:
            self.logger.exception(f"❌ Error ejecutando orden: {e}")
            return {"success": False, "order": None, "error": str(e)}

    async def _execute_stock_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simular ejecución de orden de acciones (modo papel)"""
        try:
            position = {
                "id": f"stock_{datetime.now().timestamp()}",
                "symbol": order_data["symbol"],
                "side": order_data["side"].upper(),
                "entry_price": order_data["price"],
                "size": order_data["amount"],
                "stop_loss": order_data["stop_loss"],
                "take_profit": order_data["take_profit"],
                "entry_time": datetime.now(),
                "status": "open",
            }
            return {
    "success": True,
    "order": position,
    "position": position,
    "error": None
}

        except Exception as e:
            self.logger.exception(f"❌ Error ejecutando orden de acciones: {e}")
            return {"success": False, "order": None, "error": str(e)}

    async def _place_stop_orders(self, position: Dict[str, Any]):
        """Preparado para implementar OCO o Stop-Limit en el futuro"""
        return None

    # ======================================================
    # 🔁 CIERRE DE POSICIONES
    # ======================================================
    async def close_position(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Cerrar posición abierta"""
        close_side = "sell" if position["side"] == "BUY" else "buy"
        try:
            close_order = await self.exchange.create_order(
                symbol=position["symbol"],
                type="market",
                side=close_side,
                amount=position["size"],
            )

            ticker = await self.exchange.fetch_ticker(position["symbol"])
            exit_price = ticker.get("last")

            if position["side"] == "BUY":
                pnl = (exit_price - position["entry_price"]) * position["size"]
            else:
                pnl = (position["entry_price"] - exit_price) * position["size"]

            self.logger.info(f"💸 Posición cerrada ({position['symbol']}) | PnL: {pnl:.2f}")
            return {"success": True, "pnl": pnl, "exit_price": exit_price, "error": None}

        except Exception as e:
            self.logger.exception(f"❌ Error cerrando posición: {e}")
            return {"success": False, "pnl": 0.0, "error": str(e)}

    # ======================================================
    # 📊 CONSULTAS Y GESTIÓN
    # ======================================================
    def get_order_history(self) -> List[Dict[str, Any]]:
        """Obtener historial de órdenes ejecutadas"""
        return list(self.executed_orders)

    async def cancel_all_orders(self):
        """Cancelar todas las órdenes abiertas"""
        try:
            await self.exchange.cancel_all_orders()
            self.logger.info("✅ Todas las órdenes canceladas exitosamente")
        except Exception as e:
            self.logger.exception(f"❌ Error cancelando órdenes: {e}")

    # ======================================================
    # 🧹 CIERRE DE CONEXIONES
    # ======================================================
    async def close(self):
        """Cerrar conexión del exchange"""
        try:
            if self.exchange is not None:
                await self.exchange.close()
            self.logger.info("✅ Conexión del ejecutor cerrada correctamente")
        except Exception as e:
            self.logger.exception(f"❌ Error al cerrar OrderExecutor: {e}")
