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
        self.dashboard = Dashboard(
            self.config) if self.config.ENABLE_DASHBOARD else None
        self.notifications = NotificationManager(self.config)

        # Componentes avanzados
        self.regime_classifier = MarketRegimeClassifier(self.config)
        self.param_manager = DynamicParameterManager(self.config)
        self.position_manager = AdvancedPositionManager(self.config)

        # ML components
        self.trade_recorder = TradeRecorder() if self.config.ENABLE_ML else None

        self.ml_filter = MLSignalFilter(
            self.config) if self.config.ENABLE_ML else None

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

        # Modo MVP (Minimum Viable Product)
        self.mvp_mode = False
        self.total_trades_count = 0

        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    async def start(self):
        """Iniciar el bot de trading"""
        try:
            self.logger.info("🚀 Iniciando Bot de Day Trading Avanzado...")
            self.logger.info("=" * 60)

            # Verificar modo DEBUG
            if self.config.ENABLE_DEBUG_STRATEGY:
                self.logger.warning("=" * 60)
                self.logger.warning("🐛 MODO DEBUG ACTIVADO")
                self.logger.warning("=" * 60)
                self.logger.warning(
                    "⚠️  Los siguientes filtros están DESHABILITADOS:")
                self.logger.warning(
                    "   - Filtro ML (se evalúa pero no rechaza)")
                self.logger.warning(
                    "   - Validación de riesgo (se evalúa pero no rechaza)")
                self.logger.warning(
                    "   - Filtros de volatilidad/volumen/fuerza")
                self.logger.warning(
                    "⚠️  El bot ejecutará trades siempre que haya señal básica")
                self.logger.warning("=" * 60)

            # Verificar configuración
            if not self._validate_config():
                self.logger.error("❌ Configuración inválida. Abortando...")
                return

            # Inicializar componentes
            await self._initialize_components()

            # Verificar modo MVP (antes de preparación diaria)
            await self._check_mvp_mode()

            # Preparación diaria (análisis de régimen y parámetros) - Solo si no es MVP
            if not self.mvp_mode:
                await self._daily_preparation()
            else:
                self.logger.info(
                    "🚀 MODO MVP: Saltando preparación diaria avanzada")
                # Usar parámetros básicos
                self.current_parameters = {
                    'max_daily_trades': 20,  # Mucho más permisivo en MVP
                    'stop_loss_pct': self.config.STOP_LOSS_PCT,
                    'take_profit_ratio': self.config.TAKE_PROFIT_RATIO,
                    'risk_per_trade': self.config.RISK_PER_TRADE,
                }

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
                self.logger.warning(
                    "⚠️ Datos históricos insuficientes, usando configuración por defecto")
                self.daily_prepared = True
                return

            self.logger.info(
                f"✅ Histórico descargado: {len(historical_data)} períodos")

            # 2. Analizar régimen de mercado
            self.logger.info("🔍 Analizando régimen de mercado...")
            self.current_regime_info = await self.regime_classifier.analyze_daily_regime(
                historical_data,
                self.config.SYMBOL
            )

            regime = self.current_regime_info.get('regime', 'unknown')
            confidence = self.current_regime_info.get('confidence', 0)

            self.logger.info(
                f"✅ Régimen detectado: {regime.upper()} (confianza: {confidence:.2%})")

            # 3. Adaptar parámetros según régimen
            self.logger.info("🔧 Adaptando parámetros al régimen...")
            self.current_parameters = self.param_manager.adapt_parameters(
                self.current_regime_info)
            self.strategy.update_parameters_for_regime(
                self.current_regime_info)

            # Log de parámetros clave
            self.logger.info(
                f"   ├─ Estilo de trading: {self.current_parameters.get('trading_style', 'balanced')}")
            self.logger.info(
                f"   ├─ Stop Loss: {self.current_parameters.get('stop_loss_pct', 0.01):.2%}")
            self.logger.info(
                f"   ├─ Take Profit: {self.current_parameters.get('take_profit_ratio', 2.0):.1f}R")
            self.logger.info(
                f"   ├─ Riesgo por trade: {self.current_parameters.get('risk_per_trade', 0.02):.2%}")
            self.logger.info(
                f"   ├─ Fuerza mínima: {self.current_parameters.get('min_signal_strength', 0.15):.2%}")
            self.logger.info(
                f"   └─ Max trades diarios: {self.current_parameters.get('max_daily_trades', 5)}")

            # 4. Verificar modelo ML
            if self.ml_filter and self.ml_filter.is_model_available():
                self.logger.info("✅ Modelo ML cargado y disponible")
                model_info = self.ml_filter.get_model_info()
                self.logger.info(
                    f"   └─ Probabilidad mínima: {model_info['min_probability']:.2%}")
            elif self.config.ENABLE_ML:
                self.logger.warning(
                    "⚠️ ML habilitado pero modelo no disponible")

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

    async def _check_mvp_mode(self):
        """
        Verifica si debe activarse el modo MVP
        MVP se activa automáticamente si hay < 500 trades históricos
        """
        try:
            if not self.config.MVP_MODE_ENABLED:
                self.mvp_mode = False
                return

            # Contar trades históricos
            if self.trade_recorder:
                try:
                    df = self.trade_recorder.get_training_data()
                    self.total_trades_count = len(
                        df) if df is not None and not df.empty else 0
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ No se pudo contar trades históricos: {e}")
                    self.total_trades_count = 0

            # Activar MVP si hay menos de 500 trades
            if self.total_trades_count < self.config.MVP_MIN_TRADES_FOR_ADVANCED_FEATURES:
                self.mvp_mode = True
                self.logger.warning("=" * 60)
                self.logger.warning("🚀 MODO MVP ACTIVADO")
                self.logger.warning("=" * 60)
                self.logger.warning(
                    f"📊 Trades históricos: {self.total_trades_count} / {self.config.MVP_MIN_TRADES_FOR_ADVANCED_FEATURES}")
                self.logger.warning("")
                self.logger.warning(
                    "✅ FEATURES ACTIVADAS (prioridad: sample size):")
                self.logger.warning(
                    "   - Señales técnicas básicas (EMA + RSI)")
                self.logger.warning("   - Logging completo para ML")
                self.logger.warning("   - Gestión de riesgo básica")
                self.logger.warning(
                    "   - Límites de trades aumentados (20/día)")
                self.logger.warning("")
                self.logger.warning(
                    "❌ FEATURES DESACTIVADAS (hasta 500 trades):")
                self.logger.warning(
                    "   - Filtro ML (no hay suficientes datos)")
                self.logger.warning("   - Análisis de régimen de mercado")
                self.logger.warning("   - Parámetros dinámicos avanzados")
                self.logger.warning("   - Validaciones de riesgo estrictas")
                self.logger.warning(
                    "   - Filtros de volatilidad/volumen restrictivos")
                self.logger.warning("")
                self.logger.warning(
                    "🎯 OBJETIVO: Acumular 500+ trades para entrenar ML")
                self.logger.warning("=" * 60)
            else:
                self.mvp_mode = False
                self.logger.info(
                    f"✅ Modo avanzado activado ({self.total_trades_count} trades históricos)")

        except Exception as e:
            self.logger.error(f"❌ Error verificando modo MVP: {e}")
            # En caso de error, activar MVP por seguridad
            self.mvp_mode = True

    async def _check_daily_preparation(self) -> bool:
        """
        Verifica si necesitamos re-preparar (nuevo día)
        Retorna True si está preparado, False si necesita preparación
        """
        today = datetime.now().date()

        # Si es un nuevo día, necesitamos re-preparar
        if self.last_preparation_date != today:
            self.logger.info(
                "🌅 Nuevo día detectado, ejecutando preparación diaria...")
            await self._daily_preparation()

        return self.daily_prepared

    async def _main_loop(self):
        """Bucle principal del bot CON preparación diaria automática"""
        self.logger.info("🔄 Iniciando bucle principal de trading...")

        iteration_count = 0
        last_status_log = datetime.now()

        while self.is_running:
            try:
                iteration_count += 1
                current_time = datetime.now()

                # Log de estado cada 30 segundos para confirmar que está vivo
                if (current_time - last_status_log).total_seconds() >= 30:
                    self.logger.info(
                        f"💓 Bot activo | Iteración #{iteration_count} | "
                        f"PnL: {self.daily_pnl:.2f} | Trades: {self.daily_trades} | "
                        f"Posiciones: {len(self.current_positions)}"
                    )
                    last_status_log = current_time

                # Verificar preparación diaria (re-preparar si es nuevo día)
                if not await self._check_daily_preparation():
                    await asyncio.sleep(60)
                    continue

                # Verificar si es horario de trading
                if not self._is_trading_time():
                    await asyncio.sleep(60)  # Esperar 1 minuto
                    continue

                if self.mvp_mode:
                    # ✅ En MVP también queremos un límite diario razonable, pero alto
                    max_daily_trades = self.config.MAX_DAILY_TRADES

                    max_loss = self.config.INITIAL_CAPITAL * self.config.MAX_DAILY_LOSS
                    if self.daily_pnl < -max_loss:
                        self.logger.warning(
                            f"⚠️ Límite de pérdida diaria alcanzado (MVP): {self.daily_pnl:.2f}")
                        await asyncio.sleep(300)
                        continue
                else:
                    # En modo avanzado: respetar lo que diga el régimen,
                    # pero nunca pasar el techo global de config
                    if self.current_parameters:
                        max_daily_trades = min(
                            self.current_parameters.get('max_daily_trades', self.config.MAX_DAILY_TRADES),
                            self.config.MAX_DAILY_TRADES
                        )
                    else:
                        max_daily_trades = self.config.MAX_DAILY_TRADES

                    if not self.risk_manager.check_daily_limits(self.daily_pnl, self.daily_trades):
                        self.logger.warning(
                            f"⚠️ Límites diarios alcanzados (PnL: {self.daily_pnl:.2f} o trades: {self.daily_trades})")
                        await asyncio.sleep(300)
                        continue

                if self.daily_trades >= max_daily_trades:
                    if not self.mvp_mode:
                        self.logger.warning(
                            f"⚠️ Máximo de trades diarios alcanzado ({self.daily_trades}/{max_daily_trades})")
                    await asyncio.sleep(300)
                    continue

                # Obtener datos de mercado
                market_data = await self.market_data.get_latest_data()
                if not market_data:
                    self.logger.warning(
                        "⚠️ No se pudieron obtener datos de mercado, reintentando en 10s...")
                    await asyncio.sleep(10)
                    continue

                price = market_data.get('price', 0)
                symbol = market_data.get('symbol', 'N/A')

                # Generar señal de trading (con régimen)
                signal = await self.strategy.generate_signal(market_data, self.current_regime_info)
                self.current_signal = signal  # Guardar señal actual para el dashboard

                if signal:
                    self.logger.info(
                        f"🔔 Señal generada: {signal['action']} {symbol} @ {signal['price']:.2f} (Fuerza: {signal['strength']:.2%})")
                else:
                    # Log cada 10 iteraciones para no saturar
                    if iteration_count % 10 == 0:
                        indicators = market_data.get('indicators', {})
                        self.logger.info(
                            f"🔍 Analizando {symbol} @ {price:.2f} | "
                            f"RSI: {indicators.get('rsi', 0):.1f} | "
                            f"EMA9: {indicators.get('fast_ma', 0):.2f} | "
                            f"EMA21: {indicators.get('slow_ma', 0):.2f} | "
                            f"Sin señal (condiciones no cumplidas)"
                        )

                if signal:
                    # CRÍTICO: Aplicar sizing y protección ANTES de cualquier validación
                    atr = market_data.get('indicators', {}).get('atr')
                    signal = self.risk_manager.size_and_protect(
                        signal, atr=atr)
                    self.logger.info(
                        f"📏 Señal procesada por size_and_protect: "
                        f"Size={signal.get('position_size', 0):.6f}, "
                        f"SL={signal.get('stop_loss', 0):.2f}, "
                        f"TP={signal.get('take_profit', 0):.2f}"
                    )

                    is_debug = self.config.ENABLE_DEBUG_STRATEGY

                    # FILTRO ML: Solo usar si NO es modo MVP y NO es debug
                    ml_decision = None
                    use_ml_filter = not self.mvp_mode and not is_debug and self.ml_filter and self.ml_filter.is_model_available()

                    if use_ml_filter:
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
                            self.logger.info(
                                f"🚫 Señal rechazada por filtro ML: {ml_decision['reason']} (P(win)={ml_decision.get('probability', 0):.2%})")
                            signal = None
                    elif is_debug and self.ml_filter and self.ml_filter.is_model_available():
                        # En modo debug, evaluar ML pero no rechazar
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

                        if not ml_decision['approved']:
                            self.logger.warning(
                                f"🐛 [DEBUG] ⚠️ ML rechazaría la señal: {ml_decision['reason']} "
                                f"(P(win)={ml_decision.get('probability', 0):.2%}), pero DEBUG permite continuar"
                            )
                        else:
                            self.logger.info(
                                f"🐛 [DEBUG] ✅ ML aprobaría la señal: {ml_decision['reason']} "
                                f"(P(win)={ml_decision.get('probability', 0):.2%})"
                            )
                    elif is_debug:
                        self.logger.info(
                            "🐛 [DEBUG] ML no disponible o deshabilitado - saltando filtro ML")

                    if signal:
                        # Verificar riesgo de la operación (simplificado en MVP)
                        if self.mvp_mode:
                            # En MVP: solo verificar límites básicos (pérdida máxima, posiciones máximas)
                            risk_valid = self._validate_trade_mvp(
                                signal, self.current_positions)
                            if not risk_valid:
                                self.logger.warning(
                                    "⚠️ Trade rechazado por límites básicos de MVP")
                        elif is_debug:
                            # En debug: evaluar pero no rechazar
                            risk_valid = self.risk_manager.validate_trade(
                                signal, self.current_positions)
                            if risk_valid:
                                self.logger.info(
                                    "🐛 [DEBUG] ✅ Gestor de riesgo aprobaría la operación")
                            else:
                                self.logger.warning(
                                    f"🐛 [DEBUG] ⚠️ Gestor de riesgo rechazaría la operación, pero DEBUG permite continuar"
                                )
                            risk_valid = True  # Forzar aprobación en debug
                        else:
                            # Modo normal: validación completa
                            risk_valid = self.risk_manager.validate_trade(
                                signal, self.current_positions)

                        # Ejecutar si está validado o en modo MVP/debug
                        if risk_valid:
                            if self.mvp_mode:
                                self.logger.info(
                                    f"🚀 [MVP] Ejecutando orden (prioridad: sample size)")
                            elif is_debug:
                                if not self.risk_manager.validate_trade(signal, self.current_positions):
                                    self.logger.warning(
                                        "🐛 [DEBUG] ⚠️ Ejecutando orden a pesar de validación de riesgo fallida (MODO DEBUG)")
                                self.logger.info(
                                    f"🐛 [DEBUG] ✅ Ejecutando orden (MODO DEBUG - filtros ignorados)")
                            else:
                                self.logger.info(
                                    f"✅ Riesgo validado, ejecutando orden...")

                            # Ejecutar orden
                            order_result = await self.order_executor.execute_order(signal)

                            if order_result['success']:
                                position = order_result['position']
                                self.current_positions.append(position)
                                self.daily_trades += 1

                                if self.mvp_mode:
                                    self.logger.info(
                                        f"🚀 [MVP] ✅ Trade #{self.total_trades_count + self.daily_trades}: "
                                        f"{signal['action']} {signal['symbol']} @ {signal['price']:.2f} "
                                        f"(Size: {signal['position_size']:.4f}, SL: {signal['stop_loss']:.2f}, TP: {signal['take_profit']:.2f})"
                                    )
                                elif is_debug:
                                    self.logger.info(
                                        f"🐛 [DEBUG] ✅ ORDEN EJECUTADA: {signal['action']} {signal['symbol']} @ {signal['price']:.2f} "
                                        f"(Size: {signal['position_size']:.4f}, SL: {signal['stop_loss']:.2f}, TP: {signal['take_profit']:.2f})"
                                    )
                                else:
                                    self.logger.info(
                                        f"✅ {signal['action']} {signal['symbol']} @ {signal['price']} "
                                        f"(Fuerza: {signal['strength']:.2%}, Régimen: {signal.get('regime', 'unknown')})"
                                    )

                                # Guardar contexto para el trade recorder (SIEMPRE en MVP para generar datos ML)
                                if self.trade_recorder or self.mvp_mode:
                                    # En MVP, crear trade_recorder si no existe para logging
                                    if not self.trade_recorder and self.config.ENABLE_ML:
                                        from src.ml.trade_recorder import TradeRecorder
                                        self.trade_recorder = TradeRecorder(
                                            config=self.config)

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
                                self.logger.error(
                                    f"❌ Error ejecutando orden: {order_result['error']}")
                        else:
                            self.logger.info(
                                f"🚫 Operación rechazada por gestor de riesgo (exposición máxima o límites alcanzados)")

                # Verificar y gestionar posiciones abiertas (con trailing stop, break-even, etc.)
                await self._check_open_positions(market_data)

                # Actualizar dashboard
                if self.dashboard:
                    try:
                        dashboard_payload = self._build_dashboard_payload(
                            market_data)
                        await self.dashboard.update_data(dashboard_payload)
                    except Exception as e:
                        self.logger.error(
                            f"❌ Error actualizando dashboard: {e}")

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
                symbol = position.get('symbol', 'UNKNOWN')

                # TIME STOP OBLIGATORIO: Verificar si pasaron 30 segundos
                entry_time = position.get(
                    'entry_time') or position.get('open_time')
                if entry_time:
                    # Convertir string a datetime si es necesario
                    if isinstance(entry_time, str):
                        try:
                            entry_time = datetime.fromisoformat(
                                entry_time.replace('Z', '+00:00'))
                        except:
                            try:
                                entry_time = datetime.fromisoformat(entry_time)
                            except:
                                entry_time = datetime.now()

                    time_diff = datetime.now() - entry_time
                    time_seconds = time_diff.total_seconds()

                    # FORCE CLOSE: Cerrar cualquier posición abierta más de 30 segundos
                    if time_seconds >= 30:
                        self.logger.info(
                            f"⏰ FORCE TIME CLOSE -> {position_id}, {symbol}, tiempo: {time_seconds:.1f}s"
                        )

                        # Cerrar posición a precio de mercado
                        close_result = await self.order_executor.close_position(position)

                        if close_result.get('success'):
                            # Calcular PnL
                            pnl = close_result.get('pnl', 0.0)

                            # Registrar trade en RiskManager
                            self.risk_manager.register_trade({
                                'symbol': symbol,
                                'action': position.get('side', 'UNKNOWN'),
                                'price': close_result.get('exit_price', current_price),
                                'position_size': position.get('size', 0),
                                'pnl': pnl,
                                'reason': 'Force time close (30s)'
                            })

                            # Remover de current_positions
                            if position in self.current_positions:
                                self.current_positions.remove(position)

                            # Remover de executor.positions
                            if position in self.order_executor.positions:
                                self.order_executor.positions.remove(position)

                            # Actualizar PnL diario
                            self.daily_pnl += pnl

                            self.logger.info(
                                f"⏰ FORCE TIME CLOSE -> {position_id}, {symbol}, PnL: {pnl:.2f}"
                            )

                            # Continuar con siguiente posición (esta ya está cerrada)
                            continue
                        else:
                            self.logger.error(
                                f"❌ Error en force time close de {position_id}: {close_result.get('error', 'Unknown')}"
                            )

                # 1. Gestión avanzada de posición (pasar mvp_mode, executor, risk_manager y lista)
                management_decision = await self.position_manager.manage_position(
                    position,
                    current_price,
                    market_data,
                    mvp_mode=self.mvp_mode,
                    executor=self.order_executor,
                    risk_manager=self.risk_manager,
                    positions_list=self.current_positions
                )

                # Si AdvancedPositionManager cerró realmente la posición, actualizar PnL y continuar
                if management_decision.get('closed', False):
                    pnl = management_decision.get('pnl', 0.0)
                    # También remover de executor.positions si está ahí
                    if position in self.order_executor.positions:
                        self.order_executor.positions.remove(position)
                    continue

                # 2. Actualizar stops si es necesario (solo si NO es MVP)
                if not self.mvp_mode and management_decision.get('action') == 'update_stops':
                    new_stop_loss = management_decision.get('new_stop_loss')
                    if new_stop_loss:
                        position['stop_loss'] = new_stop_loss
                        self.logger.info(
                            f"🔄 Stop actualizado en {symbol}: "
                            f"Nuevo SL={new_stop_loss:.2f} - {management_decision.get('reason')}"
                        )

                # 3. SIEMPRE verificar con risk_manager (stop loss/take profit básico)
                # Esto asegura que SL/TP se evalúen en cada iteración
                should_close_risk = self.risk_manager.should_close_position(
                    position, market_data)
                should_close = management_decision.get(
                    'should_close', False) or should_close_risk

                if should_close_risk and not management_decision.get('should_close', False):
                    self.logger.info(
                        f"🛑 [{symbol}] RiskManager detectó condición de cierre (SL/TP/Time)"
                    )

                if should_close:
                    # Log antes de cerrar
                    self.logger.info(
                        f"🔒 [{symbol}] Cerrando posición {position_id} | "
                        f"Razón: {management_decision.get('reason', 'SL/TP/Time alcanzado')}"
                    )

                    # Cerrar posición
                    close_result = await self.order_executor.close_position(position)

                    if close_result['success']:
                        self.current_positions.remove(position)
                        self.daily_pnl += close_result['pnl']

                        self.logger.info(
                            f"✅ [{symbol}] Posición {position_id} cerrada exitosamente | "
                            f"PnL: {close_result['pnl']:.2f}"
                        )

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

                        # Registrar trade completo para ML (SIEMPRE en MVP)
                        should_record = (
                            self.trade_recorder or self.mvp_mode) and position_id in self.position_market_data
                        if should_record:
                            # Asegurar que trade_recorder existe en MVP
                            if not self.trade_recorder and self.config.ENABLE_ML:
                                from src.ml.trade_recorder import TradeRecorder
                                self.trade_recorder = TradeRecorder(
                                    config=self.config)

                            if self.trade_recorder:
                                context = self.position_market_data.pop(
                                    position_id)

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
                                position_stats = self.position_manager.get_position_stats(
                                    position_id)

                                # Registrar con TODO el contexto (crítico para ML)
                                self.trade_recorder.record_trade(
                                    entry_data=entry_data,
                                    exit_data=exit_data,
                                    market_data_entry=context.get(
                                        'market_data', {}),
                                    market_data_exit=market_data,
                                    regime_info=context.get(
                                        'regime_info') if not self.mvp_mode else {},
                                    bot_state=context.get('bot_state'),
                                    ml_decision=context.get('ml_decision'),
                                    position_stats=position_stats
                                )

                                # Actualizar contador de trades en MVP
                                if self.mvp_mode:
                                    try:
                                        df = self.trade_recorder.get_training_data()
                                        self.total_trades_count = len(
                                            df) if df is not None and not df.empty else 0
                                        remaining = self.config.MVP_MIN_TRADES_FOR_ADVANCED_FEATURES - self.total_trades_count
                                        if remaining > 0:
                                            self.logger.info(
                                                f"📊 [MVP] Progreso: {self.total_trades_count}/{self.config.MVP_MIN_TRADES_FOR_ADVANCED_FEATURES} trades ({remaining} restantes)")
                                        else:
                                            self.logger.warning(
                                                "🎉 [MVP] ¡500 trades alcanzados! El bot cambiará a modo avanzado en el próximo reinicio")
                                    except Exception as e:
                                        self.logger.warning(
                                            f"⚠️ No se pudo actualizar contador MVP: {e}")

                        # Limpiar tracking del position manager
                        self.position_manager.cleanup_position(position_id)

                        await self.notifications.send_position_closed_notification(close_result)
                    else:
                        self.logger.error(
                            f"❌ Error cerrando posición: {close_result['error']}")

            except Exception as e:
                self.logger.error(
                    f"❌ Error gestionando posición {position.get('id')}: {e}")

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
                (self._safe_float(p.get('size')) or 0.0) *
                (self._safe_float(p.get('entry_price')) or 0.0)
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
                # Precio actual como close
                'close': self._safe_float(market_data.get('price')),
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
                self.logger.error(
                    "❌ Riesgo por trade debe estar entre 0 y 0.1 (10%)")
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

    def _validate_trade_mvp(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """
        Validación simplificada de riesgo para modo MVP
        Solo verifica que no estemos TOTALMENTE fuera de control.
        """
        try:
            # 1) Límite de pérdida diaria (mantenerlo)
            max_loss = self.config.INITIAL_CAPITAL * self.config.MAX_DAILY_LOSS
            if self.daily_pnl < -max_loss:
                self.logger.warning(
                    "⚠️ [MVP] Límite de pérdida diaria alcanzado")
                return False

            # 2) Subir bastante el límite de posiciones simultáneas
            # antes 3, ahora mínimo 10
            max_positions_mvp = max(self.config.MAX_POSITIONS, 15)
            if len(current_positions) >= max_positions_mvp:
                self.logger.warning(
                    f"⚠️ [MVP] Máximo de posiciones simultáneas alcanzado: "
                    f"{len(current_positions)}/{max_positions_mvp}"
                )
                return False

            # 3) Aflojar exposición a algo grande o directamente desactivarlo
            total_exposure = sum(
                (p.get('size', 0) * p.get('entry_price', 0))
                for p in current_positions
            )
            new_exposure = signal.get(
                'position_size', 0) * signal.get('price', 0)
            max_exposure = self.config.INITIAL_CAPITAL * 0.8  # 80% en MVP
            if total_exposure + new_exposure > max_exposure:
                self.logger.warning(
                    f"⚠️ [MVP] Exposición máxima superada: "
                    f"{total_exposure + new_exposure:.2f} / {max_exposure:.2f}"
                )
                # Si querés ser ultra permisivo, podés comentar este return:
                # return False

            return True
        except Exception as e:
            self.logger.error(f"❌ Error en validación MVP: {e}")
            return False

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
