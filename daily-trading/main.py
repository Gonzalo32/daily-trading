"""
Bot de Day Trading Automatizado AVANZADO
Archivo principal que orquesta todos los componentes del sistema con:
- Preparación diaria (análisis de régimen)
- Parámetros dinámicos
- Filtro ML
- Gestión avanzada de posiciones
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from config import Config
from src.data.market_data import MarketDataProvider
from src.strategy.trading_strategy import TradingStrategy
from src.strategy.market_regime import MarketRegimeClassifier
from src.strategy.dynamic_parameters import DynamicParameterManager
from src.risk.risk_manager import RiskManager
from src.risk.advanced_position_manager import AdvancedPositionManager
from src.execution.order_executor import OrderExecutor
from src.monitoring.dashboard import Dashboard
from src.utils.logger import setup_logger
from src.utils.notifications import NotificationManager
from src.ml.trade_recorder import TradeRecorder
from src.ml.ml_signal_filter import MLSignalFilter

class TradingBot:
    """
    Bot principal de trading automatizado con:
    - Análisis de régimen diario
    - Adaptación de parámetros
    - Filtrado ML inteligente
    - Gestión avanzada de posiciones
    """
    
    def __init__(self):
        self.config = Config()
        self.logger = setup_logger(self.config.LOG_LEVEL, self.config.LOG_FILE)
        
        # Inicializar componentes principales
        self.market_data = MarketDataProvider(self.config)
        self.strategy = TradingStrategy(self.config)
        self.risk_manager = RiskManager(self.config)
        self.order_executor = OrderExecutor(self.config)
        self.dashboard = Dashboard(self.config) if self.config.ENABLE_DASHBOARD else None
        self.notifications = NotificationManager(self.config)
        
        # Componentes avanzados
        self.regime_classifier = MarketRegimeClassifier(self.config)
        self.param_manager = DynamicParameterManager(self.config)
        self.position_manager = AdvancedPositionManager(self.config)
        
        # ML components
        self.trade_recorder = TradeRecorder(config=self.config) if self.config.ENABLE_ML else None
        self.ml_filter = MLSignalFilter(self.config) if self.config.ENABLE_ML else None
        
        # Estado del bot
        self.is_running = False
        self.current_positions = []
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.current_signal = None  # Señal actual que está analizando
        self.position_market_data = {}  # Guardar datos de mercado al abrir posiciones
        
        # Estado de preparación diaria
        self.daily_prepared = False
        self.last_preparation_date = None
        self.current_regime_info = None
        self.current_parameters = None
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    async def start(self):
        """Iniciar el bot de trading"""
        try:
            self.logger.info("🚀 Iniciando Bot de Day Trading Avanzado...")
            self.logger.info("=" * 60)
            
            # Verificar configuración
            if not self._validate_config():
                self.logger.error("❌ Configuración inválida. Abortando...")
                return
                
            # Inicializar componentes
            await self._initialize_components()
            
            # Preparación diaria (análisis de régimen y parámetros)
            await self._daily_preparation()
            
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
        
    async def _daily_preparation(self):
        """
        PREPARACIÓN DIARIA - Ejecutar antes de abrir el grifo de órdenes
        
        1. Descargar histórico reciente
        2. Analizar régimen de mercado
        3. Adaptar parámetros según régimen
        4. Cargar/actualizar modelos ML
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("📋 INICIANDO PREPARACIÓN DIARIA")
            self.logger.info("=" * 60)
            
            # 1. Descargar histórico (últimos 90 días)
            self.logger.info("📥 Descargando histórico reciente...")
            historical_data = await self.market_data.get_historical_data(
                symbol=self.config.SYMBOL,
                days=90,  # 90 días de historia
                timeframe=self.config.TIMEFRAME
            )
            
            if historical_data is None or len(historical_data) < 20:
                self.logger.warning("⚠️ Datos históricos insuficientes, usando configuración por defecto")
                self.daily_prepared = True
                return
            
            self.logger.info(f"✅ Histórico descargado: {len(historical_data)} períodos")
            
            # 2. Analizar régimen de mercado
            self.logger.info("🔍 Analizando régimen de mercado...")
            self.current_regime_info = await self.regime_classifier.analyze_daily_regime(
                historical_data, 
                self.config.SYMBOL
            )
            
            regime = self.current_regime_info.get('regime', 'unknown')
            confidence = self.current_regime_info.get('confidence', 0)
            
            self.logger.info(f"✅ Régimen detectado: {regime.upper()} (confianza: {confidence:.2%})")
            
            # 3. Adaptar parámetros según régimen
            self.logger.info("🔧 Adaptando parámetros al régimen...")
            self.current_parameters = self.param_manager.adapt_parameters(self.current_regime_info)
            self.strategy.update_parameters_for_regime(self.current_regime_info)
            
            # Log de parámetros clave
            self.logger.info(f"   ├─ Estilo de trading: {self.current_parameters.get('trading_style', 'balanced')}")
            self.logger.info(f"   ├─ Stop Loss: {self.current_parameters.get('stop_loss_pct', 0.01):.2%}")
            self.logger.info(f"   ├─ Take Profit: {self.current_parameters.get('take_profit_ratio', 2.0):.1f}R")
            self.logger.info(f"   ├─ Riesgo por trade: {self.current_parameters.get('risk_per_trade', 0.02):.2%}")
            self.logger.info(f"   ├─ Fuerza mínima: {self.current_parameters.get('min_signal_strength', 0.15):.2%}")
            self.logger.info(f"   └─ Max trades diarios: {self.current_parameters.get('max_daily_trades', 5)}")
            
            # 4. Verificar modelo ML
            if self.ml_filter and self.ml_filter.is_model_available():
                self.logger.info("✅ Modelo ML cargado y disponible")
                model_info = self.ml_filter.get_model_info()
                self.logger.info(f"   └─ Probabilidad mínima: {model_info['min_probability']:.2%}")
            elif self.config.ENABLE_ML:
                self.logger.warning("⚠️ ML habilitado pero modelo no disponible")
            
            # 5. Marcar como preparado
            self.daily_prepared = True
            self.last_preparation_date = datetime.now().date()
            
            self.logger.info("=" * 60)
            self.logger.info("✅ PREPARACIÓN DIARIA COMPLETADA")
            self.logger.info("🟢 Sistema listo para operar")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"❌ Error en preparación diaria: {e}")
            # Continuar con configuración por defecto
            self.daily_prepared = True

    async def _check_daily_preparation(self) -> bool:
        """
        Verifica si necesitamos re-preparar (nuevo día)
        Retorna True si está preparado, False si necesita preparación
        """
        today = datetime.now().date()
        
        # Si es un nuevo día, necesitamos re-preparar
        if self.last_preparation_date != today:
            self.logger.info("🌅 Nuevo día detectado, ejecutando preparación diaria...")
            await self._daily_preparation()
        
        return self.daily_prepared

    async def _main_loop(self):
        """Bucle principal del bot CON preparación diaria automática"""
        self.logger.info("🔄 Iniciando bucle principal de trading...")
        
        while self.is_running:
            try:
                # Verificar preparación diaria (re-preparar si es nuevo día)
                if not await self._check_daily_preparation():
                    await asyncio.sleep(60)
                    continue
                
                # Verificar si es horario de trading
                if not self._is_trading_time():
                    await asyncio.sleep(60)  # Esperar 1 minuto
                    continue
                
                # Verificar límites diarios
                max_daily_trades = self.current_parameters.get('max_daily_trades', 5) if self.current_parameters else 5
                
                if not self.risk_manager.check_daily_limits(self.daily_pnl, self.daily_trades):
                    self.logger.warning(f"⚠️ Límites diarios alcanzados (PnL o pérdida)")
                    await asyncio.sleep(300)
                    continue
                
                if self.daily_trades >= max_daily_trades:
                    self.logger.warning(f"⚠️ Máximo de trades diarios alcanzado ({self.daily_trades}/{max_daily_trades})")
                    await asyncio.sleep(300)
                    continue
                
                # Obtener datos de mercado
                market_data = await self.market_data.get_latest_data()
                if not market_data:
                    await asyncio.sleep(10)
                    continue
                
                # Generar señal de trading (con régimen)
                signal = await self.strategy.generate_signal(market_data, self.current_regime_info)
                self.current_signal = signal  # Guardar señal actual para el dashboard
                
                if signal:
                    # FILTRO ML: Verificar con modelo si la señal es buena
                    ml_decision = None
                    if self.ml_filter and self.ml_filter.is_model_available():
                        bot_state = {
                            'daily_pnl': self.daily_pnl,
                            'daily_trades': self.daily_trades,
                            'consecutive_signals': self.strategy.consecutive_signals,
                            'daily_pnl_normalized': self.daily_pnl / self.config.INITIAL_CAPITAL
                        }
                        
                        ml_decision = await self.ml_filter.filter_signal(
                            signal, 
                            market_data, 
                            self.current_regime_info,
                            bot_state
                        )
                        
                        # Si ML rechaza la señal, no operar
                        if not ml_decision['approved']:
                            self.logger.info(f"🚫 Señal rechazada por filtro ML: {ml_decision['reason']}")
                            signal = None
                    
                    if signal:
                        # Verificar riesgo de la operación
                        if self.risk_manager.validate_trade(signal, self.current_positions):
                            # Ejecutar orden
                            order_result = await self.order_executor.execute_order(signal)
                            
                            if order_result['success']:
                                position = order_result['position']
                                self.current_positions.append(position)
                                self.daily_trades += 1
                                
                                self.logger.info(
                                    f"✅ {signal['action']} {signal['symbol']} @ {signal['price']} "
                                    f"(Fuerza: {signal['strength']:.2%}, Régimen: {signal.get('regime', 'unknown')})"
                                )
                                
                                # Guardar contexto para el trade recorder
                                if self.trade_recorder:
                                    self.position_market_data[position['id']] = {
                                        'market_data': market_data.copy(),
                                        'regime_info': self.current_regime_info.copy() if self.current_regime_info else {},
                                        'ml_decision': ml_decision,
                                        'bot_state': {
                                            'daily_pnl': self.daily_pnl,
                                            'daily_trades': self.daily_trades,
                                            'consecutive_signals': self.strategy.consecutive_signals,
                                        }
                                    }
                                
                                await self.notifications.send_trade_notification(order_result)
                            else:
                                self.logger.error(f"❌ Error ejecutando orden: {order_result['error']}")
                        
                # Verificar y gestionar posiciones abiertas (con trailing stop, break-even, etc.)
                await self._check_open_positions(market_data)
                
                # Actualizar dashboard
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
        """
        Verificar y gestionar posiciones abiertas con lógica AVANZADA:
        - Trailing stop
        - Break-even
        - Time-based stops
        - Cierre por fin de día
        """
        current_price = market_data.get('price', 0)
        
        for position in self.current_positions[:]:
            try:
                position_id = position.get('id', 'unknown')
                
                # 1. Gestión avanzada de posición
                management_decision = await self.position_manager.manage_position(
                    position, 
                    current_price, 
                    market_data
                )
                
                # 2. Actualizar stops si es necesario
                if management_decision.get('action') == 'update_stops':
                    new_stop_loss = management_decision.get('new_stop_loss')
                    if new_stop_loss:
                        position['stop_loss'] = new_stop_loss
                        self.logger.info(
                            f"🔄 Stop actualizado en {position.get('symbol')}: "
                            f"Nuevo SL={new_stop_loss:.2f} - {management_decision.get('reason')}"
                        )
                
                # 3. Cerrar posición si es necesario
                should_close = management_decision.get('should_close', False)
                
                # También verificar con risk_manager (stop loss/take profit básico)
                if not should_close:
                    should_close = self.risk_manager.should_close_position(position, market_data)
                
                if should_close:
                    # Cerrar posición
                    close_result = await self.order_executor.close_position(position)
                    
                    if close_result['success']:
                        self.current_positions.remove(position)
                        self.daily_pnl += close_result['pnl']
                        
                        # Determinar tipo de salida
                        exit_type = 'unknown'
                        if 'trailing' in management_decision.get('reason', '').lower():
                            exit_type = 'trailing_stop'
                        elif 'break-even' in management_decision.get('reason', '').lower() or 'breakeven' in management_decision.get('reason', '').lower():
                            exit_type = 'break_even'
                        elif 'time' in management_decision.get('reason', '').lower() or 'tiempo' in management_decision.get('reason', '').lower():
                            exit_type = 'time_stop'
                        elif 'stop loss' in management_decision.get('reason', '').lower():
                            exit_type = 'stop_loss'
                        elif 'take profit' in management_decision.get('reason', '').lower():
                            exit_type = 'take_profit'
                        
                        self.logger.info(
                            f"✅ Posición cerrada: {position.get('symbol')} - "
                            f"PnL={close_result['pnl']:.2f} - "
                            f"Tipo: {exit_type} - "
                            f"Razón: {management_decision.get('reason', 'Stop/TP alcanzado')}"
                        )
                        
                        # Registrar trade completo para ML
                        if self.trade_recorder and position_id in self.position_market_data:
                            context = self.position_market_data.pop(position_id)
                            
                            entry_data = {
                                'entry_time': position.get('entry_time', datetime.now()),
                                'symbol': position.get('symbol'),
                                'action': position.get('side'),
                                'entry_price': position.get('entry_price'),
                                'size': position.get('size'),
                                'stop_loss': position.get('stop_loss'),
                                'take_profit': position.get('take_profit'),
                                'strength': self.current_signal.get('strength') if self.current_signal else 0,
                                'volume_relative': context.get('market_data', {}).get('volume', 0) / max(1, market_data.get('volume', 1)),
                            }
                            
                            exit_data = {
                                'exit_time': datetime.now(),
                                'exit_price': close_result.get('exit_price', current_price),
                                'pnl': close_result['pnl'],
                                'exit_type': exit_type,
                            }
                            
                            # Obtener estadísticas de la posición (MFE, MAE)
                            position_stats = self.position_manager.get_position_stats(position_id)
                            
                            # Registrar con TODO el contexto
                            self.trade_recorder.record_trade(
                                entry_data=entry_data,
                                exit_data=exit_data,
                                market_data_entry=context.get('market_data', {}),
                                market_data_exit=market_data,
                                regime_info=context.get('regime_info'),
                                bot_state=context.get('bot_state'),
                                ml_decision=context.get('ml_decision'),
                                position_stats=position_stats
                            )
                        
                        # Limpiar tracking del position manager
                        self.position_manager.cleanup_position(position_id)
                        
                        await self.notifications.send_position_closed_notification(close_result)
                    else:
                        self.logger.error(f"❌ Error cerrando posición: {close_result['error']}")
                        
            except Exception as e:
                self.logger.error(f"❌ Error gestionando posición {position.get('id')}: {e}")
                    
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
