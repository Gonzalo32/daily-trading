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
        """
        Inicializa el exchange de Binance.
        En PAPER mode, puede funcionar sin credenciales (solo lectura de precios).
        En LIVE mode, requiere credenciales válidas.
        """
        try:
            # En PAPER mode, podemos usar el exchange sin credenciales para obtener precios
            # En LIVE mode, las credenciales son obligatorias
            api_key = self.config.BINANCE_API_KEY if self.config.TRADING_MODE == "LIVE" else None
            secret = self.config.BINANCE_SECRET_KEY if self.config.TRADING_MODE == "LIVE" else None

            self.exchange = ccxt.binance({
                "apiKey": api_key or "",
                "secret": secret or "",
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                    "adjustForTimeDifference": True
                },
            })

            if self.config.BINANCE_TESTNET:
                self.exchange.set_sandbox_mode(True)

            await self.exchange.load_markets()

            mode_info = f"PAPER (solo lectura)" if self.config.TRADING_MODE == "PAPER" else "LIVE"
            self.logger.info(
                f"✅ Conexión con Binance establecida | Modo: {mode_info} | Testnet: {self.config.BINANCE_TESTNET}")

        except Exception as e:
            # En PAPER mode, si falla la inicialización, solo advertimos (no bloqueamos)
            if self.config.TRADING_MODE == "PAPER":
                self.logger.warning(
                    f"⚠️ No se pudo inicializar exchange de Binance en PAPER mode: {e}. "
                    f"Los precios se obtendrán del parámetro current_price pasado al cerrar posiciones."
                )
                self.exchange = None
            else:
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
    async def close_position(self, position: dict, current_price: Optional[float] = None) -> dict:
        """
        Cierra una posición y calcula el PnL usando precios reales del mercado.

        Args:
            position: Diccionario con datos de la posición a cerrar
            current_price: Precio actual del mercado (opcional, se obtiene del exchange si no se proporciona)

        Returns:
            Dict con success, exit_price, pnl, position
        """
        try:
            symbol = position["symbol"]
            side = str(position["side"]).upper()
            # Las posiciones pueden tener "size" o "quantity"
            size = position.get("size") or position.get("quantity")
            entry = float(position["entry_price"])

            if not size:
                raise ValueError(
                    f"size/quantity no definido en posición: {position}")

            # ============================================
            # OBTENER PRECIO DE SALIDA REAL
            # ============================================
            exit_price: float

            # Prioridad 1: Usar current_price pasado como parámetro (más confiable)
            if current_price is not None:
                exit_price = float(current_price)
                self.logger.debug(
                    f"💰 Usando precio pasado como parámetro: {exit_price:.2f}")

            # Prioridad 2: Obtener del exchange (precio real en tiempo real)
            elif self.config.MARKET == "CRYPTO" and self.exchange:
                try:
                    ticker = await self.exchange.fetch_ticker(symbol)
                    exit_price = float(ticker.get(
                        "last", ticker.get("close", entry)))
                    self.logger.debug(
                        f"💰 Precio obtenido del exchange: {exit_price:.2f}")
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ No se pudo obtener precio del exchange: {e}. "
                        f"Usando precio de entrada como fallback."
                    )
                    exit_price = entry

            # Prioridad 3: Fallback al precio de entrada (último recurso)
            else:
                self.logger.warning(
                    f"⚠️ No hay exchange disponible ni precio proporcionado para {symbol}. "
                    f"Usando precio de entrada como fallback (PnL será 0)."
                )
                exit_price = entry

            # ============================================
            # CALCULAR PnL
            # ============================================
            if side == "BUY":
                pnl = (exit_price - entry) * size
            else:  # SELL/SHORT
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
                f"Entry={entry:.2f} Exit={exit_price:.2f} PnL={pnl:.2f} | "
                f"Size={size:.6f}"
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
                "error": str(e),
                "exit_price": position.get("entry_price", 0),
                "pnl": 0.0
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
