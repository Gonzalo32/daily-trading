"""
Estrategia de trading automatizada SELECTIVA - ALTA PROBABILIDAD
Objetivo: Generar POCAS señales de ALTA calidad.
Prioridad: Calidad sobre cantidad - solo operar en condiciones óptimas.

Condiciones estrictas:
- BUY: EMA rápida > EMA lenta + RSI < 35
- SELL: EMA rápida < EMA lenta + RSI > 65

Filtros estrictos:
- NO operar en zonas laterales (rango de precios)
- NO operar en velas de bajo volumen
- Solo señales de alta probabilidad
"""

from datetime import datetime
from typing import Dict, Optional, Any
import pandas as pd

from config import Config
from src.utils.logging_setup import setup_logging
from src.strategy.dynamic_parameters import DynamicParameterManager


class TradingStrategy:
    """
    Estrategia de trading SELECTIVA - ALTA PROBABILIDAD:
    - Genera POCAS señales de ALTA calidad
    - Filtros estrictos (volumen, zonas laterales, condiciones técnicas)
    - Objetivo: Solo operar cuando las condiciones son óptimas
    - Prioridad: Calidad sobre cantidad
    """

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(
            __name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)

        # Gestor de parámetros dinámicos
        self.param_manager = DynamicParameterManager(config)

        # Estado de la estrategia
        self.last_signal: Optional[Dict[str, Any]] = None
        self.consecutive_signals: int = 0

        # Parámetros actuales (adaptados según régimen)
        self.current_params: Dict[str, Any] = {}

        # Historial para detección de zonas laterales y filtros de volumen
        self.recent_volumes = []
        self.recent_prices = []
        self.recent_ma_diffs = []  # Diferencias entre fast_ma y slow_ma para detectar laterales
        # ATR para detectar volatilidad baja (laterales)
        self.recent_atr_values = []

    # ======================================================
    # 🔧 ADAPTACIÓN DE PARÁMETROS
    # ======================================================
    def update_parameters_for_regime(self, regime_info: Dict[str, Any]):
        """
        Actualiza los parámetros de la estrategia según el régimen de mercado

        Args:
            regime_info: Información del régimen (regime, confidence, metrics)
        """
        try:
            self.current_params = self.param_manager.adapt_parameters(
                regime_info)
            self.logger.info(
                f"🔧 Parámetros actualizados para régimen: {regime_info.get('regime')} "
                f"(confianza: {regime_info.get('confidence', 0):.2%})"
            )
        except Exception as e:
            self.logger.error(f"❌ Error actualizando parámetros: {e}")

    def get_current_parameters(self) -> Dict[str, Any]:
        """Retorna los parámetros actuales adaptados"""
        return self.current_params if self.current_params else self.param_manager.get_current_parameters()

    # ======================================================
    # 🎯 GENERACIÓN DE SEÑALES
    # ======================================================

    async def generate_signal(self, market_data: Dict[str, Any], regime_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Genera señal de compra o venta según indicadores técnicos simplificados

        Args:
            market_data: Datos de mercado con precio, volumen, indicadores
            regime_info: Información del régimen de mercado (opcional, no usado en versión simplificada)

        Returns:
            Señal con action, precio, stop_loss, take_profit, etc.
        """
        try:
            is_debug = self.config.ENABLE_DEBUG_STRATEGY

            if is_debug:
                self.logger.info("🐛 [DEBUG] Iniciando generación de señal...")

            if not market_data or "indicators" not in market_data:
                if is_debug:
                    self.logger.warning(
                        "🐛 [DEBUG] Rechazado: market_data o indicators faltantes")
                return None

            indicators = market_data["indicators"]
            price = market_data["price"]

            # Si faltan indicadores, usar valores por defecto o fallback
            required = ["fast_ma", "slow_ma", "rsi"]
            missing = [k for k in required if k not in indicators]
            if missing:
                if is_debug:
                    self.logger.warning(
                        f"🐛 [DEBUG] Indicadores faltantes: {missing}, usando fallback")
                # Usar precio como fallback para MAs y RSI neutral
                indicators.setdefault("fast_ma", price)
                indicators.setdefault("slow_ma", price)
                indicators.setdefault("rsi", 50)  # RSI neutral
                self.logger.warning(
                    f"⚠️ Indicadores faltantes ({missing}), usando valores por defecto")

            if is_debug:
                self.logger.info(
                    f"🐛 [DEBUG] Indicadores disponibles - "
                    f"EMA9: {indicators.get('fast_ma', 0):.2f}, "
                    f"EMA21: {indicators.get('slow_ma', 0):.2f}, "
                    f"RSI: {indicators.get('rsi', 0):.2f}"
                )

            # Análisis selectivo (solo genera señal si se cumplen condiciones estrictas)
            signal = self._analyze_indicators(indicators, price)
            if not signal:
                # No se cumplen las condiciones estrictas, no generar señal
                if is_debug:
                    fast = indicators.get('fast_ma', price)
                    slow = indicators.get('slow_ma', price)
                    rsi = indicators.get('rsi', 50)
                    ema_diff_pct = ((fast - slow) / slow *
                                    100) if slow > 0 else 0
                    self.logger.debug(
                        f"🐛 [DEBUG] No se cumplen condiciones estrictas - "
                        f"EMA diff: {ema_diff_pct:.4f}%, RSI: {rsi:.2f} "
                        f"(BUY requiere: EMA rápida > EMA lenta + RSI < 35, "
                        f"SELL requiere: EMA rápida < EMA lenta + RSI > 65)"
                    )
                return None

            if is_debug:
                self.logger.info(
                    f"🐛 [DEBUG] ✅ Señal detectada: {signal['action']} @ {signal['price']:.2f} - "
                    f"Razón: {signal.get('reason', 'N/A')}"
                )

            # Actualizar historial para detección de zonas laterales
            self._update_market_history(market_data)

            # Aplicar filtros estrictos (volumen, zonas laterales, horario)
            filter_result = self._apply_filters(signal, market_data)
            if not filter_result:
                # Señal rechazada por filtros estrictos
                if is_debug:
                    self.logger.debug(
                        "🐛 [DEBUG] Señal rechazada por filtros estrictos")
                return None
            else:
                if is_debug:
                    self.logger.info(
                        "🐛 [DEBUG] ✅ Todos los filtros estrictos pasados")

            # Calcular tamaño de posición simple (solo por riesgo)
            position_size = self._calculate_position_size(signal)
            if position_size <= 0:
                if is_debug:
                    self.logger.warning(
                        f"🐛 [DEBUG] Rechazado: Tamaño de posición insuficiente ({position_size})")
                return None

            if is_debug:
                self.logger.info(
                    f"🐛 [DEBUG] Tamaño de posición calculado: {position_size:.4f}")

            # Completar datos de la señal
            signal.update({
                "position_size": position_size,
                "timestamp": market_data["timestamp"],
                "symbol": market_data["symbol"],
            })

            self.last_signal = signal
            if self.last_signal and self.last_signal["action"] == signal["action"]:
                self.consecutive_signals += 1
            else:
                self.consecutive_signals = 1

            if is_debug:
                self.logger.info(
                    f"🐛 [DEBUG] ✅ Señal FINAL aprobada: {signal['action']} {signal['symbol']} @ {price:.2f} "
                    f"(Size: {position_size:.4f}, SL: {signal['stop_loss']:.2f}, TP: {signal['take_profit']:.2f})"
                )
            else:
                self.logger.info(
                    f"✨ Señal generada: {signal['action']} {signal['symbol']} @ {price:.2f}"
                )

            return signal

        except Exception as e:
            self.logger.exception(f"❌ Error generando señal: {e}")
            return None

    # ======================================================
    # ⚙️ ANÁLISIS DE INDICADORES (SELECTIVO - ALTA PROBABILIDAD)
    # ======================================================
    def _analyze_indicators(self, indicators: Dict[str, float], price: float) -> Optional[Dict[str, Any]]:
        """
        Evalúa los indicadores técnicos para generar señal SOLO en condiciones óptimas

        Condiciones estrictas:
        - BUY: EMA rápida > EMA lenta + RSI < 35
        - SELL: EMA rápida < EMA lenta + RSI > 65

        Si no se cumplen estas condiciones, NO genera señal (None)
        """
        try:
            fast = indicators.get("fast_ma", price)
            slow = indicators.get("slow_ma", price)
            rsi = indicators.get("rsi", 50)

            if any(pd.isna([fast, slow, rsi])):
                # Si hay datos faltantes, NO generar señal
                self.logger.warning(
                    "⚠️ Indicadores con valores NaN, no se genera señal")
                return None

            # Usar valores fijos del config
            stop_loss_pct = self.config.STOP_LOSS_PCT
            take_profit_ratio = self.config.TAKE_PROFIT_RATIO

            # ============================================
            # CONDICIÓN ESTRICTA: BUY
            # EMA rápida > EMA lenta + RSI < 35
            # ============================================
            if fast > slow and rsi < 35:
                return {
                    "action": "BUY",
                    "price": price,
                    "strength": 0.9,  # Alta probabilidad
                    "reason": f"ALTA PROBABILIDAD: EMA rápida > EMA lenta + RSI < 35 (RSI actual: {rsi:.2f})",
                    "stop_loss": round(price * (1 - stop_loss_pct), 2),
                    "take_profit": round(price * (1 + stop_loss_pct * take_profit_ratio), 2),
                }

            # ============================================
            # CONDICIÓN ESTRICTA: SELL
            # EMA rápida < EMA lenta + RSI > 65
            # ============================================
            if fast < slow and rsi > 65:
                return {
                    "action": "SELL",
                    "price": price,
                    "strength": 0.9,  # Alta probabilidad
                    "reason": f"ALTA PROBABILIDAD: EMA rápida < EMA lenta + RSI > 65 (RSI actual: {rsi:.2f})",
                    "stop_loss": round(price * (1 + stop_loss_pct), 2),
                    "take_profit": round(price * (1 - stop_loss_pct * take_profit_ratio), 2),
                }

            # Si no se cumplen las condiciones estrictas, NO generar señal
            return None

        except Exception as e:
            self.logger.exception(f"❌ Error analizando indicadores: {e}")
            return None

    def _is_lateral_market(self, market_data: Dict[str, Any]) -> bool:
        """
        Detecta si el mercado está en una zona lateral (rango de precios)

        Criterios:
        - Las EMAs están muy cerca (diferencia < 0.3%)
        - ATR bajo (volatilidad reducida)
        - Precios recientes en rango estrecho
        """
        try:
            indicators = market_data.get("indicators", {})
            price = market_data.get("price", 0)

            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            atr = indicators.get("atr", 0)

            # Calcular diferencia porcentual entre EMAs
            if slow_ma > 0:
                ma_diff_pct = abs(fast_ma - slow_ma) / slow_ma * 100
            else:
                ma_diff_pct = 0

            # Criterio 1: EMAs muy cerca (zona lateral)
            # Si la diferencia es menor al 0.3%, probablemente es lateral
            if ma_diff_pct < 0.15:
                self.logger.debug(
                    f"🔍 Zona lateral detectada: EMAs muy cerca (diff: {ma_diff_pct:.4f}%)")
                return True

            # Criterio 2: ATR bajo relativo al precio (baja volatilidad = lateral)
            if price > 0:
                atr_pct = (atr / price) * 100
                # Si ATR es menor al 0.5% del precio, es baja volatilidad
                if atr_pct < 0.5:
                    # Verificar si el ATR está en el percentil bajo del historial
                    if len(self.recent_atr_values) >= 10:
                        sorted_atr = sorted(self.recent_atr_values)
                        atr_percentile_25 = sorted_atr[int(
                            len(sorted_atr) * 0.25)]
                        if atr < atr_percentile_25:
                            self.logger.debug(
                                f"🔍 Zona lateral detectada: ATR bajo ({atr_pct:.4f}%)")
                            return True

            # Criterio 3: Precios recientes en rango estrecho
            if len(self.recent_prices) >= 20:
                recent_prices = self.recent_prices[-20:]
                price_range = max(recent_prices) - min(recent_prices)
                avg_price = sum(recent_prices) / len(recent_prices)
                if avg_price > 0:
                    range_pct = (price_range / avg_price) * 100
                    # Si el rango de precios es menor al 1%, es lateral
                    if range_pct < 1.0:
                        self.logger.debug(
                            f"🔍 Zona lateral detectada: Rango de precios estrecho ({range_pct:.4f}%)")
                        return True

            return False

        except Exception as e:
            self.logger.exception(f"❌ Error detectando zona lateral: {e}")
            # En caso de error, asumir que NO es lateral (más conservador)
            return False

    # ======================================================
    # 🧮 CÁLCULOS AUXILIARES
    # ======================================================

    def _update_market_history(self, market_data: Dict[str, Any]):
        """Actualiza el historial de mercado para detección de zonas laterales"""
        try:
            price = market_data.get("price", 0)
            volume = market_data.get("volume", 0)
            indicators = market_data.get("indicators", {})
            atr = indicators.get("atr", 0)
            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)

            # Actualizar historiales
            self.recent_prices.append(price)
            self.recent_volumes.append(volume)
            self.recent_atr_values.append(atr)

            if slow_ma > 0:
                ma_diff_pct = abs(fast_ma - slow_ma) / slow_ma * 100
                self.recent_ma_diffs.append(ma_diff_pct)

            # Limitar historial a 100 valores
            max_history = 100
            for history_list in [self.recent_prices, self.recent_volumes,
                                 self.recent_atr_values, self.recent_ma_diffs]:
                if len(history_list) > max_history:
                    history_list.pop(0)

        except Exception as e:
            self.logger.exception(f"❌ Error actualizando historial: {e}")

    def _apply_filters(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """
        Filtra señales con condiciones ESTRICTAS

        Filtros:
        1. Volumen mínimo (rechazar velas de bajo volumen)
        2. Zonas laterales (NO operar en rangos)
        3. Horario (solo para acciones)
        4. Repeticiones excesivas
        """
        try:
            is_debug = self.config.ENABLE_DEBUG_STRATEGY

            # ============================================
            # FILTRO 1: Volumen mínimo (ESTRICTO)
            # ============================================
            volume = market_data.get("volume", 0)

            # Calcular umbral de volumen basado en promedio reciente
            if len(self.recent_volumes) >= 20:
                # Usar percentil 50 (mediana) como umbral mínimo
                sorted_volumes = sorted(self.recent_volumes)
                volume_median = sorted_volumes[len(sorted_volumes) // 2]
                min_volume = volume_median * 0.7  # Al menos 70% de la mediana
            else:
                # Si no hay suficiente historial, usar un umbral fijo conservador
                min_volume = volume * 0.5 if volume > 0 else 100

            if volume < min_volume:
                if is_debug:
                    self.logger.debug(
                        f"🐛 [DEBUG] Filtro VOLUMEN: Volumen insuficiente "
                        f"({volume:.2f} < {min_volume:.2f})"
                    )
                self.logger.info(
                    f"❌ Señal rechazada: Volumen bajo ({volume:.2f} < {min_volume:.2f})")
                return False

            # ============================================
            # FILTRO 2: Zonas laterales (NO operar)
            # ============================================
            if self._is_lateral_market(market_data):
                if is_debug:
                    self.logger.debug(
                        "🐛 [DEBUG] Filtro LATERAL: Mercado en zona lateral")
                self.logger.info(
                    "❌ Señal rechazada: Mercado en zona lateral (no operar)")
                return False

            # ============================================
            # FILTRO 3: Horario (solo para acciones)
            # ============================================
            if self.config.MARKET == "STOCK":
                hour = market_data.get("timestamp", datetime.now()).hour
                if not (self.config.TRADING_START_HOUR <= hour < self.config.TRADING_END_HOUR):
                    if is_debug:
                        self.logger.debug(
                            f"🐛 [DEBUG] Filtro HORARIO: Fuera de horario de trading "
                            f"(Hora: {hour}, Permitido: {self.config.TRADING_START_HOUR}-{self.config.TRADING_END_HOUR})"
                        )
                    return False

            # ============================================
            # FILTRO 4: Evitar repeticiones excesivas
            # ============================================
            max_consecutive = 3  # Máximo 3 señales consecutivas del mismo tipo

            if (
                self.last_signal
                and self.last_signal["action"] == signal["action"]
                and self.consecutive_signals >= max_consecutive
            ):
                if is_debug:
                    self.logger.debug(
                        f"🐛 [DEBUG] Filtro REPETICIÓN: Señales consecutivas "
                        f"({self.consecutive_signals} >= {max_consecutive}) del mismo tipo ({signal['action']})"
                    )
                self.logger.info(
                    f"❌ Señal rechazada: Demasiadas señales consecutivas ({self.consecutive_signals})")
                return False

            if is_debug:
                self.logger.info(
                    "🐛 [DEBUG] ✅ Todos los filtros estrictos pasados")

            return True

        except Exception as e:
            self.logger.exception(f"❌ Error aplicando filtros: {e}")
            # En caso de error, rechazar (más conservador)
            return False

    def _calculate_position_size(self, signal: Dict[str, Any]) -> float:
        """
        Calcula el tamaño de posición basado solo en riesgo (versión simplificada)
        """
        try:
            base_capital = self.config.INITIAL_CAPITAL
            risk_per_trade = self.config.RISK_PER_TRADE

            risk_amount = base_capital * risk_per_trade
            risk_per_unit = abs(signal["price"] - signal["stop_loss"])

            if risk_per_unit == 0:
                return 0.0

            # Tamaño base según riesgo (sin ajustes por fuerza)
            qty = risk_amount / risk_per_unit

            # Límite máximo de exposición (10% del capital)
            max_position_value = base_capital * 0.1
            max_qty = max_position_value / signal["price"]

            # Tomar el menor
            final_qty = min(qty, max_qty)

            return round(final_qty, 2)

        except Exception as e:
            self.logger.exception(f"❌ Error calculando posición: {e}")
            return 0.0

    # ======================================================
    # 📊 UTILIDADES
    # ======================================================
    def get_strategy_info(self) -> Dict[str, Any]:
        """Retorna configuración y último estado"""
        return {
            "name": "EMA + RSI Selectiva (Alta Probabilidad)",
            "description": "Estrategia selectiva que solo genera señales en condiciones óptimas: BUY (EMA rápida > EMA lenta + RSI < 35), SELL (EMA rápida < EMA lenta + RSI > 65). Filtros: NO operar en zonas laterales, NO operar en velas de bajo volumen.",
            "parameters": {
                "fast_ma_period": self.config.FAST_MA_PERIOD,
                "slow_ma_period": self.config.SLOW_MA_PERIOD,
                "rsi_period": self.config.RSI_PERIOD,
                "rsi_buy_threshold": 35,
                "rsi_sell_threshold": 65,
                "stop_loss_pct": self.config.STOP_LOSS_PCT,
                "take_profit_ratio": self.config.TAKE_PROFIT_RATIO,
                "filters": {
                    "lateral_market_detection": True,
                    "volume_filter": True,
                    "max_consecutive_signals": 3,
                }
            },
            "last_signal": self.last_signal,
            "consecutive_signals": self.consecutive_signals,
        }

    def reset_strategy(self):
        """Reinicia el estado interno de la estrategia"""
        self.last_signal = None
        self.consecutive_signals = 0
        self.logger.info("🔄 Estrategia reiniciada")
