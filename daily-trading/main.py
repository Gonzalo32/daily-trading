"""
Bot de Day Trading Automatizado
Archivo principal que orquesta todos los componentes del sistema
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

from config import Config
from src.data.market_data import MarketDataProvider
from src.strategy.trading_strategy import TradingStrategy
from src.risk.risk_manager import RiskManager
from src.execution.order_executor import OrderExecutor
from src.monitoring.dashboard import Dashboard
from src.utils.logger import setup_logger
from src.utils.notifications import NotificationManager
from src.ml.trade_recorder import TradeRecorder

class TradingBot:
    """Bot principal de trading automatizado"""
    
    def __init__(self):
        self.config = Config()
        self.logger = setup_logger(self.config.LOG_LEVEL, self.config.LOG_FILE)
        
        # Inicializar componentes
        self.market_data = MarketDataProvider(self.config)
        self.strategy = TradingStrategy(self.config)
        self.risk_manager = RiskManager(self.config)
        self.order_executor = OrderExecutor(self.config)
        self.dashboard = Dashboard(self.config) if self.config.ENABLE_DASHBOARD else None
        self.notifications = NotificationManager(self.config)
        self.trade_recorder = TradeRecorder() if self.config.ENABLE_ML else None  # Sistema de aprendizaje
        
        # Estado del bot
        self.is_running = False
        self.current_positions = []
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.current_signal = None  # Señal actual que está analizando
        self.position_market_data = {}  # Guardar datos de mercado al abrir posiciones
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    async def start(self):
        """Iniciar el bot de trading"""
        try:
            self.logger.info("🚀 Iniciando Bot de Day Trading...")
            
            # Verificar configuración
            if not self._validate_config():
                self.logger.error("❌ Configuración inválida. Abortando...")
                return
                
            # Inicializar componentes
            await self._initialize_components()
            
            # Iniciar dashboard si está habilitado
            if self.dashboard:
                await self.dashboard.start()
                
            # Iniciar bucle principal
            self.is_running = True
            await self._main_loop()
            
        except Exception as e:
            self.logger.error(f"❌ Error crítico en el bot: {e}")
            await self._emergency_shutdown()
            
    async def stop(self):
        """Detener el bot de trading"""
        self.logger.info("🛑 Deteniendo Bot de Day Trading...")
        self.is_running = False
        
        # Cerrar posiciones abiertas si es necesario
        if self.current_positions:
            self.logger.warning("⚠️ Cerrando posiciones abiertas...")
            await self._close_all_positions()
            
        # Detener dashboard
        if self.dashboard:
            await self.dashboard.stop()
            
        self.logger.info("✅ Bot detenido correctamente")
        
    async def _main_loop(self):
        """Bucle principal del bot"""
        self.logger.info("🔄 Iniciando bucle principal de trading...")
        
        while self.is_running:
            try:
                # Verificar si es horario de trading
                if not self._is_trading_time():
                    await asyncio.sleep(60)  # Esperar 1 minuto
                    continue
                    
                # Obtener datos de mercado
                market_data = await self.market_data.get_latest_data()
                if not market_data:
                    self.logger.warning("⚠️ No se pudieron obtener datos de mercado")
                    await asyncio.sleep(10)
                    continue
                    
                # Verificar límites de riesgo diario
                if not self.risk_manager.check_daily_limits(self.daily_pnl, self.daily_trades):
                    self.logger.warning("⚠️ Límites de riesgo diario alcanzados. Pausando trading...")
                    await asyncio.sleep(300)  # Esperar 5 minutos
                    continue
                    
                # Generar señal de trading
                signal = await self.strategy.generate_signal(market_data)
                self.current_signal = signal  # Guardar señal actual para el dashboard
                
                if signal:
                    # Verificar riesgo de la operación
                    if self.risk_manager.validate_trade(signal, self.current_positions):
                        # Ejecutar orden
                        order_result = await self.order_executor.execute_order(signal)
                        
                        if order_result['success']:
                            position = order_result['position']
                            self.current_positions.append(position)
                            self.daily_trades += 1
                            self.logger.info(f"✅ Orden ejecutada: {signal['action']} {signal['symbol']}")
                            
                            # Guardar datos de mercado al abrir posición (para aprendizaje)
                            if self.trade_recorder:
                                self.position_market_data[position['id']] = market_data.copy()
                            
                            # Enviar notificación
                            await self.notifications.send_trade_notification(order_result)
                        else:
                            self.logger.error(f"❌ Error ejecutando orden: {order_result['error']}")
                    else:
                        self.logger.info("ℹ️ Operación rechazada por gestión de riesgo")
                        
                # Verificar posiciones abiertas
                await self._check_open_positions(market_data)
                
                # Actualizar dashboard (siempre, incluso sin datos de mercado)
                if self.dashboard:
                    try:
                        dashboard_payload = self._build_dashboard_payload(market_data)
                        await self.dashboard.update_data(dashboard_payload)
                    except Exception as e:
                        self.logger.error(f"❌ Error actualizando dashboard: {e}")
                    
                # Esperar antes de la siguiente iteración
                await asyncio.sleep(1)  # 1 segundo entre iteraciones
                
            except Exception as e:
                self.logger.error(f"❌ Error en bucle principal: {e}")
                await asyncio.sleep(10)
                
    async def _check_open_positions(self, market_data):
        """Verificar y gestionar posiciones abiertas"""
        for position in self.current_positions[:]:
            # Verificar stop loss y take profit
            if self.risk_manager.should_close_position(position, market_data):
                # Cerrar posición
                close_result = await self.order_executor.close_position(position)
                
                if close_result['success']:
                    self.current_positions.remove(position)
                    self.daily_pnl += close_result['pnl']
                    self.logger.info(f"✅ Posición cerrada: PnL = {close_result['pnl']:.2f}")
                    
                    # Registrar operación para aprendizaje
                    if self.trade_recorder and position['id'] in self.position_market_data:
                        entry_market_data = self.position_market_data.pop(position['id'])
                        entry_data = {
                            'entry_time': position.get('entry_time', datetime.now()),
                            'symbol': position.get('symbol'),
                            'action': position.get('side'),
                            'entry_price': position.get('entry_price'),
                            'size': position.get('size'),
                            'stop_loss': position.get('stop_loss'),
                            'take_profit': position.get('take_profit'),
                            'strength': self.current_signal.get('strength') if self.current_signal else 0,
                        }
                        exit_data = {
                            'exit_time': datetime.now(),
                            'exit_price': close_result.get('exit_price', market_data.get('price')),
                            'pnl': close_result['pnl'],
                        }
                        self.trade_recorder.record_trade(entry_data, exit_data, entry_market_data, market_data)
                        self.logger.info("📚 Operación registrada para aprendizaje")
                    
                    # Enviar notificación
                    await self.notifications.send_position_closed_notification(close_result)
                else:
                    self.logger.error(f"❌ Error cerrando posición: {close_result['error']}")
                    
    async def _close_all_positions(self):
        """Cerrar todas las posiciones abiertas"""
        for position in self.current_positions[:]:
            close_result = await self.order_executor.close_position(position)
            if close_result['success']:
                self.current_positions.remove(position)
                self.daily_pnl += close_result['pnl']

    def _build_dashboard_payload(self, market_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Construir un payload serializable para el dashboard web"""
        positions = []
        for position in self.current_positions:
            entry_time = position.get('entry_time')
            if isinstance(entry_time, datetime):
                entry_time = entry_time.isoformat()
            positions.append({
                'symbol': position.get('symbol'),
                'side': (position.get('side') or '').upper(),
                'entry_price': self._safe_float(position.get('entry_price')),
                'size': self._safe_float(position.get('size')),
                'stop_loss': self._safe_float(position.get('stop_loss')),
                'take_profit': self._safe_float(position.get('take_profit')),
                'entry_time': entry_time,
                'pnl': self._safe_float(position.get('pnl', 0.0)) or 0.0,
            })

        metrics = {
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'win_rate': None,
            'max_drawdown': None,
        }

        balance = {
            'current': float(self.config.INITIAL_CAPITAL + self.daily_pnl),
            'peak': float(max(self.config.INITIAL_CAPITAL, self.config.INITIAL_CAPITAL + self.daily_pnl)),
            'exposure': sum(
                (self._safe_float(p.get('size')) or 0.0) * (self._safe_float(p.get('entry_price')) or 0.0)
                for p in self.current_positions
            )
        }

        market_snapshot = None
        if market_data:
            market_snapshot = {
                'symbol': market_data.get('symbol'),
                'price': self._safe_float(market_data.get('price')),
                'open': self._safe_float(market_data.get('open')),
                'high': self._safe_float(market_data.get('high')),
                'low': self._safe_float(market_data.get('low')),
                'close': self._safe_float(market_data.get('price')),  # Precio actual como close
                'volume': self._safe_float(market_data.get('volume')),
                'change': self._safe_float(market_data.get('change')),
                'change_percent': self._safe_float(market_data.get('change_percent')),
            }
            
            # Agregar datos OHLC históricos si están disponibles
            if 'dataframe' in market_data:
                df = market_data.get('dataframe')
                if df is not None and hasattr(df, 'tail') and len(df) > 0:
                    # Obtener últimas 200 velas para más contexto histórico
                    recent_candles = df.tail(200)
                    market_snapshot['ohlc_history'] = [
                        {
                            'timestamp': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                            'open': float(row.get('open', 0)),
                            'high': float(row.get('high', 0)),
                            'low': float(row.get('low', 0)),
                            'close': float(row.get('close', 0)),
                            'volume': float(row.get('volume', 0))
                        }
                        for idx, row in recent_candles.iterrows()
                    ]

            timestamp = market_data.get('timestamp')
            if isinstance(timestamp, datetime):
                market_snapshot['timestamp'] = timestamp.isoformat()

            indicators = market_data.get('indicators', {})
            market_snapshot['indicators'] = {
                name: self._safe_float(value)
                for name, value in indicators.items()
                if value is not None
            }

        # Preparar señal actual para el dashboard
        current_signal_snapshot = None
        if self.current_signal:
            current_signal_snapshot = {
                'action': self.current_signal.get('action'),
                'strength': self._safe_float(self.current_signal.get('strength')),
                'reason': self.current_signal.get('reason'),
                'stop_loss': self._safe_float(self.current_signal.get('stop_loss')),
                'take_profit': self._safe_float(self.current_signal.get('take_profit')),
            }

        return {
            'positions': positions,
            'metrics': metrics,
            'balance': balance,
            'market': market_snapshot,
            'current_signal': current_signal_snapshot,
        }

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Intentar convertir un valor numérico a float serializable"""
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
                
    def _validate_config(self) -> bool:
        """Validar configuración del bot"""
        try:
            # Verificar configuración de mercado
            if self.config.MARKET == 'CRYPTO' and not self.config.BINANCE_API_KEY:
                self.logger.error("❌ API Key de Binance no configurada")
                return False
                
            if self.config.MARKET == 'STOCK' and not self.config.ALPACA_API_KEY:
                self.logger.error("❌ API Key de Alpaca no configurada")
                return False
                
            # Verificar límites de riesgo
            if self.config.RISK_PER_TRADE <= 0 or self.config.RISK_PER_TRADE > 0.1:
                self.logger.error("❌ Riesgo por trade debe estar entre 0 y 0.1 (10%)")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error validando configuración: {e}")
            return False
            
    async def _initialize_components(self):
        """Inicializar todos los componentes del bot"""
        self.logger.info("🔧 Inicializando componentes...")
        
        # Inicializar proveedor de datos
        await self.market_data.initialize()
        
        # Inicializar ejecutor de órdenes
        await self.order_executor.initialize()
        
        # Inicializar notificaciones
        if self.config.ENABLE_NOTIFICATIONS:
            await self.notifications.initialize()
            
        self.logger.info("✅ Componentes inicializados correctamente")
        
    def _is_trading_time(self) -> bool:
        """Verificar si es horario de trading"""
        if self.config.MARKET == 'CRYPTO':
            return True  # Cripto opera 24/7
            
        # Para acciones, verificar horario de mercado
        current_hour = datetime.now().hour
        return self.config.TRADING_START_HOUR <= current_hour < self.config.TRADING_END_HOUR
        
    async def _emergency_shutdown(self):
        """Cierre de emergencia del bot"""
        self.logger.critical("🚨 Ejecutando cierre de emergencia...")
        
        try:
            # Cerrar todas las posiciones
            await self._close_all_positions()
            
            # Enviar notificación de emergencia
            await self.notifications.send_emergency_notification("Bot detenido por error crítico")
            
        except Exception as e:
            self.logger.error(f"❌ Error en cierre de emergencia: {e}")
        finally:
            self.is_running = False
            
    def _signal_handler(self, signum, frame):
        """Manejador de señales del sistema"""
        self.logger.info(f"📡 Señal recibida: {signum}")
        asyncio.create_task(self.stop())

async def main():
    """Función principal"""
    bot = TradingBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n🛑 Interrupción del usuario")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
