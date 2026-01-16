"""
Bot de Day Trading Automatizado AVANZADO
Archivo principal que orquesta todos los componentes del sistema con:
- Preparación diaria (análisis de régimen)
- Parámetros dinámicos
- Filtro ML
- Gestión avanzada de posiciones
"""
# pylint: disable=logging-fstring-interpolation,broad-except,redefined-outer-name,reimported,bare-except

import asyncio
import signal
from datetime import datetime
from typing import Dict, List, Optional, Any

from config import Config
from src.data.market_data import MarketDataProvider
from src.strategy.strategy_factory import StrategyFactory
from src.strategy.decision_sampler import DecisionSampler
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
from src.state.state_manager import StateManager


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
        # Usar StrategyFactory para elegir estrategia según modo (PAPER → LearningStrategy, LIVE → TradingStrategy)
        self.strategy = StrategyFactory.create_strategy(self.config)
        self.risk_manager = RiskManager(self.config)

        # Gestor de persistencia de estado
        self.state_manager = StateManager("state.json")

        # Restaurar estado persistido (si existe)
        persisted_state = self.state_manager.load()
        today = datetime.now().date()

        if persisted_state:
            # Verificar si es un nuevo día - resetear contadores diarios
            last_saved_at = persisted_state.get("last_saved_at")
            if last_saved_at:
                try:
                    if isinstance(last_saved_at, str):
                        last_date = datetime.fromisoformat(
                            last_saved_at.replace('Z', '+00:00')).date()
                    else:
                        last_date = last_saved_at.date() if hasattr(last_saved_at, 'date') else today

                    # Si es un nuevo día, resetear métricas diarias
                    if last_date < today:
                        self.logger.info(
                            f"🌅 Nuevo día detectado ({last_date} -> {today}). Reseteando métricas diarias.")
                        self.risk_manager.reset_daily_metrics()
                    else:
                        # Mismo día: restaurar estado
                        self.risk_manager.state.daily_pnl = persisted_state.get(
                            "daily_pnl", 0.0
                        )
                        self.risk_manager.state.trades_today = persisted_state.get(
                            "trades_today", 0
                        )
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Error verificando fecha del estado: {e}. Reseteando métricas diarias.")
                    self.risk_manager.reset_daily_metrics()
            else:
                # No hay fecha guardada, resetear por seguridad
                self.risk_manager.reset_daily_metrics()

            self.risk_manager.state.equity = persisted_state.get(
                "equity", self.risk_manager.state.equity
            )
            self.risk_manager.state.peak_equity = persisted_state.get(
                "peak_equity", self.risk_manager.state.peak_equity
            )
            self.risk_manager.state.max_drawdown = persisted_state.get(
                "max_drawdown", 0.0
            )

            self.logger.info(
                "🔁 Estado restaurado | Equity=%.2f | PnL=%.2f | Trades=%d | Peak=%.2f",
                self.risk_manager.state.equity,
                self.risk_manager.state.daily_pnl,
                self.risk_manager.state.trades_today,
                self.risk_manager.state.peak_equity
            )

        self.order_executor = OrderExecutor(self.config)
        self.dashboard = Dashboard(
            self.config) if self.config.ENABLE_DASHBOARD else None
        self.notifications = NotificationManager(self.config)

        # Componentes avanzados
        self.regime_classifier = MarketRegimeClassifier(self.config)
        self.param_manager = DynamicParameterManager(self.config)
        self.position_manager = AdvancedPositionManager(self.config)

        # Decision Sampling Layer (NUEVO) - Solo en PAPER para recopilación de datos ML
        # Esta capa separa decisiones de ejecución, permitiendo al ML aprender del espacio completo
        self.decision_sampler = DecisionSampler(
            self.config) if self.config.TRADING_MODE == "PAPER" else None
        if self.decision_sampler:
            self.logger.info("📊 Decision Sampling Layer activada (PAPER mode)")

        # ML components - SIEMPRE habilitado en PAPER mode para recopilación de datos
        # En LIVE mode, solo si ENABLE_ML está activado
        ml_enabled = self.config.ENABLE_ML or (
            self.config.TRADING_MODE == "PAPER")
        self.trade_recorder = TradeRecorder() if ml_enabled else None

        self.ml_filter = MLSignalFilter(
            model_path=self.config.ML_MODEL_PATH,
            min_probability=self.config.ML_MIN_PROBABILITY,
        ) if ml_enabled and self.config.ENABLE_ML else None

        # Progress tracker para ML - SIEMPRE en PAPER mode para monitorear recopilación
        if ml_enabled or self.config.TRADING_MODE == "PAPER":
            from src.ml.ml_progress_tracker import MLProgressTracker
            self.ml_progress = MLProgressTracker()
            # Log progreso inicial
            self.ml_progress.log_progress()
        else:
            self.ml_progress = None

        # Estado del bot
        self.is_running = False
        self.current_positions = []
        # ELIMINADO: daily_pnl y daily_trades ahora viven en risk_manager.state (ÚNICA FUENTE DE VERDAD)
        self.current_signal = None  # Señal actual que está analizando
        self.position_market_data = {}  # Guardar datos de mercado al abrir posiciones

        # Cooldown entre trades ejecutados (para alta frecuencia controlada)
        self.last_trade_time = None
        self.min_cooldown_seconds = self.config.MIN_COOLDOWN_BETWEEN_TRADES

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

            # Validación de arquitectura
            self._validate_architecture()

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
                # En modo PAPER (Learning Mode): usar límite alto del config
                # En modo LIVE: usar límite conservador
                max_trades_mvp = self.config.MAX_DAILY_TRADES if self.config.TRADING_MODE == "PAPER" else 20
                self.current_parameters = {
                    'max_daily_trades': max_trades_mvp,
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

    async def _initialize_components(self):
        """Inicializa todos los componentes del bot."""
        try:
            self.logger.info("🔧 Inicializando componentes...")

            # 1. Inicializar market_data (CRÍTICO para obtener datos reales)
            self.logger.info("📊 Inicializando MarketDataProvider...")
            await self.market_data.initialize()
            if self.market_data.exchange:
                self.logger.info(
                    "✅ MarketDataProvider inicializado con conexión a Binance")
            else:
                self.logger.warning(
                    "⚠️ MarketDataProvider sin conexión (modo simulado)")

            # 2. Inicializar order_executor
            self.logger.info("📦 Inicializando OrderExecutor...")
            await self.order_executor.initialize()

            # 3. Inicializar dashboard si está habilitado
            if self.dashboard:
                self.logger.info("🌐 Inicializando Dashboard...")
                await self.dashboard.start()

            self.logger.info(
                "✅ Todos los componentes inicializados correctamente")

        except Exception as e:
            self.logger.exception(f"❌ Error inicializando componentes: {e}")
            raise

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
            trading_style = self.current_parameters.get(
                'trading_style', 'balanced')
            self.logger.info(f"   ├─ Estilo de trading: {trading_style}")

            stop_loss = self.current_parameters.get('stop_loss_pct', 0.01)
            self.logger.info(f"   ├─ Stop Loss: {stop_loss:.2%}")

            tp_ratio = self.current_parameters.get('take_profit_ratio', 2.0)
            self.logger.info(f"   ├─ Take Profit: {tp_ratio:.1f}R")

            risk = self.current_parameters.get('risk_per_trade', 0.02)
            self.logger.info(f"   ├─ Riesgo por trade: {risk:.2%}")

            min_strength = self.current_parameters.get(
                'min_signal_strength', 0.15)
            self.logger.info(f"   ├─ Fuerza mínima: {min_strength:.2%}")

            max_trades = self.current_parameters.get('max_daily_trades', 5)
            self.logger.info(f"   └─ Max trades diarios: {max_trades}")

            # 4. Verificar modelo ML
            if self.ml_filter is not None and self.ml_filter.is_model_available():
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
                min_trades = self.config.MVP_MIN_TRADES_FOR_ADVANCED_FEATURES
                msg = f"📊 Trades históricos: {self.total_trades_count} / {min_trades}"
                self.logger.warning(msg)
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
                        f"PnL: {self.risk_manager.state.daily_pnl:.2f} | Trades: {self.risk_manager.state.trades_today} | "
                        f"Posiciones: {len(self.current_positions)}"
                    )
                    last_status_log = current_time

                    # Actualizar dashboard periódicamente
                    if self.dashboard:
                        dashboard_data = self._build_dashboard_payload(
                            market_data if 'market_data' in locals() else None)
                        await self.dashboard.update_data(dashboard_data)

                # ✅ LEARNING MODE: En modo PAPER no bloquear por límites diarios
                # El RiskManager maneja reducción de riesgo adaptativa
                # En modo LIVE: mantener bloqueos estrictos
                if self.config.TRADING_MODE == "LIVE":
                    if self.risk_manager.state.trades_today >= self.config.MAX_DAILY_TRADES:
                        self.logger.warning(
                            f"⛔ [LIVE] Límite de trades diarios alcanzado: {self.risk_manager.state.trades_today}"
                        )
                        await asyncio.sleep(60)
                        continue

                # Verificar si es horario de trading
                if not self._is_trading_time():
                    await asyncio.sleep(60)  # Esperar 1 minuto
                    continue

                if self.mvp_mode:
                    # ✅ En MVP, el RiskManager maneja los límites de forma adaptativa
                    # En modo PAPER, permite continuar con riesgo reducido (sin bloqueos)
                    # En modo LIVE, bloquea estrictamente
                    max_daily_trades = self.config.MAX_DAILY_TRADES

                    # En modo MVP + PAPER: nunca bloquear, solo informar
                    # En modo MVP + LIVE: verificar límites estrictamente
                    if self.config.TRADING_MODE == "LIVE":
                        if self.risk_manager.state.trades_today >= max_daily_trades:
                            self.logger.warning(
                                f"🚨 [LIVE] Máximo de trades diarios alcanzado ({self.risk_manager.state.trades_today}/{max_daily_trades})")
                            await asyncio.sleep(300)
                            continue
                    # En PAPER (Learning Mode): permitir continuar indefinidamente
                    # Solo log cada 100 trades para no saturar
                    elif self.risk_manager.state.trades_today >= max_daily_trades:
                        if self.risk_manager.state.trades_today % 100 == 0:
                            self.logger.info(
                                f"📚 [PAPER Learning Mode - MVP] {self.risk_manager.state.trades_today} trades acumulados "
                                f"(límite soft: {max_daily_trades}) - Continuando para ML")
                else:
                    # En modo avanzado: respetar lo que diga el régimen,
                    # pero nunca pasar el techo global de config
                    if self.current_parameters:
                        max_daily_trades = min(
                            self.current_parameters.get(
                                'max_daily_trades', self.config.MAX_DAILY_TRADES),
                            self.config.MAX_DAILY_TRADES
                        )
                    else:
                        max_daily_trades = self.config.MAX_DAILY_TRADES

                    # En modo LIVE: verificar límites estrictos
                    # En modo PAPER: siempre permitir (learning mode)
                    if self.config.TRADING_MODE == "LIVE":
                        limits_ok = self.risk_manager.check_daily_limits(
                            daily_pnl=self.risk_manager.state.daily_pnl,
                            daily_trades=self.risk_manager.state.trades_today
                        )
                        if not limits_ok:
                            msg = (f"🚨 [LIVE] Límites diarios alcanzados - Trading bloqueado "
                                   f"(PnL: {self.risk_manager.state.daily_pnl:.2f} o trades: {self.risk_manager.state.trades_today})")
                            self.logger.warning(msg)
                            await asyncio.sleep(300)
                            continue

                        if self.risk_manager.state.trades_today >= max_daily_trades:
                            self.logger.warning(
                                f"🚨 [LIVE] Máximo de trades diarios alcanzado ({self.risk_manager.state.trades_today}/{max_daily_trades})")
                            await asyncio.sleep(300)
                            continue
                    else:
                        # PAPER (Learning Mode): Solo log informativo, nunca bloquear
                        limits_ok = self.risk_manager.check_daily_limits(
                            daily_pnl=self.risk_manager.state.daily_pnl,
                            daily_trades=self.risk_manager.state.trades_today
                        )
                        # En PAPER, check_daily_limits siempre retorna True, pero puede advertir
                        if self.risk_manager.state.trades_today >= max_daily_trades:
                            if self.risk_manager.state.trades_today % 100 == 0:  # Log cada 100 trades
                                self.logger.info(
                                    f"📚 [PAPER Learning Mode] {self.risk_manager.state.trades_today} trades acumulados "
                                    f"(límite soft: {max_daily_trades}) - Continuando para ML")

                # Obtener datos de mercado
                market_data = await self.market_data.get_latest_data()
                if not market_data:
                    msg = "⚠️ No se pudieron obtener datos de mercado, reintentando en 10s..."
                    self.logger.warning(msg)
                    await asyncio.sleep(10)
                    continue

                # Actualizar dashboard con los datos más recientes
                if self.dashboard:
                    try:
                        dashboard_data = self._build_dashboard_payload(
                            market_data)
                        await self.dashboard.update_data(dashboard_data)
                    except Exception as e:
                        self.logger.debug(f"Error actualizando dashboard: {e}")

                price = market_data.get('price', 0)
                symbol = market_data.get('symbol', 'N/A')

                # Generar señal de trading (con régimen)
                signal = await self.strategy.generate_signal(market_data, self.current_regime_info)
                self.current_signal = signal  # Guardar señal actual para el dashboard

                executed_action = None
                decision_sample = None
                decision_type = "hold"

                if signal:
                    self.logger.info(
                        f"🔔 Señal generada: {signal['action']} {symbol} @ {signal['price']:.2f} (Fuerza: {signal['strength']:.2%})")
                else:
                    executed_action = "HOLD"
                    decision_type = "no_signal"

                    if self.decision_sampler and self.trade_recorder and self.config.TRADING_MODE == "PAPER":
                        if not hasattr(self, '_hold_sample_counter'):
                            self._hold_sample_counter = 0
                        self._hold_sample_counter += 1

                        hold_downsample_rate = getattr(
                            self.config, 'HOLD_DOWNSAMPLE_RATE', 10)

                        if self._hold_sample_counter % hold_downsample_rate == 0:
                            decision_sample = self.decision_sampler.create_decision_sample(
                                market_data=market_data,
                                strategy=self.strategy,
                                strategy_signal=None,
                                executed_action=executed_action,
                                regime_info=self.current_regime_info
                            )
                            self.trade_recorder.record_decision_sample(
                                decision_sample, decision_type)

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
                    pos_size = signal.get('position_size', 0)
                    sl = signal.get('stop_loss', 0)
                    tp = signal.get('take_profit', 0)
                    msg = (f"📏 Señal procesada por size_and_protect: "
                           f"Size={pos_size:.6f}, SL={sl:.2f}, TP={tp:.2f}")
                    self.logger.info(msg)

                    is_debug = self.config.ENABLE_DEBUG_STRATEGY

                    # FILTRO ML: Solo usar si NO es modo MVP y NO es debug
                    ml_decision = None
                    use_ml_filter = not self.mvp_mode and not is_debug and self.ml_filter is not None and self.ml_filter.is_model_available()

                    if use_ml_filter:
                        bot_state = {
                            'daily_pnl': self.risk_manager.state.daily_pnl,
                            'daily_trades': self.risk_manager.state.trades_today,
                            'consecutive_signals': self.strategy.consecutive_signals,
                            'daily_pnl_normalized': self.risk_manager.state.daily_pnl / self.config.INITIAL_CAPITAL
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

                            # Actualizar executed_action = HOLD (rechazada por ML)
                            executed_action = "HOLD"
                            decision_type = "rejected_ml"

                            if self.decision_sampler and self.trade_recorder and self.config.TRADING_MODE == "PAPER":
                                decision_sample = self.decision_sampler.create_decision_sample(
                                    market_data=market_data,
                                    strategy=self.strategy,
                                    strategy_signal=signal,
                                    executed_action=executed_action,
                                    regime_info=self.current_regime_info
                                )
                                self.trade_recorder.record_decision_sample(
                                    decision_sample, decision_type)

                            if self.trade_recorder:
                                self.trade_recorder.record_rejected_signal(
                                    signal,
                                    market_data,
                                    "ml_filter",
                                    self.current_regime_info
                                )
                            signal = None
                    elif is_debug and self.ml_filter is not None and self.ml_filter.is_model_available():
                        # En modo debug, evaluar ML pero no rechazar
                        bot_state = {
                            'daily_pnl': self.risk_manager.state.daily_pnl,
                            'daily_trades': self.risk_manager.state.trades_today,
                            'consecutive_signals': self.strategy.consecutive_signals,
                            'daily_pnl_normalized': self.risk_manager.state.daily_pnl / self.config.INITIAL_CAPITAL
                        }

                        ml_decision = await self.ml_filter.filter_signal(
                            signal,
                            market_data,
                            self.current_regime_info,
                            bot_state
                        )

                        if not ml_decision['approved']:
                            reason = ml_decision['reason']
                            prob = ml_decision.get('probability', 0)
                            msg = (f"🐛 [DEBUG] ⚠️ ML rechazaría la señal: {reason} "
                                   f"(P(win)={prob:.2%}), pero DEBUG permite continuar")
                            self.logger.warning(msg)
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
                            # En MVP: solo verificar límites básicos
                            # (pérdida máxima, posiciones máximas)
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
                                msg = ("🐛 [DEBUG] ⚠️ Gestor de riesgo rechazaría "
                                       "la operación, pero DEBUG permite continuar")
                                self.logger.warning(msg)
                            risk_valid = True  # Forzar aprobación en debug
                        else:
                            # Modo normal: validación completa
                            risk_valid = self.risk_manager.validate_trade(
                                signal, self.current_positions)

                        if not risk_valid:
                            executed_action = "HOLD"
                            decision_type = "rejected_risk"
                            
                            if self.decision_sampler and self.trade_recorder and self.config.TRADING_MODE == "PAPER":
                                decision_sample = self.decision_sampler.create_decision_sample(
                                    market_data=market_data,
                                    strategy=self.strategy,
                                    strategy_signal=signal,
                                    executed_action=executed_action,
                                    regime_info=self.current_regime_info
                                )
                                self.trade_recorder.record_decision_sample(
                                    decision_sample, decision_type)

                            self.logger.info(
                                "🚫 Operación rechazada por gestor de riesgo (exposición máxima o límites alcanzados)")

                        # Ejecutar si está validado o en modo MVP/debug
                        if risk_valid:
                            # Cooldown mínimo entre trades (especialmente en PAPER para alta frecuencia controlada)
                            now_time = datetime.now()
                            if self.last_trade_time is not None:
                                elapsed_since_last_trade = (
                                    now_time - self.last_trade_time).total_seconds()
                                if elapsed_since_last_trade < self.min_cooldown_seconds:
                                    # En PAPER (Learning Mode): permitir más frecuencia, pero con cooldown mínimo
                                    # En LIVE: respetar cooldown estrictamente
                                    if self.config.TRADING_MODE == "LIVE":
                                        self.logger.debug(
                                            f"⏳ Cooldown activo: {elapsed_since_last_trade:.1f}s < {self.min_cooldown_seconds}s")
                                        await asyncio.sleep(self.min_cooldown_seconds - elapsed_since_last_trade)
                                    else:
                                        # En PAPER: cooldown más flexible, pero registrar para análisis
                                        if elapsed_since_last_trade < (self.min_cooldown_seconds * 0.5):
                                            await asyncio.sleep(self.min_cooldown_seconds * 0.5 - elapsed_since_last_trade)

                            if self.mvp_mode:
                                self.logger.info(
                                    "🚀 [MVP] Ejecutando orden (prioridad: sample size)")
                            elif is_debug:
                                if not self.risk_manager.validate_trade(signal, self.current_positions):
                                    self.logger.warning(
                                        "🐛 [DEBUG] ⚠️ Ejecutando orden a pesar de validación de riesgo fallida (MODO DEBUG)")
                                msg = ("🐛 [DEBUG] ✅ Ejecutando orden "
                                       "(MODO DEBUG - filtros ignorados)")
                                self.logger.info(msg)
                            else:
                                self.logger.info(
                                    "✅ Riesgo validado, ejecutando orden...")

                            # Ejecutar orden
                            order_result = await self.order_executor.execute_order(signal)

                            # Actualizar tiempo del último trade
                            if order_result.get('success'):
                                self.last_trade_time = datetime.now()

                            if order_result['success']:
                                position = order_result['position']
                                self.current_positions.append(position)
                                self.risk_manager.state.trades_today += 1

                                # Actualizar executed_action para DecisionSample
                                executed_action = signal['action']

                                # Registrar DecisionSample con acción ejecutada (PAPER)
                                if self.decision_sampler and self.trade_recorder and self.config.TRADING_MODE == "PAPER":
                                    decision_sample = self.decision_sampler.create_decision_sample(
                                        market_data=market_data,
                                        strategy=self.strategy,  # Pasar strategy para obtener decision_space
                                        strategy_signal=signal,
                                        executed_action=executed_action,
                                        regime_info=self.current_regime_info
                                    )
                                    self.trade_recorder.record_decision_sample(
                                        decision_sample, "executed")

                                if self.mvp_mode:
                                    trade_num = self.total_trades_count + self.risk_manager.state.trades_today
                                    action = signal['action']
                                    symbol = signal['symbol']
                                    price = signal['price']
                                    size = signal['position_size']
                                    sl = signal['stop_loss']
                                    tp = signal['take_profit']
                                    msg = (f"🚀 [MVP] ✅ Trade #{trade_num}: "
                                           f"{action} {symbol} @ {price:.2f} "
                                           f"(Size: {size:.4f}, SL: {sl:.2f}, TP: {tp:.2f})")
                                    self.logger.info(msg)
                                elif is_debug:
                                    action = signal['action']
                                    symbol = signal['symbol']
                                    price = signal['price']
                                    size = signal['position_size']
                                    sl = signal['stop_loss']
                                    tp = signal['take_profit']
                                    msg = (f"🐛 [DEBUG] ✅ ORDEN EJECUTADA: {action} {symbol} "
                                           f"@ {price:.2f} (Size: {size:.4f}, "
                                           f"SL: {sl:.2f}, TP: {tp:.2f})")
                                    self.logger.info(msg)
                                else:
                                    self.logger.info(
                                        f"✅ {signal['action']} {signal['symbol']} @ {signal['price']} "
                                        f"(Fuerza: {signal['strength']:.2%}, Régimen: {signal.get('regime', 'unknown')})"
                                    )

                                # Guardar contexto para el trade recorder
                                # (SIEMPRE en MVP para generar datos ML)
                                if self.trade_recorder or self.mvp_mode:
                                    # En MVP, crear trade_recorder si no existe
                                    if not self.trade_recorder and self.config.ENABLE_ML:
                                        from src.ml.trade_recorder import TradeRecorder
                                        self.trade_recorder = TradeRecorder()

                                    if self.trade_recorder:
                                        self.position_market_data[position['id']] = {
                                            'market_data': market_data.copy(),
                                            'regime_info': self.current_regime_info.copy() if self.current_regime_info else {},
                                            'ml_decision': ml_decision,
                                            'bot_state': {
                                                'daily_pnl': self.risk_manager.state.daily_pnl,
                                                'daily_trades': self.risk_manager.state.trades_today,
                                                'consecutive_signals': self.strategy.consecutive_signals,
                                            }
                                        }

                                await self.notifications.send_trade_notification(order_result)
                            else:
                                self.logger.error(
                                    f"❌ Error ejecutando orden: {order_result['error']}")
                        else:
                            self.logger.info(
                                "🚫 Operación rechazada por gestor de riesgo (exposición máxima o límites alcanzados)")

                            # Actualizar executed_action = HOLD (se rechazó)
                            executed_action = "HOLD"

                            # Registrar DecisionSample con HOLD (se rechazó por riesgo)
                            if self.decision_sampler and self.trade_recorder and self.config.TRADING_MODE == "PAPER":
                                decision_sample = self.decision_sampler.create_decision_sample(
                                    market_data=market_data,
                                    strategy_signal=signal,
                                    executed_action=executed_action,
                                    regime_info=self.current_regime_info
                                )
                                self.trade_recorder.record_decision_sample(
                                    decision_sample)

                            # También registrar como señal rechazada (compatibilidad)
                            if self.trade_recorder and signal:
                                self.trade_recorder.record_rejected_signal(
                                    signal,
                                    market_data,
                                    "risk_manager",
                                    self.current_regime_info
                                )

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
                                'reason': 'Force time close (30s)',
                                # Para análisis ML
                                'risk_multiplier': position.get('risk_multiplier', 1.0)
                            })

                            # Remover de current_positions
                            if position in self.current_positions:
                                self.current_positions.remove(position)

                            # Remover de executor.positions
                            if position in self.order_executor.positions:
                                self.order_executor.positions.remove(position)

                            # Actualizar estado en RiskManager (ÚNICA FUENTE DE VERDAD)
                            self.risk_manager.apply_trade_result(pnl)

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

                    # ✅ CRÍTICO: Remover de TODAS las listas
                    if position in self.current_positions:
                        self.current_positions.remove(position)
                    if position in self.order_executor.positions:
                        self.order_executor.positions.remove(position)

                    # Guardar estado
                    self.state_manager.save({
                        "equity": self.risk_manager.state.equity,
                        "daily_pnl": self.risk_manager.state.daily_pnl,
                        "trades_today": self.risk_manager.state.trades_today,
                        "peak_equity": self.risk_manager.state.peak_equity,
                        "max_drawdown": self.risk_manager.state.max_drawdown,
                    })

                    self.logger.info(
                        f"✅ Posición cerrada por AdvancedPositionManager | "
                        f"PnL: {pnl:.2f} | Posiciones restantes: {len(self.current_positions)}"
                    )
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

                should_close_mgmt = management_decision.get(
                    'should_close', False)
                if should_close_risk and not should_close_mgmt:
                    msg = f"🛑 [{symbol}] RiskManager detectó condición de cierre (SL/TP/Time)"
                    self.logger.info(msg)

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

                        # Actualizar estado en RiskManager (ÚNICA FUENTE DE VERDAD)
                        self.risk_manager.apply_trade_result(
                            close_result['pnl'])

                        self.logger.info(
                            f"✅ [{symbol}] Posición {position_id} cerrada exitosamente | "
                            f"PnL: {close_result['pnl']:.2f}"
                        )

                        # Guardar estado después de cerrar posición
                        self.state_manager.save({
                            "equity": self.risk_manager.state.equity,
                            "daily_pnl": self.risk_manager.state.daily_pnl,
                            "trades_today": self.risk_manager.state.trades_today,
                            "peak_equity": self.risk_manager.state.peak_equity,
                            "max_drawdown": self.risk_manager.state.max_drawdown,
                        })

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

                        pos_symbol = position.get('symbol')
                        pnl = close_result['pnl']
                        reason = management_decision.get(
                            'reason', 'Stop/TP alcanzado')
                        msg = (f"✅ Posición cerrada: {pos_symbol} - "
                               f"PnL={pnl:.2f} - Tipo: {exit_type} - Razón: {reason}")
                        self.logger.info(msg)

                        # Registrar trade completo para ML (SIEMPRE en MVP)
                        has_recorder = self.trade_recorder or self.mvp_mode
                        has_data = position_id in self.position_market_data
                        should_record = has_recorder and has_data
                        if should_record:
                            # Asegurar que trade_recorder existe en MVP
                            if not self.trade_recorder and self.config.ENABLE_ML:
                                from src.ml.trade_recorder import TradeRecorder
                                self.trade_recorder = TradeRecorder()

                            if self.trade_recorder:
                                # Obtener contexto de mercado al momento de entrada
                                market_data_context = None
                                if position_id in self.position_market_data:
                                    ctx_data = self.position_market_data[position_id]
                                    market_data_context = ctx_data.get(
                                        'market_data', {})
                                    # Incluir indicators si están disponibles
                                    if not market_data_context.get('indicators'):
                                        # Si no hay indicators guardados, usar datos actuales como fallback
                                        market_data_context['indicators'] = market_data.get(
                                            'indicators', {})

                                # Registrar trade en CSV con contexto completo
                                self.trade_recorder.record_trade(
                                    position=position,
                                    exit_price=close_result.get(
                                        'exit_price', current_price),
                                    pnl=close_result['pnl'],
                                    market_data_context=market_data_context
                                )

                                # Limpiar contexto guardado
                                if position_id in self.position_market_data:
                                    del self.position_market_data[position_id]

                                # Actualizar progreso ML y métricas
                                if self.trade_recorder:
                                    # Log progreso ML cada 10 trades
                                    if self.risk_manager.state.trades_today % 10 == 0:
                                        if self.ml_progress:
                                            self.ml_progress.log_progress()

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
                self.risk_manager.state.daily_pnl += close_result['pnl']

    def _build_dashboard_payload(
            self, market_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
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

        # Calcular win rate del día si hay trades
        win_rate_daily = None
        winning_trades_daily = 0
        losing_trades_daily = 0
        if len(self.risk_manager.trade_history) > 0:
            winning_trades_daily = sum(
                1 for trade in self.risk_manager.trade_history if trade.get('pnl', 0) > 0)
            losing_trades_daily = sum(
                1 for trade in self.risk_manager.trade_history if trade.get('pnl', 0) <= 0)
            total_trades_daily = len(self.risk_manager.trade_history)
            win_rate_daily = winning_trades_daily / \
                total_trades_daily if total_trades_daily > 0 else None

        # Calcular métricas históricas desde training_data (para ML)
        historical_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': None,
            'win_rate_percent': None,
        }

        if self.trade_recorder:
            try:
                df = self.trade_recorder.get_training_data()
                if df is not None and not df.empty and 'target' in df.columns:
                    total_historical = len(df)
                    winning_historical = int(
                        df['target'].sum()) if 'target' in df.columns else 0
                    losing_historical = total_historical - winning_historical
                    win_rate_historical = winning_historical / \
                        total_historical if total_historical > 0 else None

                    historical_metrics = {
                        'total_trades': int(total_historical),
                        'winning_trades': int(winning_historical),
                        'losing_trades': int(losing_historical),
                        'win_rate': float(win_rate_historical) if win_rate_historical is not None else None,
                        'win_rate_percent': float(win_rate_historical * 100) if win_rate_historical is not None else None,
                    }
            except Exception as e:
                self.logger.debug(
                    f"No se pudieron calcular métricas históricas: {e}")

        # Asegurar que max_drawdown tenga un valor válido
        max_dd = self.risk_manager.state.max_drawdown
        if max_dd is None:
            max_dd = 0.0

        # Calcular métricas estadísticas avanzadas del día
        avg_win_daily = None
        avg_loss_daily = None
        profit_factor_daily = None
        expectancy_daily = None
        largest_win_daily = None
        largest_loss_daily = None

        if len(self.risk_manager.trade_history) > 0:
            wins = [t.get('pnl', 0)
                    for t in self.risk_manager.trade_history if t.get('pnl', 0) > 0]
            losses = [t.get('pnl', 0) for t in self.risk_manager.trade_history if t.get(
                'pnl', 0) <= 0]

            if wins:
                avg_win_daily = sum(wins) / len(wins)
                largest_win_daily = max(wins)
            if losses:
                avg_loss_daily = sum(losses) / len(losses)
                largest_loss_daily = min(losses)

            # Profit Factor = Total ganancias / Total pérdidas (absolutas)
            total_wins = sum(wins) if wins else 0
            total_losses_abs = abs(sum(losses)) if losses else 1
            profit_factor_daily = total_wins / \
                total_losses_abs if total_losses_abs > 0 else None

            # Expectativa = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
            win_rate = win_rate_daily or 0
            loss_rate = 1 - win_rate
            if avg_win_daily is not None and avg_loss_daily is not None:
                expectancy_daily = (win_rate * avg_win_daily) + \
                    (loss_rate * avg_loss_daily)

        # Obtener risk multiplier actual (learning-aware)
        risk_multiplier = self.risk_manager.get_adaptive_risk_multiplier() if hasattr(
            self.risk_manager, 'get_adaptive_risk_multiplier') else 1.0

        # Calcular métricas históricas avanzadas
        avg_win_historical = None
        avg_loss_historical = None
        profit_factor_historical = None
        expectancy_historical = None

        if self.trade_recorder:
            try:
                df = self.trade_recorder.get_training_data()
                if df is not None and not df.empty and 'pnl' in df.columns:
                    wins_hist = df[df['pnl'] > 0]['pnl'].tolist()
                    losses_hist = df[df['pnl'] <= 0]['pnl'].tolist()

                    if wins_hist:
                        avg_win_historical = float(
                            sum(wins_hist) / len(wins_hist))
                    if losses_hist:
                        avg_loss_historical = float(
                            sum(losses_hist) / len(losses_hist))

                    total_wins_hist = sum(wins_hist) if wins_hist else 0
                    total_losses_abs_hist = abs(
                        sum(losses_hist)) if losses_hist else 1
                    profit_factor_historical = total_wins_hist / \
                        total_losses_abs_hist if total_losses_abs_hist > 0 else None

                    hist_win_rate = historical_metrics.get('win_rate') or 0
                    hist_loss_rate = 1 - hist_win_rate
                    if avg_win_historical is not None and avg_loss_historical is not None:
                        expectancy_historical = (
                            hist_win_rate * avg_win_historical) + (hist_loss_rate * avg_loss_historical)
            except Exception as e:
                self.logger.debug(
                    f"No se pudieron calcular métricas históricas avanzadas: {e}")

        metrics = {
            'daily_pnl': float(self.risk_manager.state.daily_pnl or 0.0),
            'daily_trades': int(self.risk_manager.state.trades_today or 0),
            'winning_trades_daily': int(winning_trades_daily),
            'losing_trades_daily': int(losing_trades_daily),
            'win_rate_daily': float(win_rate_daily) if win_rate_daily is not None else None,
            'win_rate_daily_percent': float(win_rate_daily * 100) if win_rate_daily is not None else None,
            'max_drawdown': float(max_dd),
            # Métricas estadísticas avanzadas del día
            'avg_win_daily': float(avg_win_daily) if avg_win_daily is not None else None,
            'avg_loss_daily': float(avg_loss_daily) if avg_loss_daily is not None else None,
            'profit_factor_daily': float(profit_factor_daily) if profit_factor_daily is not None else None,
            'expectancy_daily': float(expectancy_daily) if expectancy_daily is not None else None,
            'largest_win_daily': float(largest_win_daily) if largest_win_daily is not None else None,
            'largest_loss_daily': float(largest_loss_daily) if largest_loss_daily is not None else None,
            # Risk multiplier adaptativo (learning-aware)
            'risk_multiplier': float(risk_multiplier),
            # Métricas históricas (para ML)
            'historical': {
                **historical_metrics,
                'avg_win': avg_win_historical,
                'avg_loss': avg_loss_historical,
                'profit_factor': profit_factor_historical,
                'expectancy': expectancy_historical,
            },
        }

        # Calcular equity actual (capital inicial + PnL acumulado)
        current_equity = self.config.INITIAL_CAPITAL + self.risk_manager.state.daily_pnl
        peak_equity = max(
            self.config.INITIAL_CAPITAL,
            self.risk_manager.state.peak_equity or self.config.INITIAL_CAPITAL,
            current_equity
        )

        balance = {
            'current': float(current_equity),
            'peak': float(peak_equity),
            'exposure': sum(
                (self._safe_float(p.get('size')) or 0.0) *
                (self._safe_float(p.get('entry_price')) or 0.0)
                for p in self.current_positions
            )
        }

        market_snapshot = None
        if market_data:
            price = self._safe_float(market_data.get('price')) or 0.0
            # Calcular change y change_percent si no están disponibles
            change = self._safe_float(market_data.get('change'))
            change_percent = self._safe_float(
                market_data.get('change_percent'))

            # Si no hay change, calcular basado en open y price
            if change is None:
                open_price = self._safe_float(market_data.get('open'))
                if open_price and open_price > 0:
                    change = price - open_price
                    change_percent = (change / open_price) * 100

            # Detectar si son datos reales o simulados
            is_real_data = self.market_data.exchange is not None if hasattr(
                self.market_data, 'exchange') else False
            data_source = 'BINANCE_REAL' if is_real_data else 'SIMULATED'

            market_snapshot = {
                'symbol': market_data.get('symbol') or self.config.SYMBOL,
                'price': price,
                'open': self._safe_float(market_data.get('open')) or price,
                'high': self._safe_float(market_data.get('high')) or price,
                'low': self._safe_float(market_data.get('low')) or price,
                'close': price,
                'volume': self._safe_float(market_data.get('volume')) or 0.0,
                'change': change or 0.0,
                'change_percent': change_percent or 0.0,
                'data_source': data_source,  # Información sobre origen de datos
                'is_real_data': is_real_data,  # Flag booleano para fácil verificación
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
            # Asegurar que siempre haya indicadores, incluso si están vacíos
            market_snapshot['indicators'] = {
                'rsi': self._safe_float(indicators.get('rsi')) or 50.0,
                'fast_ma': self._safe_float(indicators.get('fast_ma')) or price,
                'slow_ma': self._safe_float(indicators.get('slow_ma')) or price,
                'macd': self._safe_float(indicators.get('macd')) or 0.0,
            }

            # Si no hay ohlc_history, crear datos básicos para el gráfico
            if 'ohlc_history' not in market_snapshot or not market_snapshot['ohlc_history']:
                # Crear una vela básica con el precio actual
                now = datetime.now()
                market_snapshot['ohlc_history'] = [{
                    'timestamp': now.isoformat(),
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': market_snapshot.get('volume', 0.0)
                }]

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

        # Obtener órdenes ejecutadas (últimas 50)
        orders_executed = []
        if self.order_executor and hasattr(self.order_executor, 'executed_orders'):
            try:
                recent_orders = self.order_executor.executed_orders[-50:
                                                                    ] if self.order_executor.executed_orders else []
                for order in recent_orders:
                    order_time = order.get('timestamp')
                    if isinstance(order_time, datetime):
                        order_time = order_time.isoformat()
                    orders_executed.append({
                        'id': order.get('id', ''),
                        'symbol': order.get('symbol', ''),
                        'side': order.get('side', '').upper(),
                        'price': self._safe_float(order.get('price')),
                        'size': self._safe_float(order.get('size')),
                        'status': order.get('status', ''),
                        'timestamp': order_time,
                        'pnl': self._safe_float(order.get('pnl')),
                    })
            except Exception as e:
                self.logger.debug(
                    f"No se pudieron obtener órdenes ejecutadas: {e}")

        # Información del régimen de mercado (si está disponible)
        regime_info = None
        if hasattr(self, 'current_regime_info') and self.current_regime_info:
            regime_info = {
                'regime': self.current_regime_info.get('regime', 'unknown'),
                'volatility': self._safe_float(self.current_regime_info.get('volatility')),
                'trend': self.current_regime_info.get('trend', 'unknown'),
            }

        # Información del modo de operación
        operation_mode = {
            'trading_mode': self.config.TRADING_MODE,
            'mvp_mode': self.mvp_mode,
            'ml_enabled': self.ml_filter is not None and hasattr(self.ml_filter, 'is_model_available') and self.ml_filter.is_model_available() if self.ml_filter else False,
            'target_trades_for_ml': 500,
            'current_trades_count': historical_metrics.get('total_trades', 0),
        }

        return {
            'positions': positions,
            'metrics': metrics,
            'balance': balance,
            'market': market_snapshot,
            'current_signal': current_signal_snapshot,
            'orders': orders_executed,  # Historial de órdenes ejecutadas
            'regime': regime_info,  # Información del régimen de mercado
            'operation_mode': operation_mode,  # Información del modo de operación
            'bot_status': {
                'is_running': self.is_running,
                'trading_time': self._is_trading_time(),
                'initial_capital': float(self.config.INITIAL_CAPITAL),
            },
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
            # En modo PAPER no se requieren API keys (puede funcionar sin ellas)
            # Solo validar API keys si está en modo LIVE
            if self.config.TRADING_MODE == 'LIVE':
                # Verificar configuración de mercado solo en modo LIVE
                if self.config.MARKET == 'CRYPTO' and not self.config.BINANCE_API_KEY:
                    self.logger.error(
                        "❌ API Key de Binance no configurada (requerida en modo LIVE)")
                    return False

                is_stock = self.config.MARKET == 'STOCK'
                no_api_key = not self.config.ALPACA_API_KEY
                if is_stock and no_api_key:
                    self.logger.error(
                        "❌ API Key de Alpaca no configurada (requerida en modo LIVE)")
                    return False
            else:
                # En modo PAPER, advertir pero permitir continuar
                if self.config.MARKET == 'CRYPTO' and not self.config.BINANCE_API_KEY:
                    self.logger.info(
                        "ℹ️ Modo PAPER: Sin API Key de Binance (usando datos simulados)")
                if self.config.MARKET == 'STOCK' and not self.config.ALPACA_API_KEY:
                    self.logger.info(
                        "ℹ️ Modo PAPER: Sin API Key de Alpaca (usando datos simulados)")

            # Verificar límites de riesgo
            if self.config.RISK_PER_TRADE <= 0 or self.config.RISK_PER_TRADE > 0.1:
                self.logger.error(
                    "❌ Riesgo por trade debe estar entre 0 y 0.1 (10 porciento)")
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
            # ✅ El RiskManager learning-aware maneja los límites diarios
            # En modo PAPER: permite continuar con riesgo reducido
            # En modo LIVE: bloquea estrictamente
            # No necesitamos verificación manual aquí - usar validate_trade()

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

    def _signal_handler(self, signum, frame):  # pylint: disable=unused-argument
        """Manejador de señales del sistema"""
        self.logger.info(f"📡 Señal recibida: {signum}")
        asyncio.create_task(self.stop())

    def _validate_architecture(self):
        """
        Valida que la arquitectura esté correctamente configurada.

        Verifica:
        - ProductionStrategy es idéntica en PAPER y LIVE
        - DecisionSampler solo existe en PAPER
        - LearningStrategy solo se usa en PAPER
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("🔍 VALIDACIÓN DE ARQUITECTURA")
            self.logger.info("=" * 60)

            # 1. Verificar estrategia según modo
            strategy_name = type(self.strategy).__name__
            if self.config.TRADING_MODE == "PAPER":
                if strategy_name == "LearningStrategy":
                    self.logger.info(
                        "✅ PAPER mode: Usando LearningStrategy (correcto)")
                else:
                    self.logger.warning(
                        f"⚠️ PAPER mode: Usando {strategy_name} (esperado LearningStrategy)")

                # Verificar DecisionSampler
                if self.decision_sampler:
                    self.logger.info(
                        "✅ Decision Sampling Layer activada en PAPER (correcto)")
                else:
                    self.logger.warning(
                        "⚠️ Decision Sampling Layer NO activada en PAPER")
            else:
                if strategy_name == "TradingStrategy" or strategy_name == "ProductionStrategy":
                    self.logger.info(
                        f"✅ LIVE mode: Usando {strategy_name} (correcto)")
                else:
                    self.logger.warning(
                        f"⚠️ LIVE mode: Usando {strategy_name} (esperado ProductionStrategy)")

                # Verificar que NO hay DecisionSampler en LIVE
                if self.decision_sampler is None:
                    self.logger.info(
                        "✅ Decision Sampling Layer desactivada en LIVE (correcto)")
                else:
                    self.logger.warning(
                        "⚠️ Decision Sampling Layer activada en LIVE (no debería estar)")

            # 2. Verificar que DecisionSampler usa decision_space de Strategy
            if self.decision_sampler and self.strategy:
                if hasattr(self.strategy, 'get_decision_space'):
                    self.logger.info(
                        "✅ Strategy tiene método get_decision_space() (DecisionSampler lo usará)")
                else:
                    self.logger.warning(
                        "⚠️ Strategy NO tiene método get_decision_space() (DecisionSampler usará fallback)")

            # 3. Verificar TradeRecorder
            if self.trade_recorder:
                self.logger.info("✅ TradeRecorder activado")
                if hasattr(self.trade_recorder, 'record_decision_sample'):
                    self.logger.info(
                        "✅ TradeRecorder tiene método record_decision_sample (correcto)")
                else:
                    self.logger.warning(
                        "⚠️ TradeRecorder NO tiene método record_decision_sample")

                # Verificar que tiene archivo de decisiones separado
                if hasattr(self.trade_recorder, 'decisions_file'):
                    self.logger.info(
                        f"✅ TradeRecorder tiene archivo de decisiones: {self.trade_recorder.decisions_file}")
                else:
                    self.logger.warning(
                        "⚠️ TradeRecorder NO tiene archivo de decisiones separado")
            else:
                if self.config.TRADING_MODE == "PAPER":
                    self.logger.warning(
                        "⚠️ TradeRecorder desactivado en PAPER (debería estar activo)")
                else:
                    self.logger.info(
                        "ℹ️ TradeRecorder desactivado (modo LIVE sin ML)")

            # 4. Validación adicional: confirmar que ProductionStrategy no referencia TRADING_MODE
            if hasattr(self.strategy, '_analyze_indicators'):
                import inspect
                try:
                    source = inspect.getsource(
                        self.strategy._analyze_indicators)
                    if "TRADING_MODE" in source or "is_paper_mode" in source:
                        self.logger.warning(
                            "⚠️ ProductionStrategy contiene referencia a TRADING_MODE (debería ser idéntica en PAPER/LIVE)")
                    else:
                        self.logger.info(
                            "✅ ProductionStrategy no referencia TRADING_MODE (correcto)")
                except Exception as e:
                    self.logger.debug(
                        f"No se pudo inspeccionar código fuente: {e}")

            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.exception(
                f"❌ Error en validación de arquitectura: {e}")


async def main():
    """Función principal"""
    bot = TradingBot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n🛑 Interrupción del usuario")
        bot.logger.info("🛑 Guardando estado antes de salir...")

        # Guardar estado al salir
        bot.state_manager.save({
            "equity": bot.risk_manager.state.equity,
            "daily_pnl": bot.risk_manager.state.daily_pnl,
            "trades_today": bot.risk_manager.state.trades_today,
            "peak_equity": bot.risk_manager.state.peak_equity,
            "max_drawdown": bot.risk_manager.state.max_drawdown,
        })

        bot.logger.info("✅ Estado guardado correctamente")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
