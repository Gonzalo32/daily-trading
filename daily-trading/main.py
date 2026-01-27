"""
Bot de Day Trading Automatizado AVANZADO
Archivo principal que orquesta todos los componentes del sistema con:
- Preparación diaria (análisis de régimen)
- Parámetros dinámicos
- Filtro ML
- Gestión avanzada de posiciones
"""


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
from src.ml.ml_v2_filter import MLV2Filter
from src.state.state_manager import StateManager
from src.utils.decision_constants import (
    DecisionOutcome,
    ExecutedAction,
    validate_decision_consistency,
    validate_decision_outcome,
    VALID_EXECUTED_ACTIONS,
    VALID_DECISION_OUTCOMES
)
from src.utils.decision_pipeline import (
    TickDecision,
    create_tick_decision_no_signal,
    create_tick_decision_executed,
    create_tick_decision_rejected,
    normalize_rejection,
    run_decision_invariant_smoke_tests
)


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

        self.market_data = MarketDataProvider(self.config)

        self.strategy = StrategyFactory.create_strategy(self.config)
        self.risk_manager = RiskManager(self.config)

        self.state_manager = StateManager(self.config.STATE_PATH)
        state_path = self.state_manager.path
        state_exists = self.state_manager.exists()
        self.logger.info(
            f"State path configurado: {state_path} | encontrado={state_exists}"
        )

        persisted_state = self.state_manager.load()
        today = datetime.now().date()

        if persisted_state:

            last_saved_at = persisted_state.get("last_saved_at")
            if last_saved_at:
                try:
                    if isinstance(last_saved_at, str):
                        last_date = datetime.fromisoformat(
                            last_saved_at.replace('Z', '+00:00')).date()
                    else:
                        last_date = last_saved_at.date() if hasattr(last_saved_at, 'date') else today

                    if last_date < today:
                        self.logger.info(
                            f"Nuevo dia detectado ({last_date} -> {today}). Reseteando metricas diarias.")
                        self.risk_manager.reset_daily_metrics()
                    else:

                        self.risk_manager.state.daily_pnl = persisted_state.get(
                            "daily_pnl", 0.0
                        )
                        trades_today_legacy = persisted_state.get(
                            "trades_today", 0)
                        self.risk_manager.state.executed_trades_today = persisted_state.get(
                            "executed_trades_today", trades_today_legacy)
                        self.risk_manager.state.decision_samples_collected = persisted_state.get(
                            "decision_samples_collected", 0)
                        self.risk_manager.state.trades_today = self.risk_manager.state.executed_trades_today
                except Exception as e:
                    self.logger.warning(
                        f"Error verificando fecha del estado: {e}. Reseteando metricas diarias.")
                    self.risk_manager.reset_daily_metrics()
            else:

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
                "loaded state from %s | equity=%.2f | pnl=%.2f | trades=%d | peak=%.2f",
                state_path,
                self.risk_manager.state.equity,
                self.risk_manager.state.daily_pnl,
                self.risk_manager.state.executed_trades_today,
                self.risk_manager.state.peak_equity
            )
        else:
            self.logger.info(
                f"Estado no encontrado o vacio en {state_path}. Se mantiene estado inicial."
            )

        self.order_executor = OrderExecutor(self.config)
        self.dashboard = Dashboard(
            self.config) if self.config.ENABLE_DASHBOARD else None
        self.notifications = NotificationManager(self.config)

        self.regime_classifier = MarketRegimeClassifier(self.config)
        self.param_manager = DynamicParameterManager(self.config)
        self.position_manager = AdvancedPositionManager(self.config)

        self.decision_sampler = DecisionSampler(
            self.config) if self.config.TRADING_MODE == "PAPER" else None
        if self.decision_sampler:
            self.logger.info("📊 Decision Sampling Layer activada (PAPER mode)")

        ml_enabled = self.config.ENABLE_ML or (
            self.config.TRADING_MODE == "PAPER")
        self.trade_recorder = TradeRecorder() if ml_enabled else None

        self.ml_filter = MLSignalFilter(
            model_path=self.config.ML_MODEL_PATH,
            min_probability=self.config.ML_MIN_PROBABILITY,
        ) if ml_enabled and self.config.ENABLE_ML else None
        
        self.ml_v2_filter = MLV2Filter(
            model_path="models/ml_v2_model.pkl",
            paper_threshold_percentile=70.0,
            live_threshold_percentile=80.0,
            trading_mode=self.config.TRADING_MODE
        ) if ml_enabled else None

        if ml_enabled or self.config.TRADING_MODE == "PAPER":
            from src.ml.ml_progress_tracker import MLProgressTracker
            self.ml_progress = MLProgressTracker()

            self.ml_progress.log_progress()
        else:
            self.ml_progress = None

        self.is_running = False
        self.current_positions = []

        self.current_signal = None
        self.position_market_data = {}

        self.last_trade_time = None
        self.min_cooldown_seconds = self.config.MIN_COOLDOWN_BETWEEN_TRADES

        self.daily_prepared = False
        self.last_preparation_date = None
        self.current_regime_info = None
        self.current_parameters = None

        self.mvp_mode = False
        self.total_trades_count = 0

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    async def start(self):
        """Iniciar el bot de trading"""
        try:
            self.logger.info("🚀 Iniciando Bot de Day Trading Avanzado...")
            self.logger.info("=" * 60)

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

            self._validate_architecture()

            if not self._validate_config():
                self.logger.error("❌ Configuración inválida. Abortando...")
                return

            await self._initialize_components()

            self._validate_architecture()

            await self._check_mvp_mode()

            if not self.mvp_mode:
                await self._daily_preparation()
            else:
                self.logger.info(
                    "🚀 MODO MVP: Saltando preparación diaria avanzada")

                if self.config.TRADING_MODE == "PAPER":
                    max_trades_mvp = getattr(self.config, "PAPER_MAX_DAILY_TRADES", None) or getattr(
                        self.config, "MAX_DAILY_TRADES", 100)
                else:
                    max_trades_mvp = 20
                self.current_parameters = {
                    'max_daily_trades': max_trades_mvp,
                    'stop_loss_pct': self.config.STOP_LOSS_PCT,
                    'take_profit_ratio': self.config.TAKE_PROFIT_RATIO,
                    'risk_per_trade': self.config.RISK_PER_TRADE,
                }

            self._validate_decision_system()

            if getattr(self.config, 'ENABLE_SMOKE_TESTS', False) and self.config.TRADING_MODE == "PAPER":
                self.logger.info("🧪 Ejecutando smoke tests de invariantes...")
                if run_decision_invariant_smoke_tests():
                    self.logger.info("✅ Smoke tests pasaron correctamente")
                else:
                    self.logger.error(
                        "❌ Smoke tests fallaron - revisar invariantes")
                    if self.config.TRADING_MODE == "PAPER":
                        raise ValueError(
                            "Smoke tests fallaron - abortando en PAPER")

            if self.dashboard:
                self.logger.info("🌐 Iniciando dashboard...")
                try:
                    await self.dashboard.start()
                    self.logger.info("✅ Dashboard iniciado correctamente")
                except Exception as dashboard_error:
                    self.logger.error(f"❌ Error iniciando dashboard: {dashboard_error}", exc_info=True)
                    self.logger.warning("⚠️ Continuando sin dashboard...")
                    self.dashboard = None

            self.logger.info("🔄 Iniciando loop principal...")
            self.is_running = True
            await self._main_loop()

        except KeyboardInterrupt:
            self.logger.info("⚠️ Interrupción de teclado recibida")
            await self.stop()
        except Exception as e:
            self.logger.error(f"❌ Error crítico en el bot: {e}", exc_info=True)
            await self._emergency_shutdown()

    async def stop(self):
        """Detener el bot de trading"""
        self.logger.info("🛑 Deteniendo Bot de Day Trading...")
        self.is_running = False

        if self.current_positions:
            self.logger.warning("⚠️ Cerrando posiciones abiertas...")
            await self._close_all_positions()

        if self.dashboard:
            await self.dashboard.stop()

        self.logger.info("✅ Bot detenido correctamente")

    async def _initialize_components(self):
        """
        Inicializa todos los componentes del bot.
        ÚNICA versión (eliminado duplicado).
        """
        try:
            self.logger.info("🔧 Inicializando componentes...")

            self.logger.info("📊 Inicializando MarketDataProvider...")
            await self.market_data.initialize()
            if self.market_data.exchange:
                self.logger.info(
                    "✅ MarketDataProvider inicializado con conexión a Binance")
            else:
                self.logger.warning(
                    "⚠️ MarketDataProvider sin conexión (modo simulado)")

            self.logger.info("📦 Inicializando OrderExecutor...")
            await self.order_executor.initialize()

            if self.config.ENABLE_NOTIFICATIONS:
                if not hasattr(self, 'notifications') or self.notifications is None:
                    from src.utils.notifications import NotificationManager
                    self.notifications = NotificationManager(self.config)
                await self.notifications.initialize()

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

            self.logger.info("📥 Descargando histórico reciente...")
            historical_data = await self.market_data.get_historical_data(
                symbol=self.config.SYMBOL,
                days=90,
                timeframe=self.config.TIMEFRAME
            )

            if historical_data is None or len(historical_data) < 20:
                self.logger.warning(
                    "⚠️ Datos históricos insuficientes, usando configuración por defecto")
                self.daily_prepared = True
                return

            self.logger.info(
                f"✅ Histórico descargado: {len(historical_data)} períodos")

            self.logger.info("🔍 Analizando régimen de mercado...")
            self.current_regime_info = await self.regime_classifier.analyze_daily_regime(
                historical_data,
                self.config.SYMBOL
            )

            regime = self.current_regime_info.get('regime', 'unknown')
            confidence = self.current_regime_info.get('confidence', 0)

            self.logger.info(
                f"✅ Régimen detectado: {regime.upper()} (confianza: {confidence:.2%})")

            self.logger.info("🔧 Adaptando parámetros al régimen...")
            self.current_parameters = self.param_manager.adapt_parameters(
                self.current_regime_info)
            self.strategy.update_parameters_for_regime(
                self.current_regime_info)

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

            if self.config.TRADING_MODE == "PAPER":
                max_trades = self.config.PAPER_MAX_DAILY_TRADES
                self.logger.info(
                    f"   └─ Max trades diarios (PAPER): {max_trades} (fijo, ignorando límite adaptativo)")
            else:
                max_trades = self.current_parameters.get('max_daily_trades', 5)
                self.logger.info(
                    f"   └─ Max trades diarios (LIVE): {max_trades}")
            self.current_parameters['max_daily_trades'] = max_trades

            if self.ml_filter is not None and self.ml_filter.is_model_available():
                self.logger.info("✅ Modelo ML cargado y disponible")
                model_info = self.ml_filter.get_model_info()
                self.logger.info(
                    f"   └─ Probabilidad mínima: {model_info['min_probability']:.2%}")
            elif self.config.ENABLE_ML:
                self.logger.warning(
                    "⚠️ ML habilitado pero modelo no disponible")

            self.daily_prepared = True
            self.last_preparation_date = datetime.now().date()

            self.logger.info("=" * 60)
            self.logger.info("✅ PREPARACIÓN DIARIA COMPLETADA")
            self.logger.info("🟢 Sistema listo para operar")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"❌ Error en preparación diaria: {e}")

            self.daily_prepared = True

    def _validate_architecture(self):
        """
        Valida que la arquitectura esté correctamente configurada.
        ÚNICA versión (eliminado duplicado).

        Verifica:
        - ProductionStrategy es idéntica en PAPER y LIVE
        - DecisionSampler solo existe en PAPER
        - LearningStrategy solo se usa en PAPER
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("🔍 VALIDACIÓN DE ARQUITECTURA")
            self.logger.info("=" * 60)

            if isinstance(self.strategy, type(self.strategy)):
                strategy_name = type(self.strategy).__name__
                if strategy_name == "TradingStrategy" or strategy_name == "ProductionStrategy":
                    import inspect
                    source = inspect.getsource(self.strategy.__class__)
                    if "TRADING_MODE" in source or "is_paper_mode" in source:
                        self.logger.error(
                            "❌ ERROR ARQUITECTÓNICO: ProductionStrategy contiene referencias a TRADING_MODE")
                        raise ValueError(
                            "ProductionStrategy debe ser 100% determinística e independiente de TRADING_MODE")
                    else:
                        self.logger.info(
                            "✅ ProductionStrategy es determinística (sin dependencias de TRADING_MODE)")

            if self.config.TRADING_MODE == "PAPER":
                if not self.decision_sampler:
                    self.logger.warning(
                        "⚠️ DecisionSampler no está activo en modo PAPER")
                else:
                    self.logger.info(
                        "✅ DecisionSampler activo para generación de datos")

            if hasattr(self.strategy, 'get_decision_space'):
                self.logger.info("✅ Strategy implementa get_decision_space()")
            else:
                self.logger.warning(
                    "⚠️ Strategy no implementa get_decision_space()")

            self.logger.info("✅ Validación de arquitectura completada")
        except Exception as e:
            self.logger.error(f"❌ Error en validación de arquitectura: {e}")

    async def _check_mvp_mode(self):
        """
        Verifica si debe activarse el modo MVP
        MVP se activa automáticamente si hay < 500 trades históricos
        """
        try:
            if not self.config.MVP_MODE_ENABLED:
                self.mvp_mode = False
                return

            if self.trade_recorder:
                try:
                    df = self.trade_recorder.get_training_data()
                    self.total_trades_count = len(
                        df) if df is not None and not df.empty else 0
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ No se pudo contar trades históricos: {e}")
                    self.total_trades_count = 0

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

            self.mvp_mode = True

    async def _check_daily_preparation(self) -> bool:
        """
        Verifica si necesitamos re-preparar (nuevo día)
        Retorna True si está preparado, False si necesita preparación
        """
        today = datetime.now().date()

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

                if (current_time - last_status_log).total_seconds() >= 30:
                    positions_count = self.position_manager.count_open_positions(self.current_positions)
                    self.logger.info(
                        f"💓 Bot activo | Iteración #{iteration_count} | "
                        f"PnL: {self.risk_manager.state.daily_pnl:.2f} | Trades: {self.risk_manager.state.executed_trades_today} | "
                        f"Posiciones: {positions_count}"
                    )
                    last_status_log = current_time

                    if self.dashboard:
                        dashboard_data = self._build_dashboard_payload(
                            market_data if 'market_data' in locals() else None)
                        await self.dashboard.update_data(dashboard_data)

                if self.config.TRADING_MODE == "LIVE":
                    if self.risk_manager.state.executed_trades_today >= self.config.MAX_DAILY_TRADES:
                        self.logger.warning(
                            f"⛔ [LIVE] Límite de trades diarios alcanzado: {self.risk_manager.state.executed_trades_today}"
                        )
                        await asyncio.sleep(60)
                        continue
                else:
                    paper_max_trades = getattr(self.config, "PAPER_MAX_DAILY_TRADES", None) or getattr(
                        self.config, "MAX_DAILY_TRADES", 100)
                    if self.risk_manager.state.executed_trades_today >= paper_max_trades:
                        if self.risk_manager.state.executed_trades_today % 100 == 0:
                            self.logger.info(
                                f"📚 [PAPER] Trades ejecutados: {self.risk_manager.state.executed_trades_today} "
                                f"(límite informativo: {paper_max_trades}) - DecisionSamples continuarán")

                if not self._is_trading_time():
                    if self.config.TRADING_MODE == "LIVE":
                        await asyncio.sleep(60)
                        continue

                if self.mvp_mode:

                    if self.config.TRADING_MODE == "PAPER":
                        max_daily_trades = getattr(self.config, "PAPER_MAX_DAILY_TRADES", None) or getattr(
                            self.config, "MAX_DAILY_TRADES", 100)
                    else:
                        max_daily_trades = self.config.MAX_DAILY_TRADES

                    if self.config.TRADING_MODE == "LIVE":
                        if self.risk_manager.state.executed_trades_today >= max_daily_trades:
                            self.logger.warning(
                                f"🚨 [LIVE] Máximo de trades diarios alcanzado ({self.risk_manager.state.executed_trades_today}/{max_daily_trades})")
                            await asyncio.sleep(300)
                            continue
                    else:
                        if self.risk_manager.state.executed_trades_today >= max_daily_trades:
                            if self.risk_manager.state.executed_trades_today % 100 == 0:
                                self.logger.info(
                                    f"📚 [PAPER Learning Mode - MVP] {self.risk_manager.state.executed_trades_today} trades ejecutados "
                                    f"(límite informativo: {max_daily_trades}) - DecisionSamples continuarán")
                else:

                    if self.config.TRADING_MODE == "PAPER":
                        max_daily_trades = self.config.PAPER_MAX_DAILY_TRADES
                    else:
                        if self.current_parameters:
                            max_daily_trades = min(
                                self.current_parameters.get(
                                    'max_daily_trades', self.config.MAX_DAILY_TRADES),
                                self.config.MAX_DAILY_TRADES
                            )
                        else:
                            max_daily_trades = self.config.MAX_DAILY_TRADES

                    if self.config.TRADING_MODE == "LIVE":
                        limits_ok = self.risk_manager.check_daily_limits(
                            daily_pnl=self.risk_manager.state.daily_pnl
                        )
                        if not limits_ok:
                            msg = (f"🚨 [LIVE] Límites diarios alcanzados - Trading bloqueado "
                                   f"(PnL: {self.risk_manager.state.daily_pnl:.2f} o trades: {self.risk_manager.state.executed_trades_today})")
                            self.logger.warning(msg)
                            await asyncio.sleep(300)
                            continue

                        if self.risk_manager.state.executed_trades_today >= max_daily_trades:
                            self.logger.warning(
                                f"🚨 [LIVE] Máximo de trades diarios alcanzado ({self.risk_manager.state.executed_trades_today}/{max_daily_trades})")
                            await asyncio.sleep(300)
                            continue
                    else:
                        limits_ok = self.risk_manager.check_daily_limits(
                            daily_pnl=self.risk_manager.state.daily_pnl
                        )
                        if not limits_ok:
                            self.logger.info(
                                f"📚 [PAPER] Límites informativos alcanzados (PnL: {self.risk_manager.state.daily_pnl:.2f}) - DecisionSamples continuarán")

                        if self.risk_manager.state.executed_trades_today >= max_daily_trades:
                            if self.risk_manager.state.executed_trades_today % 100 == 0:
                                self.logger.info(
                                    f"📚 [PAPER Learning Mode] {self.risk_manager.state.executed_trades_today} trades acumulados "
                                    f"(límite informativo: {max_daily_trades}) - DecisionSamples continuarán")

                market_data = await self.market_data.get_latest_data()
                if not market_data:
                    msg = "⚠️ No se pudieron obtener datos de mercado, reintentando..."
                    self.logger.warning(msg)
                    if self.config.TRADING_MODE == "LIVE":
                        await asyncio.sleep(10)
                        continue
                    continue

                if self.dashboard:
                    try:
                        dashboard_data = self._build_dashboard_payload(
                            market_data)
                        await self.dashboard.update_data(dashboard_data)
                    except Exception as e:
                        self.logger.debug(f"Error actualizando dashboard: {e}")

                price = market_data.get('price', 0)
                symbol = market_data.get('symbol', 'N/A')

                bot_state_snapshot = {
                    'daily_pnl': self.risk_manager.state.daily_pnl,
                    'daily_trades': self.risk_manager.state.executed_trades_today,
                    'consecutive_signals': getattr(self.strategy, 'consecutive_signals', 0),
                    'daily_pnl_normalized': self.risk_manager.state.daily_pnl / self.config.INITIAL_CAPITAL,
                    'daily_trades_normalized': self.risk_manager.state.executed_trades_today / 200.0
                }

                signal = await self.strategy.generate_signal(market_data, self.current_regime_info)
                strategy_signal = signal
                self.current_signal = signal

                original_signal = signal

                positions_count = self.position_manager.count_open_positions(self.current_positions)
                has_active_position = positions_count > 0
                
                if has_active_position:
                    self.logger.info(
                        f"🔒 Posición activa detectada ({positions_count}) "
                        "→ no se evalúa riesgo ni se abre nueva orden. Gestionando posición existente..."
                    )
                    
                    await self._check_open_positions(market_data)
                    
                    continue

                decision_sample = None
                if signal is None:
                    tick_decision = create_tick_decision_no_signal()
                    if self.decision_sampler and self.config.TRADING_MODE == "PAPER":
                        assert decision_sample is None, "DecisionSample duplicado en el mismo tick"
                        decision_sample = self.decision_sampler.create_decision_sample(
                            market_data=market_data,
                            strategy=self.strategy,
                            strategy_signal=None,
                            executed_action=tick_decision.executed_action,
                            regime_info=self.current_regime_info,
                            decision_outcome=tick_decision.decision_outcome,
                            reject_reason=tick_decision.reject_reason
                        )

                    if iteration_count % 10 == 0:
                        indicators = market_data.get('indicators', {})
                        self.logger.info(
                            f"🔍 Analizando {symbol} @ {price:.2f} | "
                            f"RSI: {indicators.get('rsi', 0):.1f} | "
                            f"EMA9: {indicators.get('fast_ma', 0):.2f} | "
                            f"EMA21: {indicators.get('slow_ma', 0):.2f} | "
                            f"Sin señal (condiciones no cumplidas)"
                        )
                else:
                    signal_action = (
                        original_signal.get("action", "").upper()
                        if isinstance(original_signal, dict) and original_signal.get("action")
                        else ExecutedAction.HOLD.value
                    )
                    if signal_action not in [ExecutedAction.BUY.value, ExecutedAction.SELL.value]:
                        signal_action = ExecutedAction.HOLD.value
                    
                    strategy_signal_normalized = signal_action if signal_action in [ExecutedAction.BUY.value, ExecutedAction.SELL.value] else "NONE"

                    tick_decision = create_tick_decision_no_signal()
                    if self.decision_sampler and self.config.TRADING_MODE == "PAPER":
                        assert decision_sample is None, "DecisionSample duplicado en el mismo tick"
                        strategy_signal_dict = {"action": strategy_signal_normalized} if strategy_signal_normalized != "NONE" else None
                        decision_sample = self.decision_sampler.create_decision_sample(
                            market_data=market_data,
                            strategy=self.strategy,
                            strategy_signal=strategy_signal_dict,
                            executed_action=tick_decision.executed_action,
                            regime_info=self.current_regime_info,
                            decision_outcome=tick_decision.decision_outcome,
                            reject_reason="awaiting validation"
                        )

                    self.logger.info(
                        f"🔔 Señal generada: {original_signal['action']} {symbol} @ {original_signal['price']:.2f} (Fuerza: {original_signal['strength']:.2%})")
                    
                    if self.decision_sampler and self.config.TRADING_MODE == "PAPER" and decision_sample is None:
                        strategy_signal_dict = {"action": signal_action}
                        decision_sample = self.decision_sampler.create_decision_sample(
                            market_data=market_data,
                            strategy=self.strategy,
                            strategy_signal=strategy_signal_dict,
                            executed_action=None,
                            regime_info=self.current_regime_info,
                            decision_outcome=None,
                            reject_reason="awaiting filters"
                        )

                if signal:
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

                    ml_decision = None
                    use_ml_filter = not self.mvp_mode and not is_debug and self.ml_filter is not None and self.ml_filter.is_model_available()

                    if use_ml_filter:
                        ml_decision = await self.ml_filter.filter_signal(
                            signal,
                            market_data,
                            self.current_regime_info,
                            bot_state_snapshot
                        )

                        if not ml_decision['approved']:
                            self.logger.info(
                                f"🚫 Señal rechazada por filtro ML: {ml_decision['reason']} (P(win)={ml_decision.get('probability', 0):.2%})")

                            rejection_detail = f"ML filter: {ml_decision['reason']} (P(win)={ml_decision.get('probability', 0):.2%})"
                            tick_decision = create_tick_decision_rejected(
                                signal_action,
                                "ml",
                                rejection_detail
                            )

                            if decision_sample:
                                decision_sample.executed_action = tick_decision.executed_action
                                decision_sample.decision_outcome = tick_decision.decision_outcome
                                decision_sample.reject_reason = tick_decision.reject_reason

                            if self.config.TRADING_MODE == "LIVE":
                                signal = None
                            else:
                                signal = None
                    elif is_debug and self.ml_filter is not None and self.ml_filter.is_model_available():
                        ml_decision = await self.ml_filter.filter_signal(
                            signal,
                            market_data,
                            self.current_regime_info,
                            bot_state_snapshot
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
                    
                    ml_v2_decision = None
                    use_ml_v2_filter = (
                        not self.mvp_mode and 
                        not is_debug and 
                        self.ml_v2_filter is not None and 
                        self.ml_v2_filter.is_model_available() and
                        signal is not None
                    )
                    
                    if use_ml_v2_filter:
                        ml_v2_decision = await self.ml_v2_filter.filter_signal(
                            signal,
                            market_data
                        )
                        
                        if not ml_v2_decision['approved']:
                            self.logger.info(
                                f"ML v2 Filter rechazado: {ml_v2_decision['reason']} | "
                                f"Score: {ml_v2_decision['ml_score']:.4f} | "
                                f"Percentil: {ml_v2_decision['percentile']:.1f}%"
                            )
                            
                            original_action = signal.get('action', 'UNKNOWN')
                            
                            rejection_detail = (
                                f"ML_FILTER: {ml_v2_decision['reason']} "
                                f"(score={ml_v2_decision['ml_score']:.4f}, "
                                f"percentile={ml_v2_decision['percentile']:.1f}%)"
                            )
                            tick_decision = create_tick_decision_rejected(
                                original_action,
                                "ml_filter",
                                rejection_detail
                            )
                            
                            if decision_sample:
                                decision_sample.executed_action = tick_decision.executed_action
                                decision_sample.decision_outcome = tick_decision.decision_outcome
                                decision_sample.reject_reason = tick_decision.reject_reason
                            
                            signal = None
                        else:
                            self.logger.debug(
                                f"ML v2 Filter aprobado | "
                                f"Score: {ml_v2_decision['ml_score']:.4f} | "
                                f"Percentil: {ml_v2_decision['percentile']:.1f}%"
                            )

                    if signal:

                        if self.mvp_mode:
                            is_paper_mvp = self.config.TRADING_MODE == "PAPER" and self.mvp_mode

                            if is_paper_mvp:
                                risk_valid = True
                                self._validate_trade_mvp(
                                    signal, self.current_positions)
                                max_daily_trades = self.current_parameters.get('max_daily_trades',
                                                                               self.config.PAPER_MAX_DAILY_TRADES if self.config.TRADING_MODE == "PAPER" else 5)
                                if self.risk_manager.state.executed_trades_today >= max_daily_trades:
                                    self.logger.info(
                                        f"📚 [PAPER+MVP] Trades ejecutados: {self.risk_manager.state.executed_trades_today}/{max_daily_trades} "
                                        f"(límite informativo, continuando para ML)")
                            else:
                                risk_valid = self._validate_trade_mvp(
                                    signal, self.current_positions)
                                if not risk_valid:
                                    self.logger.warning(
                                        "⚠️ Trade rechazado por límites básicos de MVP")
                        elif is_debug:
                            risk_valid, risk_outcome, risk_reason = self.risk_manager.validate_trade(
                                signal, self.current_positions)
                            if risk_valid:
                                self.logger.info(
                                    "🐛 [DEBUG] ✅ Gestor de riesgo aprobaría la operación")
                            else:
                                msg = ("🐛 [DEBUG] ⚠️ Gestor de riesgo rechazaría "
                                       f"la operación ({risk_outcome}), pero DEBUG permite continuar")
                                self.logger.warning(msg)
                            risk_valid = True
                            risk_outcome = None
                            risk_reason = None
                        else:
                            risk_valid, risk_outcome, risk_reason = self.risk_manager.validate_trade(
                                signal, self.current_positions)

                        is_paper_mvp = self.config.TRADING_MODE == "PAPER" and self.mvp_mode

                        if not risk_valid and not is_paper_mvp:
                            if risk_outcome and validate_decision_outcome(risk_outcome):
                                decision_outcome = risk_outcome
                            else:
                                decision_outcome, _ = normalize_rejection(
                                    "risk", risk_reason or "Risk manager: validation failed")

                            tick_decision = create_tick_decision_rejected(
                                signal_action,
                                "risk" if decision_outcome == DecisionOutcome.REJECTED_BY_RISK.value else "limits",
                                risk_reason or "Risk manager: validation failed"
                            )

                            self.logger.info(
                                f"🚫 Operación rechazada: {tick_decision.decision_outcome} - {tick_decision.reject_reason}")

                            if decision_sample:
                                decision_sample.executed_action = tick_decision.executed_action
                                decision_sample.decision_outcome = tick_decision.decision_outcome
                                decision_sample.reject_reason = tick_decision.reject_reason
                        elif not risk_valid and is_paper_mvp:
                            self.logger.warning(
                                f"⚠️ [PAPER+MVP] Risk manager advierte riesgo, pero continuando para ML "
                                f"(trades ejecutados: {self.risk_manager.state.executed_trades_today}, "
                                f"samples: {self.risk_manager.state.decision_samples_collected}, "
                                f"pnl: {self.risk_manager.state.daily_pnl:.2f})")
                            risk_valid = True

                        can_execute, execute_outcome, execute_reason = self.risk_manager.can_execute_order(
                            current_positions=self.current_positions
                        )

                        is_paper_mode = self.config.TRADING_MODE == "PAPER"
                        
                        if is_paper_mode and risk_valid:
                            should_execute = True
                        else:
                            should_execute = risk_valid and can_execute

                        if should_execute:
                            is_paper_mvp = self.config.TRADING_MODE == "PAPER" and self.mvp_mode

                            if decision_sample and decision_sample.decision_id:
                                signal['decision_id'] = decision_sample.decision_id
                                self.logger.debug(
                                    f"🔗 Propagando decision_id={decision_sample.decision_id} a signal")

                            if not is_paper_mvp:
                                now_time = datetime.now()
                                if self.last_trade_time is not None:
                                    elapsed_since_last_trade = (
                                        now_time - self.last_trade_time).total_seconds()
                                    if elapsed_since_last_trade < self.min_cooldown_seconds:
                                        if self.config.TRADING_MODE == "LIVE":
                                            self.logger.debug(
                                                f"⏳ Cooldown activo: {elapsed_since_last_trade:.1f}s < {self.min_cooldown_seconds}s")
                                            await asyncio.sleep(self.min_cooldown_seconds - elapsed_since_last_trade)

                            if self.mvp_mode:
                                self.logger.info(
                                    "🚀 [MVP] Ejecutando orden (prioridad: sample size)")
                            elif is_debug:
                                debug_risk_valid, _, _ = self.risk_manager.validate_trade(
                                    signal, self.current_positions)
                                if not debug_risk_valid:
                                    self.logger.warning(
                                        "🐛 [DEBUG] ⚠️ Ejecutando orden a pesar de validación de riesgo fallida (MODO DEBUG)")
                                msg = ("🐛 [DEBUG] ✅ Ejecutando orden "
                                       "(MODO DEBUG - filtros ignorados)")
                                self.logger.info(msg)
                            else:
                                self.logger.info(
                                    "✅ Riesgo validado y límites OK, ejecutando orden...")

                            order_result = await self.order_executor.execute_order(signal)
                        elif risk_valid and not can_execute and not is_paper_mode:
                            self.logger.info(
                                f"📚 DecisionSample se creará, pero orden real NO se ejecutará: {execute_reason}")

                            if execute_outcome == DecisionOutcome.NO_SIGNAL.value:
                                tick_decision = create_tick_decision_no_signal()
                            else:
                                tick_decision = create_tick_decision_rejected(
                                    signal_action,
                                    "limits",
                                    execute_reason or "Daily trade limits reached"
                                )

                            if decision_sample:
                                decision_sample.executed_action = tick_decision.executed_action
                                decision_sample.decision_outcome = tick_decision.decision_outcome
                                if tick_decision.decision_outcome == DecisionOutcome.NO_SIGNAL.value:
                                    decision_sample.reject_reason = execute_reason or "paper limits"
                                else:
                                    decision_sample.reject_reason = tick_decision.reject_reason

                            order_result = {
                                "success": False, "error": "Daily limits reached (DecisionSample created)"}
                        else:
                            if decision_sample:
                                if decision_sample.executed_action is None or decision_sample.decision_outcome is None:
                                    if 'tick_decision' in locals():
                                        decision_sample.executed_action = tick_decision.executed_action
                                        decision_sample.decision_outcome = tick_decision.decision_outcome
                                        decision_sample.reject_reason = tick_decision.reject_reason
                            
                            order_result = {"success": False,
                                            "error": "Risk validation failed"}

                        if order_result.get('success'):
                            self.last_trade_time = datetime.now()
                            position = order_result.get('position')
                            if position:
                                self.current_positions.append(position)

                                symbol_val = original_signal.get('symbol') if original_signal else 'N/A'
                                price_val = original_signal.get('price', 0) if original_signal else 0
                                self.logger.info(
                                    f"✅ [TRADE EJECUTADO] {signal_action} {symbol_val} @ {price_val:.2f} | "
                                    f"Trades ejecutados hoy: {self.risk_manager.state.executed_trades_today}")

                            tick_decision = create_tick_decision_executed(
                                signal_action)

                            if decision_sample:
                                decision_sample.executed_action = tick_decision.executed_action
                                decision_sample.decision_outcome = tick_decision.decision_outcome
                                decision_sample.reject_reason = tick_decision.reject_reason

                            if self.mvp_mode:
                                trade_num = self.total_trades_count + self.risk_manager.state.executed_trades_today
                                action = original_signal['action'] if original_signal else 'N/A'
                                symbol = original_signal['symbol'] if original_signal else 'N/A'
                                price = original_signal['price'] if original_signal else 0
                                size = original_signal['position_size'] if original_signal else 0
                                sl = original_signal['stop_loss'] if original_signal else 0
                                tp = original_signal['take_profit'] if original_signal else 0
                                msg = (f"🚀 [MVP] ✅ Trade #{trade_num}: "
                                       f"{action} {symbol} @ {price:.2f} "
                                       f"(Size: {size:.4f}, SL: {sl:.2f}, TP: {tp:.2f})")
                                self.logger.info(msg)
                            elif is_debug:
                                action = original_signal['action'] if original_signal else 'N/A'
                                symbol = original_signal['symbol'] if original_signal else 'N/A'
                                price = original_signal['price'] if original_signal else 0
                                size = original_signal['position_size'] if original_signal else 0
                                sl = original_signal['stop_loss'] if original_signal else 0
                                tp = original_signal['take_profit'] if original_signal else 0
                                msg = (f"🐛 [DEBUG] ✅ ORDEN EJECUTADA: {action} {symbol} "
                                       f"@ {price:.2f} (Size: {size:.4f}, "
                                       f"SL: {sl:.2f}, TP: {tp:.2f})")
                                self.logger.info(msg)
                            else:
                                if original_signal:
                                    self.logger.info(
                                        f"✅ {original_signal['action']} {original_signal['symbol']} @ {original_signal['price']} "
                                        f"(Fuerza: {original_signal['strength']:.2%}, Régimen: {original_signal.get('regime', 'unknown')})"
                                    )

                            if self.trade_recorder or self.mvp_mode:

                                if not self.trade_recorder and self.config.ENABLE_ML:
                                    from src.ml.trade_recorder import TradeRecorder
                                    self.trade_recorder = TradeRecorder()

                                if self.trade_recorder and position:
                                    self.position_market_data[position['id']] = {
                                        'market_data': market_data.copy(),
                                        'regime_info': self.current_regime_info.copy() if self.current_regime_info else {},
                                        'ml_decision': ml_decision,
                                        'bot_state': {
                                            'daily_pnl': self.risk_manager.state.daily_pnl,
                                            'daily_trades': self.risk_manager.state.executed_trades_today,
                                            'consecutive_signals': self.strategy.consecutive_signals,
                                        }
                                    }

                            await self.notifications.send_trade_notification(order_result)
                        else:
                            self.logger.error(
                                f"❌ Error ejecutando orden: {order_result.get('error', 'unknown')}")

                            execution_error = order_result.get(
                                'error', 'unknown')
                            tick_decision = create_tick_decision_rejected(
                                signal_action,
                                "execution",
                                f"Execution error: {execution_error}"
                            )

                            if decision_sample:
                                decision_sample.executed_action = tick_decision.executed_action
                                decision_sample.decision_outcome = tick_decision.decision_outcome
                                decision_sample.reject_reason = tick_decision.reject_reason

                if self.decision_sampler and self.trade_recorder and self.config.TRADING_MODE == "PAPER" and decision_sample:
                    should_record = True

                    final_executed_action = decision_sample.executed_action
                    final_decision_outcome = decision_sample.decision_outcome

                    if final_executed_action is None:
                        self.logger.warning(
                            f"⚠️ executed_action es None después del pipeline completo. "
                            f"strategy_signal={original_signal.get('action') if original_signal else None}. "
                            "Forzando HOLD para evitar contaminación del dataset.")
                        final_executed_action = ExecutedAction.HOLD.value
                    if not final_decision_outcome:
                        if original_signal is None:
                            final_decision_outcome = DecisionOutcome.NO_SIGNAL.value
                            decision_sample.reject_reason = None
                        else:
                            final_decision_outcome = DecisionOutcome.REJECTED_BY_RISK.value
                        decision_sample.decision_outcome = final_decision_outcome

                    is_valid, error = validate_decision_consistency(
                        final_executed_action,
                        final_decision_outcome,
                        decision_sample.strategy_signal
                    )
                    if not is_valid:
                        self.logger.warning(
                            f"⚠️ INCONSISTENCIA detectada en DecisionSample: {error}. "
                            f"Corrigiendo automáticamente...")
                        if final_executed_action == ExecutedAction.HOLD.value and final_decision_outcome == DecisionOutcome.EXECUTED.value:
                            final_decision_outcome = DecisionOutcome.NO_SIGNAL.value
                            decision_sample.decision_outcome = final_decision_outcome
                            decision_sample.reject_reason = None
                            self.logger.warning(
                                f"✅ Corregido: HOLD + EXECUTED → HOLD + NO_SIGNAL")
                        elif final_executed_action in [ExecutedAction.BUY.value, ExecutedAction.SELL.value]:
                            if final_decision_outcome != DecisionOutcome.EXECUTED.value:
                                final_decision_outcome = DecisionOutcome.EXECUTED.value
                                decision_sample.decision_outcome = final_decision_outcome
                                self.logger.warning(
                                    f"✅ Corregido: {final_executed_action} + {decision_sample.decision_outcome} → {final_executed_action} + EXECUTED")

                        is_valid_after, error_after = validate_decision_consistency(
                            final_executed_action,
                            final_decision_outcome,
                            decision_sample.strategy_signal
                        )
                        if not is_valid_after:
                            self.logger.error(
                                f"❌ ERROR CRÍTICO: No se pudo corregir inconsistencia: {error_after}. "
                                f"Sample NO se guardará para evitar corrupción del dataset.")
                            should_record = False

                    if final_decision_outcome == DecisionOutcome.NO_SIGNAL.value:
                        if not (self.config.TRADING_MODE == "PAPER" and decision_sample.reject_reason and 
                                ("paper limits" in str(decision_sample.reject_reason) or 
                                 "limits (paper only)" in str(decision_sample.reject_reason))):
                            decision_sample.reject_reason = None

                    decision_space_snapshot = decision_sample.decision_space.copy() if hasattr(decision_sample.decision_space, 'copy') else dict(decision_sample.decision_space)
                    
                    decision_sample.reason = self.decision_sampler._build_reason(
                        original_signal, decision_space_snapshot, final_executed_action,
                        final_decision_outcome, decision_sample.reject_reason
                    )

                    decision_sample.executed_action = final_executed_action
                    if final_executed_action in [ExecutedAction.BUY.value, ExecutedAction.SELL.value]:
                        self.logger.debug(
                            f"📊 [DECISION SAMPLE + TRADE EJECUTADO] {final_executed_action} | "
                            f"Outcome: {final_decision_outcome} | "
                            f"Trades ejecutados: {self.risk_manager.state.executed_trades_today} | "
                            f"Samples: {self.risk_manager.state.decision_samples_collected}")
                    else:
                        self.logger.debug(
                            f"📊 [DECISION SAMPLE] {final_executed_action} | "
                            f"Outcome: {final_decision_outcome} | "
                            f"Trades ejecutados: {self.risk_manager.state.executed_trades_today} | "
                            f"Samples: {self.risk_manager.state.decision_samples_collected}")

                    is_hold_sample = (
                        original_signal is None and
                        final_executed_action == "HOLD"
                    )

                    is_buy_sell_sample = final_executed_action in [
                        "BUY", "SELL"]

                    if is_hold_sample:
                        if not hasattr(self, '_hold_sample_counter'):
                            self._hold_sample_counter = 0
                        self._hold_sample_counter += 1

                        hold_downsample_rate = self.config.DECISION_HOLD_SAMPLE_RATE
                        if hold_downsample_rate > 1:
                            if self._hold_sample_counter % hold_downsample_rate != 0:
                                should_record = False
                                self.logger.debug(
                                    f"⏭️ HOLD sample #{self._hold_sample_counter} downsampled "
                                    f"(rate: 1/{hold_downsample_rate})")
                            else:
                                self.logger.debug(
                                    f"✅ HOLD sample #{self._hold_sample_counter} guardado "
                                    f"(rate: 1/{hold_downsample_rate})")

                    elif is_buy_sell_sample:
                        should_record = True
                        self.logger.debug(
                            f"✅ {final_executed_action} sample guardado (sin downsampling)")

                    if should_record:
                        assert decision_sample.executed_action in VALID_EXECUTED_ACTIONS, (
                            f"executed_action inválido antes de guardar: {decision_sample.executed_action}"
                        )
                        assert decision_sample.decision_outcome in VALID_DECISION_OUTCOMES, (
                            f"decision_outcome inválido antes de guardar: {decision_sample.decision_outcome}"
                        )
                        if decision_sample.decision_outcome == DecisionOutcome.EXECUTED.value:
                            assert decision_sample.executed_action in ["BUY", "SELL"], (
                                f"EXECUTED no puede tener HOLD: executed_action={decision_sample.executed_action}"
                            )

                        try:
                            self.trade_recorder.record_decision_sample(
                                decision_sample, self.decision_sampler)
                            self.risk_manager.state.decision_samples_collected += 1
                        except Exception as e:
                            self.logger.error(
                                f"❌ Error guardando DecisionSample: {e}. "
                                f"Sample perdido, pero continuando para no bloquear loop.")

                await self._check_open_positions(market_data)

                if self.dashboard:
                    try:
                        dashboard_payload = self._build_dashboard_payload(
                            market_data)
                        await self.dashboard.update_data(dashboard_payload)
                    except Exception as e:
                        self.logger.error(
                            f"❌ Error actualizando dashboard: {e}")

                sleep_time = 0.2 if self.config.TRADING_MODE == "PAPER" else 1.0
                await asyncio.sleep(sleep_time)

            except Exception as e:
                self.logger.error(f"❌ Error en bucle principal: {e}")
                sleep_time = 0.2 if self.config.TRADING_MODE == "PAPER" else 10
                await asyncio.sleep(sleep_time)

    async def _check_open_positions(self, market_data):
        """
        Verificar y gestionar posiciones abiertas con lógica AVANZADA:
        - Trailing stop
        - Break-even
        - Time-based stops
        - Cierre por fin de día
        """
        current_price = market_data.get('price', 0)
        self.last_market_data = market_data

        for position in [p for p in self.current_positions if p.get('status') != 'closed']:
            try:
                position_id = position.get('id', 'unknown')
                symbol = position.get('symbol', 'UNKNOWN')

                management_decision = await self.position_manager.manage_position(
                    position,
                    current_price,
                    market_data,
                    mvp_mode=self.mvp_mode,
                    executor=self.order_executor,
                    risk_manager=self.risk_manager,
                    positions_list=self.current_positions
                )

                if management_decision.get('closed', False):
                    pnl = management_decision.get('pnl', 0.0)

                    self.state_manager.save({
                        "equity": self.risk_manager.state.equity,
                        "daily_pnl": self.risk_manager.state.daily_pnl,
                        "trades_today": self.risk_manager.state.executed_trades_today,
                        "executed_trades_today": self.risk_manager.state.executed_trades_today,
                        "decision_samples_collected": self.risk_manager.state.decision_samples_collected,
                        "peak_equity": self.risk_manager.state.peak_equity,
                        "max_drawdown": self.risk_manager.state.max_drawdown,
                    })

                    self.logger.info(
                        f"✅ Posición cerrada por AdvancedPositionManager | "
                        f"PnL: {pnl:.2f}"
                    )
                    continue

                if not self.mvp_mode and management_decision.get('action') == 'update_stops':
                    new_stop_loss = management_decision.get('new_stop_loss')
                    if new_stop_loss:
                        position['stop_loss'] = new_stop_loss
                        self.logger.info(
                            f"🔄 Stop actualizado en {symbol}: "
                            f"Nuevo SL={new_stop_loss:.2f} - {management_decision.get('reason')}"
                        )

                should_close_mgmt = management_decision.get('should_close', False)
                if should_close_mgmt and not management_decision.get('closed', False):
                    self.logger.error(
                        f"❌ ORQUESTACIÓN ERROR: manage_position() retornó should_close=True pero closed=False "
                        f"para posición {position_id}. Esto indica que faltaron executor/risk_manager. "
                        f"La posición NO se cerró realmente y causará deadlock. "
                        f"Verificar que manage_position() siempre reciba executor y risk_manager."
                    )
                    continue

            except Exception as e:
                self.logger.error(
                    f"❌ Error gestionando posición {position.get('id')}: {e}")

    async def _close_all_positions(self):
        """Cerrar todas las posiciones abiertas"""
        current_price = None
        if hasattr(self, 'last_market_data') and self.last_market_data:
            current_price = self.last_market_data.get('price')
        
        for position in self.current_positions[:]:
            market_data = self.last_market_data if hasattr(self, 'last_market_data') and self.last_market_data else {}
            await self.position_manager.manage_position(
                position,
                current_price or position.get('entry_price', 0),
                market_data,
                mvp_mode=self.mvp_mode,
                executor=self.order_executor,
                risk_manager=self.risk_manager,
                positions_list=self.current_positions
            )

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

        max_dd = self.risk_manager.state.max_drawdown
        if max_dd is None:
            max_dd = 0.0

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

            total_wins = sum(wins) if wins else 0
            total_losses_abs = abs(sum(losses)) if losses else 1
            profit_factor_daily = total_wins / \
                total_losses_abs if total_losses_abs > 0 else None

            win_rate = win_rate_daily or 0
            loss_rate = 1 - win_rate
            if avg_win_daily is not None and avg_loss_daily is not None:
                expectancy_daily = (win_rate * avg_win_daily) + \
                    (loss_rate * avg_loss_daily)

        risk_multiplier = self.risk_manager.get_adaptive_risk_multiplier() if hasattr(
            self.risk_manager, 'get_adaptive_risk_multiplier') else 1.0

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
            'daily_trades': int(self.risk_manager.state.executed_trades_today or 0),
            'winning_trades_daily': int(winning_trades_daily),
            'losing_trades_daily': int(losing_trades_daily),
            'win_rate_daily': float(win_rate_daily) if win_rate_daily is not None else None,
            'win_rate_daily_percent': float(win_rate_daily * 100) if win_rate_daily is not None else None,
            'max_drawdown': float(max_dd),

            'avg_win_daily': float(avg_win_daily) if avg_win_daily is not None else None,
            'avg_loss_daily': float(avg_loss_daily) if avg_loss_daily is not None else None,
            'profit_factor_daily': float(profit_factor_daily) if profit_factor_daily is not None else None,
            'expectancy_daily': float(expectancy_daily) if expectancy_daily is not None else None,
            'largest_win_daily': float(largest_win_daily) if largest_win_daily is not None else None,
            'largest_loss_daily': float(largest_loss_daily) if largest_loss_daily is not None else None,

            'risk_multiplier': float(risk_multiplier),

            'historical': {
                **historical_metrics,
                'avg_win': avg_win_historical,
                'avg_loss': avg_loss_historical,
                'profit_factor': profit_factor_historical,
                'expectancy': expectancy_historical,
            },
        }

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

            change = self._safe_float(market_data.get('change'))
            change_percent = self._safe_float(
                market_data.get('change_percent'))

            if change is None:
                open_price = self._safe_float(market_data.get('open'))
                if open_price and open_price > 0:
                    change = price - open_price
                    change_percent = (change / open_price) * 100

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
                'data_source': data_source,
                'is_real_data': is_real_data,
            }

            if 'dataframe' in market_data:
                df = market_data.get('dataframe')
                if df is not None and hasattr(df, 'tail') and len(df) > 0:

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
                'rsi': self._safe_float(indicators.get('rsi')) or 50.0,
                'fast_ma': self._safe_float(indicators.get('fast_ma')) or price,
                'slow_ma': self._safe_float(indicators.get('slow_ma')) or price,
                'macd': self._safe_float(indicators.get('macd')) or 0.0,
            }

            if 'ohlc_history' not in market_snapshot or not market_snapshot['ohlc_history']:

                now = datetime.now()
                market_snapshot['ohlc_history'] = [{
                    'timestamp': now.isoformat(),
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': market_snapshot.get('volume', 0.0)
                }]

        current_signal_snapshot = None
        if self.current_signal:
            current_signal_snapshot = {
                'action': self.current_signal.get('action'),
                'strength': self._safe_float(self.current_signal.get('strength')),
                'reason': self.current_signal.get('reason'),
                'stop_loss': self._safe_float(self.current_signal.get('stop_loss')),
                'take_profit': self._safe_float(self.current_signal.get('take_profit')),
            }

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

        regime_info = None
        if hasattr(self, 'current_regime_info') and self.current_regime_info:
            regime_info = {
                'regime': self.current_regime_info.get('regime', 'unknown'),
                'volatility': self._safe_float(self.current_regime_info.get('volatility')),
                'trend': self.current_regime_info.get('trend', 'unknown'),
            }

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
            'orders': orders_executed,
            'regime': regime_info,
            'operation_mode': operation_mode,
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

            if self.config.TRADING_MODE == 'LIVE':

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

                if self.config.MARKET == 'CRYPTO' and not self.config.BINANCE_API_KEY:
                    self.logger.info(
                        "ℹ️ Modo PAPER: Sin API Key de Binance (usando datos simulados)")
                if self.config.MARKET == 'STOCK' and not self.config.ALPACA_API_KEY:
                    self.logger.info(
                        "ℹ️ Modo PAPER: Sin API Key de Alpaca (usando datos simulados)")

            if self.config.RISK_PER_TRADE <= 0 or self.config.RISK_PER_TRADE > 0.1:
                self.logger.error(
                    "❌ Riesgo por trade debe estar entre 0 y 0.1 (10 porciento)")
                return False

            return True

        except Exception as e:
            self.logger.error(f"❌ Error validando configuración: {e}")
            return False

    def _validate_trade_mvp(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """
        Validación simplificada de riesgo para modo MVP.
        En PAPER+MVP: solo loguea advertencias, nunca bloquea.
        En otros modos: puede bloquear si es crítico.
        """
        try:
            is_paper_mvp = self.config.TRADING_MODE == "PAPER" and self.mvp_mode

            max_positions_mvp = max(self.config.MAX_POSITIONS, 15)
            positions_count = self.position_manager.count_open_positions(current_positions)
            if positions_count >= max_positions_mvp:
                if is_paper_mvp:
                    self.logger.info(
                        f"📚 [PAPER+MVP] Posiciones: {positions_count}/{max_positions_mvp} "
                        f"(continuando para ML)")
                else:
                    self.logger.warning(
                        f"⚠️ [MVP] Máximo de posiciones simultáneas alcanzado: "
                        f"{positions_count}/{max_positions_mvp}")
                    return False

            total_exposure = sum(
                (p.get('size', 0) * p.get('entry_price', 0))
                for p in current_positions
            )
            new_exposure = signal.get(
                'position_size', 0) * signal.get('price', 0)
            max_exposure = self.config.INITIAL_CAPITAL * 0.8
            if total_exposure + new_exposure > max_exposure:
                if is_paper_mvp:
                    self.logger.info(
                        f"📚 [PAPER+MVP] Exposición: {total_exposure + new_exposure:.2f}/{max_exposure:.2f} "
                        f"(continuando para ML)")
                else:
                    self.logger.warning(
                        f"⚠️ [MVP] Exposición máxima superada: "
                        f"{total_exposure + new_exposure:.2f} / {max_exposure:.2f}")
                    return False

            return True
        except Exception as e:
            self.logger.error(f"❌ Error en validación MVP: {e}")
            is_paper_mvp = self.config.TRADING_MODE == "PAPER" and self.mvp_mode
            return False if not is_paper_mvp else True

    def _is_trading_time(self) -> bool:
        """Verificar si es horario de trading"""
        if self.config.MARKET == 'CRYPTO':
            return True

        current_hour = datetime.now().hour
        return self.config.TRADING_START_HOUR <= current_hour < self.config.TRADING_END_HOUR

    async def _emergency_shutdown(self):
        """Cierre de emergencia del bot"""
        self.logger.critical("🚨 Ejecutando cierre de emergencia...")

        try:

            await self._close_all_positions()

            await self.notifications.send_emergency_notification("Bot detenido por error crítico")

        except Exception as e:
            self.logger.error(f"❌ Error en cierre de emergencia: {e}")
        finally:
            self.is_running = False

    def _signal_handler(self, signum, frame):
        """Manejador de señales del sistema"""
        self.logger.info(f"📡 Señal recibida: {signum}")
        asyncio.create_task(self.stop())

    def _validate_decision_system(self):
        """
        Validación final obligatoria del sistema de decisiones.
        Verifica que decision_outcome y executed_action sean consistentes.
        Si falla → log ERROR y bloquea ejecución en PAPER.
        """
        try:
            self.logger.info("🔍 Validando sistema de decisiones...")

            from src.utils.decision_constants import (
                VALID_DECISION_OUTCOMES,
                VALID_EXECUTED_ACTIONS,
                validate_decision_consistency
            )

            if not VALID_DECISION_OUTCOMES:
                raise ValueError("VALID_DECISION_OUTCOMES está vacío")

            if not VALID_EXECUTED_ACTIONS:
                raise ValueError("VALID_EXECUTED_ACTIONS está vacío")

            if self.config.TRADING_MODE == "PAPER":
                if not self.decision_sampler:
                    raise ValueError(
                        "DecisionSampler debe estar activo en modo PAPER")

                if not hasattr(self.decision_sampler, 'to_dict'):
                    raise ValueError(
                        "DecisionSampler debe implementar to_dict()")

            if self.config.TRADING_MODE == "PAPER":
                if not self.trade_recorder:
                    self.logger.warning(
                        "⚠️ TradeRecorder no inicializado en PAPER")

            self.logger.info(
                "✅ Validación del sistema de decisiones completada")

        except Exception as e:
            error_msg = f"❌ ERROR CRÍTICO en validación del sistema de decisiones: {e}"
            self.logger.error(error_msg)

            if self.config.TRADING_MODE == "PAPER":
                self.logger.error(
                    "🚨 BLOQUEANDO ejecución en PAPER debido a error de validación")
                raise ValueError(error_msg)
            else:
                self.logger.warning(
                    "⚠️ Continuando en LIVE a pesar del error de validación")


async def main():
    """Función principal"""
    bot = TradingBot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n🛑 Interrupción del usuario")
        bot.logger.info("🛑 Guardando estado antes de salir...")

        bot.state_manager.save({
            "equity": bot.risk_manager.state.equity,
            "daily_pnl": bot.risk_manager.state.daily_pnl,
            "trades_today": bot.risk_manager.state.executed_trades_today,
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
