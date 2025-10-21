"""
Ejecutor de órdenes de trading
Maneja la ejecución de órdenes de compra/venta en diferentes exchanges
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import ccxt
import requests
from config import Config

class OrderExecutor:
    """Ejecutor de órdenes para diferentes exchanges"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Inicializar exchange
        self.exchange = None
        self.is_initialized = False
        
        # Estado de órdenes
        self.pending_orders = []
        self.executed_orders = []
        
    async def initialize(self):
        """Inicializar el ejecutor de órdenes"""
        try:
            if self.config.MARKET == 'CRYPTO':
                await self._initialize_crypto_exchange()
            elif self.config.MARKET == 'STOCK':
                await self._initialize_stock_api()
            else:
                raise ValueError(f"Mercado no soportado: {self.config.MARKET}")
                
            self.is_initialized = True
            self.logger.info("✅ Ejecutor de órdenes inicializado correctamente")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando ejecutor de órdenes: {e}")
            raise
            
    async def _initialize_crypto_exchange(self):
        """Inicializar exchange de criptomonedas"""
        try:
            # Configurar Binance
            self.exchange = ccxt.binance({
                'apiKey': self.config.BINANCE_API_KEY,
                'secret': self.config.BINANCE_SECRET_KEY,
                'sandbox': self.config.BINANCE_TESTNET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            # Verificar conexión
            await self.exchange.load_markets()
            self.logger.info("✅ Conexión con Binance establecida")
            
        except Exception as e:
            self.logger.error(f"❌ Error conectando con Binance: {e}")
            raise
            
    async def _initialize_stock_api(self):
        """Inicializar API de acciones"""
        # Para acciones, usaríamos Alpaca o similar
        # Por ahora, implementación básica
        self.logger.info("✅ API de acciones configurada")
        
    async def execute_order(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar orden de trading"""
        try:
            if not self.is_initialized:
                raise Exception("Ejecutor de órdenes no inicializado")
                
            # Preparar orden
            order_data = self._prepare_order(signal)
            
            # Ejecutar orden según el mercado
            if self.config.MARKET == 'CRYPTO':
                result = await self._execute_crypto_order(order_data)
            elif self.config.MARKET == 'STOCK':
                result = await self._execute_stock_order(order_data)
            else:
                raise ValueError(f"Mercado no soportado: {self.config.MARKET}")
                
            # Registrar orden ejecutada
            if result['success']:
                self.executed_orders.append(result['order'])
                self.logger.info(f"✅ Orden ejecutada: {result['order']['id']}")
            else:
                self.logger.error(f"❌ Error ejecutando orden: {result['error']}")
                
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando orden: {e}")
            return {
                'success': False,
                'error': str(e),
                'order': None
            }
            
    def _prepare_order(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Preparar datos de la orden"""
        try:
            # Determinar tipo de orden
            order_type = 'market'  # Por simplicidad, siempre market orders
            
            # Calcular cantidad
            quantity = signal['position_size']
            
            # Preparar datos de la orden
            order_data = {
                'symbol': signal['symbol'],
                'type': order_type,
                'side': signal['action'].lower(),
                'amount': quantity,
                'price': signal['price'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'timestamp': signal['timestamp']
            }
            
            return order_data
            
        except Exception as e:
            self.logger.error(f"❌ Error preparando orden: {e}")
            raise
            
    async def _execute_crypto_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar orden en exchange de criptomonedas"""
        try:
            # Ejecutar orden principal
            order = await self.exchange.create_order(
                symbol=order_data['symbol'],
                type=order_data['type'],
                side=order_data['side'],
                amount=order_data['amount']
            )
            
            # Crear posición
            position = {
                'id': order['id'],
                'symbol': order_data['symbol'],
                'side': order_data['side'],
                'entry_price': order['price'],
                'size': order_data['amount'],
                'stop_loss': order_data['stop_loss'],
                'take_profit': order_data['take_profit'],
                'entry_time': datetime.now(),
                'status': 'open'
            }
            
            # Colocar stop loss y take profit (si el exchange lo soporta)
            await self._place_stop_orders(position)
            
            return {
                'success': True,
                'order': position,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando orden de cripto: {e}")
            return {
                'success': False,
                'order': None,
                'error': str(e)
            }
            
    async def _execute_stock_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar orden en mercado de acciones"""
        try:
            # Simular ejecución de orden de acciones
            # En implementación real, usaríamos Alpaca API
            
            position = {
                'id': f"stock_{datetime.now().timestamp()}",
                'symbol': order_data['symbol'],
                'side': order_data['side'],
                'entry_price': order_data['price'],
                'size': order_data['amount'],
                'stop_loss': order_data['stop_loss'],
                'take_profit': order_data['take_profit'],
                'entry_time': datetime.now(),
                'status': 'open'
            }
            
            return {
                'success': True,
                'order': position,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando orden de acciones: {e}")
            return {
                'success': False,
                'order': None,
                'error': str(e)
            }
            
    async def _place_stop_orders(self, position: Dict[str, Any]):
        """Colocar órdenes de stop loss y take profit"""
        try:
            if self.config.MARKET == 'CRYPTO':
                # Para cripto, usar stop loss y take profit del exchange
                # Por simplicidad, no implementamos esto aquí
                pass
            elif self.config.MARKET == 'STOCK':
                # Para acciones, usar órdenes condicionales
                # Por simplicidad, no implementamos esto aquí
                pass
                
        except Exception as e:
            self.logger.error(f"❌ Error colocando órdenes de stop: {e}")
            
    async def close_position(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Cerrar posición abierta"""
        try:
            if not self.is_initialized:
                raise Exception("Ejecutor de órdenes no inicializado")
                
            # Determinar lado de cierre
            close_side = 'sell' if position['side'] == 'BUY' else 'buy'
            
            # Ejecutar orden de cierre
            if self.config.MARKET == 'CRYPTO':
                result = await self._close_crypto_position(position, close_side)
            elif self.config.MARKET == 'STOCK':
                result = await self._close_stock_position(position, close_side)
            else:
                raise ValueError(f"Mercado no soportado: {self.config.MARKET}")
                
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error cerrando posición: {e}")
            return {
                'success': False,
                'error': str(e),
                'pnl': 0.0
            }
            
    async def _close_crypto_position(self, position: Dict[str, Any], close_side: str) -> Dict[str, Any]:
        """Cerrar posición de criptomonedas"""
        try:
            # Ejecutar orden de cierre
            close_order = await self.exchange.create_order(
                symbol=position['symbol'],
                type='market',
                side=close_side,
                amount=position['size']
            )
            
            # Calcular PnL
            entry_price = position['entry_price']
            exit_price = close_order['price']
            size = position['size']
            
            if position['side'] == 'BUY':
                pnl = (exit_price - entry_price) * size
            else:
                pnl = (entry_price - exit_price) * size
                
            return {
                'success': True,
                'pnl': pnl,
                'exit_price': exit_price,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error cerrando posición de cripto: {e}")
            return {
                'success': False,
                'pnl': 0.0,
                'error': str(e)
            }
            
    async def _close_stock_position(self, position: Dict[str, Any], close_side: str) -> Dict[str, Any]:
        """Cerrar posición de acciones"""
        try:
            # Simular cierre de posición de acciones
            # En implementación real, usaríamos Alpaca API
            
            # Simular precio de salida
            exit_price = position['entry_price'] * 1.02  # 2% de ganancia simulada
            
            # Calcular PnL
            entry_price = position['entry_price']
            size = position['size']
            
            if position['side'] == 'BUY':
                pnl = (exit_price - entry_price) * size
            else:
                pnl = (entry_price - exit_price) * size
                
            return {
                'success': True,
                'pnl': pnl,
                'exit_price': exit_price,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error cerrando posición de acciones: {e}")
            return {
                'success': False,
                'pnl': 0.0,
                'error': str(e)
            }
            
    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """Obtener posiciones abiertas"""
        try:
            if self.config.MARKET == 'CRYPTO':
                return await self._get_crypto_positions()
            elif self.config.MARKET == 'STOCK':
                return await self._get_stock_positions()
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo posiciones abiertas: {e}")
            return []
            
    async def _get_crypto_positions(self) -> List[Dict[str, Any]]:
        """Obtener posiciones abiertas de criptomonedas"""
        try:
            # Obtener balance
            balance = await self.exchange.fetch_balance()
            
            # Filtrar balances con cantidad > 0
            positions = []
            for symbol, amount in balance['free'].items():
                if amount > 0:
                    positions.append({
                        'symbol': symbol,
                        'amount': amount,
                        'side': 'BUY'
                    })
                    
            return positions
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo posiciones de cripto: {e}")
            return []
            
    async def _get_stock_positions(self) -> List[Dict[str, Any]]:
        """Obtener posiciones abiertas de acciones"""
        try:
            # Simular posiciones de acciones
            # En implementación real, usaríamos Alpaca API
            return []
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo posiciones de acciones: {e}")
            return []
            
    def get_order_history(self) -> List[Dict[str, Any]]:
        """Obtener historial de órdenes"""
        return self.executed_orders.copy()
        
    async def cancel_all_orders(self):
        """Cancelar todas las órdenes pendientes"""
        try:
            if self.config.MARKET == 'CRYPTO':
                await self.exchange.cancel_all_orders()
            elif self.config.MARKET == 'STOCK':
                # Implementar cancelación para acciones
                pass
                
            self.logger.info("✅ Todas las órdenes canceladas")
            
        except Exception as e:
            self.logger.error(f"❌ Error cancelando órdenes: {e}")
            
    async def close(self):
        """Cerrar conexiones"""
        try:
            if self.exchange:
                await self.exchange.close()
            self.logger.info("✅ Conexiones cerradas correctamente")
        except Exception as e:
            self.logger.error(f"❌ Error cerrando conexiones: {e}")
