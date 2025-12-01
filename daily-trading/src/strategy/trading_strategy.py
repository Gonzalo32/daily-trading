"""
Estrategia de trading automatizada EXTREMADAMENTE PERMISIVA
Objetivo: Operar TODOS los días, incluso con señales mediocres.
Prioridad: Disparar de más a disparar de menos.

Estrategia en cascada (4 niveles):
1. Señal FUERTE: EMA + RSI extremo (RSI < 45 o > 55)
2. Señal MEDIA: Solo EMA (cualquier diferencia > 0.1%)
3. Señal DÉBIL: Solo RSI (RSI < 50 = BUY, RSI > 50 = SELL)
4. FALLBACK: Siempre genera señal exploratoria si no hay ninguna

Filtros mínimos: Solo horario de acciones y repeticiones extremas (20+)
"""

from datetime import datetime
from typing import Dict, Optional, Any
import pandas as pd

from config import Config
from src.utils.logging_setup import setup_logging
from src.strategy.dynamic_parameters import DynamicParameterManager


class TradingStrategy:
    """
    Estrategia de trading EXTREMADAMENTE PERMISIVA:
    - SIEMPRE genera señales (4 niveles de calidad)
    - Filtros mínimos (solo horario y repeticiones extremas)
    - Objetivo: Operar TODOS los días, priorizar sample size
    - Preferir disparar de más a disparar de menos
    """

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(__name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)

        # Gestor de parámetros dinámicos
        self.param_manager = DynamicParameterManager(config)
        
        # Estado de la estrategia
        self.last_signal: Optional[Dict[str, Any]] = None
        self.consecutive_signals: int = 0
        
        # Parámetros actuales (adaptados según régimen)
        self.current_params: Dict[str, Any] = {}
        
        # Historial para umbrales dinámicos (ampliado para mejor adaptación)
        self.recent_volumes = []
        self.recent_volatilities = []
        self.recent_strengths = []
        self.recent_rsi_values = []
        self.recent_ma_diffs = []  # Diferencias entre fast_ma y slow_ma
        self.recent_macd_values = []
        self.recent_prices = []

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
            self.current_params = self.param_manager.adapt_parameters(regime_info)
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
    def _calculate_dynamic_thresholds(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calcula umbrales dinámicos basados completamente en condiciones actuales del mercado"""
        try:
            volume = market_data.get("volume", 0)
            price = market_data.get("price", 1)
            indicators = market_data.get("indicators", {})
            atr = indicators.get("atr", 0)
            rsi = indicators.get("rsi", 50)
            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            macd = indicators.get("macd", 0)
            
            # Calcular métricas actuales
            volatility = (atr / price) if price > 0 else 0
            ma_diff_pct = abs(fast_ma - slow_ma) / slow_ma * 100 if slow_ma > 0 else 0
            
            # Mantener historial ampliado (últimos 100 valores para mejor estadística)
            self.recent_volumes.append(volume)
            self.recent_volatilities.append(volatility)
            self.recent_rsi_values.append(rsi)
            self.recent_ma_diffs.append(ma_diff_pct)
            self.recent_macd_values.append(abs(macd))
            self.recent_prices.append(price)
            
            # Limitar historial a 100 valores
            max_history = 100
            for history_list in [self.recent_volumes, self.recent_volatilities, self.recent_rsi_values,
                                self.recent_ma_diffs, self.recent_macd_values, self.recent_prices]:
                if len(history_list) > max_history:
                    history_list.pop(0)
            
            # Calcular umbrales basados en estadísticas reales del mercado actual
            # Mínimo necesario: 5 valores para tener alguna estadística
            min_samples = 5
            
            if len(self.recent_volumes) >= min_samples:
                # VOLUMEN: Usar percentil 25 de los volúmenes recientes como mínimo
                sorted_volumes = sorted(self.recent_volumes)
                volume_percentile_25 = sorted_volumes[int(len(sorted_volumes) * 0.25)]
                min_volume = max(volume * 0.1, volume_percentile_25 * 0.5)  # Al menos 10% del volumen actual o 50% del percentil 25
            else:
                # Si no hay suficientes datos, usar el volumen actual como referencia
                min_volume = volume * 0.2 if volume > 0 else 100
            
            if len(self.recent_volatilities) >= min_samples:
                # VOLATILIDAD: Usar percentil 75 como máximo permitido
                sorted_volatilities = sorted(self.recent_volatilities)
                volatility_percentile_75 = sorted_volatilities[int(len(sorted_volatilities) * 0.75)]
                max_volatility = volatility_percentile_75 * 1.2  # 20% más que el percentil 75
            else:
                # Si no hay suficientes datos, usar la volatilidad actual como referencia
                max_volatility = volatility * 1.5 if volatility > 0 else 0.05
            
            if len(self.recent_rsi_values) >= min_samples:
                # RSI: Calcular umbrales basados en la distribución actual de RSI
                sorted_rsi = sorted(self.recent_rsi_values)
                rsi_median = sorted_rsi[len(sorted_rsi) // 2]
                rsi_std = pd.Series(self.recent_rsi_values).std()
                
                # Umbrales adaptativos: usar mediana ± desviación estándar ajustada
                rsi_overbought = min(95, max(70, rsi_median + rsi_std * 1.5))
                rsi_oversold = max(5, min(30, rsi_median - rsi_std * 1.5))
            else:
                # Si no hay suficientes datos, usar RSI actual como referencia
                rsi_overbought = min(95, rsi + 15) if rsi < 80 else 85
                rsi_oversold = max(5, rsi - 15) if rsi > 20 else 15
            
            if len(self.recent_ma_diffs) >= min_samples and len(self.recent_macd_values) >= min_samples:
                # FUERZA: Calcular basado en la distribución actual de diferencias de MA y MACD
                sorted_ma_diffs = sorted(self.recent_ma_diffs)
                ma_diff_percentile_50 = sorted_ma_diffs[int(len(sorted_ma_diffs) * 0.5)]
                
                sorted_macd = sorted(self.recent_macd_values)
                macd_percentile_50 = sorted_macd[int(len(sorted_macd) * 0.5)]
                
                # Fuerza mínima basada en la mediana de las señales históricas
                # Normalizar a un rango 0-1
                base_strength = (ma_diff_percentile_50 * 0.4 + (macd_percentile_50 / (macd_percentile_50 + 1)) * 0.6) / 100
                min_strength = max(0.05, min(0.3, base_strength * 0.8))  # 80% de la fuerza mediana
            else:
                # Si no hay suficientes datos, usar valores actuales como referencia
                current_strength_estimate = (ma_diff_pct * 0.4 + (abs(macd) / (abs(macd) + 1)) * 0.6) / 100
                min_strength = max(0.05, min(0.25, current_strength_estimate * 0.6))
            
            # Ajuste final basado en volatilidad actual (refinamiento)
            if volatility > 0:
                volatility_factor = min(1.5, max(0.7, volatility / (pd.Series(self.recent_volatilities).mean() if len(self.recent_volatilities) >= min_samples else volatility)))
                min_strength *= volatility_factor  # Más estricto en alta volatilidad relativa
            
            
            return {
                "min_volume": min_volume,
                "max_volatility": max_volatility,
                "min_strength": min_strength,
                "rsi_overbought": rsi_overbought,
                "rsi_oversold": rsi_oversold
            }
        except Exception as e:
            self.logger.exception(f"❌ Error calculando umbrales dinámicos: {e}")
            # En caso de error, intentar usar valores actuales del mercado
            try:
                volume = market_data.get("volume", 0)
                price = market_data.get("price", 1)
                indicators = market_data.get("indicators", {})
                rsi = indicators.get("rsi", 50)
                volatility = (indicators.get("atr", 0) / price) if price > 0 else 0.05
                
                return {
                    "min_volume": volume * 0.2 if volume > 0 else 100,
                    "max_volatility": volatility * 1.5 if volatility > 0 else 0.05,
                    "min_strength": 0.1,  # Muy permisivo como último recurso
                    "rsi_overbought": min(95, rsi + 15) if rsi < 80 else 85,
                    "rsi_oversold": max(5, rsi - 15) if rsi > 20 else 15
                }
            except:
                # Último recurso: valores muy permisivos basados en mercado típico
                return {
                    "min_volume": 100,
                    "max_volatility": 0.1,
                    "min_strength": 0.05,
                    "rsi_overbought": 90,
                    "rsi_oversold": 10
                }
    
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
                    self.logger.warning("🐛 [DEBUG] Rechazado: market_data o indicators faltantes")
                return None

            indicators = market_data["indicators"]
            price = market_data["price"]

            # Si faltan indicadores, usar valores por defecto o fallback
            required = ["fast_ma", "slow_ma", "rsi"]
            missing = [k for k in required if k not in indicators]
            if missing:
                if is_debug:
                    self.logger.warning(f"🐛 [DEBUG] Indicadores faltantes: {missing}, usando fallback")
                # Usar precio como fallback para MAs y RSI neutral
                indicators.setdefault("fast_ma", price)
                indicators.setdefault("slow_ma", price)
                indicators.setdefault("rsi", 50)  # RSI neutral
                self.logger.warning(f"⚠️ Indicadores faltantes ({missing}), usando valores por defecto")

            if is_debug:
                self.logger.info(
                    f"🐛 [DEBUG] Indicadores disponibles - "
                    f"EMA9: {indicators.get('fast_ma', 0):.2f}, "
                    f"EMA21: {indicators.get('slow_ma', 0):.2f}, "
                    f"RSI: {indicators.get('rsi', 0):.2f}"
                )

            # Análisis simplificado (SIEMPRE genera señal)
            signal = self._analyze_indicators(indicators, price)
            if not signal:
                # Esto no debería pasar nunca con la nueva lógica, pero por seguridad:
                self.logger.warning("⚠️ _analyze_indicators no generó señal, usando fallback directo")
                signal = self._generate_fallback_signal(price)

            if is_debug:
                self.logger.info(
                    f"🐛 [DEBUG] ✅ Señal detectada: {signal['action']} @ {signal['price']:.2f} - "
                    f"Razón: {signal.get('reason', 'N/A')}"
                )

            # Aplicar filtros mínimos (siempre aprobar, solo ajustar si es necesario)
            filter_result = self._apply_filters(signal, market_data)
            if not filter_result:
                # Los filtros ahora solo rechazan en casos extremos (horario acciones)
                # Si se rechaza, es por una razón técnica válida
                if is_debug:
                    self.logger.warning("🐛 [DEBUG] Señal rechazada por filtros (probablemente horario)")
                return None
            else:
                if is_debug:
                    self.logger.info("🐛 [DEBUG] ✅ Filtros básicos pasados")

            # Calcular tamaño de posición simple (solo por riesgo)
            position_size = self._calculate_position_size(signal)
            if position_size <= 0:
                if is_debug:
                    self.logger.warning(f"🐛 [DEBUG] Rechazado: Tamaño de posición insuficiente ({position_size})")
                return None

            if is_debug:
                self.logger.info(f"🐛 [DEBUG] Tamaño de posición calculado: {position_size:.4f}")

            # Completar datos de la señal
            signal.update({
                "position_size": position_size,
                "timestamp": market_data["timestamp"],
                "symbol": market_data["symbol"],
            })

            self.last_signal = signal
            self.consecutive_signals += 1

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
    # ⚙️ ANÁLISIS DE INDICADORES (SIMPLIFICADO)
    # ======================================================
    def _analyze_indicators(self, indicators: Dict[str, float], price: float) -> Optional[Dict[str, Any]]:
        """
        Evalúa los indicadores técnicos para generar señal (EXTREMADAMENTE PERMISIVA)
        
        Objetivo: Operar TODOS los días, incluso con señales mediocres.
        Prioridad: Disparar de más a disparar de menos.
        
        Estrategia en cascada:
        1. Señal fuerte (EMA + RSI extremo)
        2. Señal media (solo EMA)
        3. Señal débil (solo RSI)
        4. Fallback (momentum básico)
        """
        try:
            fast = indicators.get("fast_ma", price)
            slow = indicators.get("slow_ma", price)
            rsi = indicators.get("rsi", 50)

            if any(pd.isna([fast, slow, rsi])):
                # Si hay datos faltantes, usar fallback
                return self._generate_fallback_signal(price)

            # Usar valores fijos del config
            stop_loss_pct = self.config.STOP_LOSS_PCT
            take_profit_ratio = self.config.TAKE_PROFIT_RATIO
            
            # ============================================
            # NIVEL 1: Señal FUERTE (EMA + RSI extremo)
            # ============================================
            rsi_buy_strong = 45  # Muy permisivo
            rsi_sell_strong = 55  # Muy permisivo
            
            if fast > slow and rsi < rsi_buy_strong:
                return {
                    "action": "BUY",
                    "price": price,
                    "strength": 0.7,
                    "reason": f"FUERTE: EMA rápida > EMA lenta + RSI < {rsi_buy_strong}",
                    "stop_loss": round(price * (1 - stop_loss_pct), 2),
                    "take_profit": round(price * (1 + stop_loss_pct * take_profit_ratio), 2),
                }

            if fast < slow and rsi > rsi_sell_strong:
                return {
                    "action": "SELL",
                    "price": price,
                    "strength": 0.7,
                    "reason": f"FUERTE: EMA rápida < EMA lenta + RSI > {rsi_sell_strong}",
                    "stop_loss": round(price * (1 + stop_loss_pct), 2),
                    "take_profit": round(price * (1 - stop_loss_pct * take_profit_ratio), 2),
                }

            # ============================================
            # NIVEL 2: Señal MEDIA (solo EMA)
            # ============================================
            ma_diff_pct = abs(fast - slow) / slow * 100 if slow > 0 else 0
            
            if fast > slow and ma_diff_pct > 0.1:  # Cualquier diferencia mínima
                return {
                    "action": "BUY",
                    "price": price,
                    "strength": 0.5,
                    "reason": f"MEDIA: EMA rápida > EMA lenta (diff: {ma_diff_pct:.2f}%)",
                    "stop_loss": round(price * (1 - stop_loss_pct), 2),
                    "take_profit": round(price * (1 + stop_loss_pct * take_profit_ratio), 2),
                }

            if fast < slow and ma_diff_pct > 0.1:
                return {
                    "action": "SELL",
                    "price": price,
                    "strength": 0.5,
                    "reason": f"MEDIA: EMA rápida < EMA lenta (diff: {ma_diff_pct:.2f}%)",
                    "stop_loss": round(price * (1 + stop_loss_pct), 2),
                    "take_profit": round(price * (1 - stop_loss_pct * take_profit_ratio), 2),
                }

            # ============================================
            # NIVEL 3: Señal DÉBIL (solo RSI)
            # ============================================
            rsi_buy_weak = 50  # RSI por debajo de 50 = compra
            rsi_sell_weak = 50  # RSI por encima de 50 = venta
            
            if rsi < rsi_buy_weak:
                return {
                    "action": "BUY",
                    "price": price,
                    "strength": 0.3,
                    "reason": f"DÉBIL: RSI < {rsi_buy_weak} (momentum bajista, posible rebote)",
                    "stop_loss": round(price * (1 - stop_loss_pct), 2),
                    "take_profit": round(price * (1 + stop_loss_pct * take_profit_ratio), 2),
                }

            if rsi > rsi_sell_weak:
                return {
                    "action": "SELL",
                    "price": price,
                    "strength": 0.3,
                    "reason": f"DÉBIL: RSI > {rsi_sell_weak} (momentum alcista, posible reversión)",
                    "stop_loss": round(price * (1 + stop_loss_pct), 2),
                    "take_profit": round(price * (1 - stop_loss_pct * take_profit_ratio), 2),
                }

            # ============================================
            # NIVEL 4: FALLBACK (siempre genera señal)
            # ============================================
            return self._generate_fallback_signal(price)

        except Exception as e:
            self.logger.exception(f"❌ Error analizando indicadores: {e}")
            # Incluso en error, generar fallback
            return self._generate_fallback_signal(price)
    
    def _generate_fallback_signal(self, price: float) -> Dict[str, Any]:
        """
        Genera señal de fallback cuando no hay señales técnicas claras.
        Alterna entre BUY y SELL para asegurar operaciones.
        """
        stop_loss_pct = self.config.STOP_LOSS_PCT
        take_profit_ratio = self.config.TAKE_PROFIT_RATIO
        
        # Alternar basado en timestamp para variar
        import time
        use_buy = int(time.time()) % 2 == 0
        
        if use_buy:
            return {
                "action": "BUY",
                "price": price,
                "strength": 0.2,
                "reason": "FALLBACK: Sin señales técnicas claras, operación exploratoria BUY",
                "stop_loss": round(price * (1 - stop_loss_pct), 2),
                "take_profit": round(price * (1 + stop_loss_pct * take_profit_ratio), 2),
            }
        else:
            return {
                "action": "SELL",
                "price": price,
                "strength": 0.2,
                "reason": "FALLBACK: Sin señales técnicas claras, operación exploratoria SELL",
                "stop_loss": round(price * (1 + stop_loss_pct), 2),
                "take_profit": round(price * (1 - stop_loss_pct * take_profit_ratio), 2),
            }

    # ======================================================
    # 🧮 CÁLCULOS AUXILIARES
    # ======================================================
    def _calc_strength(self, fast: float, slow: float, rsi: float, macd: float,
                       macd_signal: float, bullish: bool, thresholds: Optional[Dict[str, float]] = None) -> float:
        """Calcula fuerza de la señal (0 a 1) en base a MA, RSI y MACD usando umbrales dinámicos"""
        try:
            ma_diff = abs(fast - slow) / slow * 100
            
            # Usar umbrales dinámicos si están disponibles, sino usar config
            if thresholds:
                rsi_overbought = thresholds.get("rsi_overbought", self.config.RSI_OVERBOUGHT)
                rsi_oversold = thresholds.get("rsi_oversold", self.config.RSI_OVERSOLD)
            else:
                rsi_overbought = self.config.RSI_OVERBOUGHT
                rsi_oversold = self.config.RSI_OVERSOLD
            
            # Calcular factor RSI usando umbrales dinámicos
            if bullish:
                # Para compras: cuanto más lejos esté del sobrecompra, mejor
                rsi_range = rsi_overbought - rsi_oversold
                rsi_factor = (rsi_overbought - rsi) / rsi_range if rsi_range > 0 else 0.5
            else:
                # Para ventas: cuanto más lejos esté del sobreventa, mejor
                rsi_range = rsi_overbought - rsi_oversold
                rsi_factor = (rsi - rsi_oversold) / rsi_range if rsi_range > 0 else 0.5
            
            # Normalizar RSI factor a 0-1
            rsi_factor = max(0, min(1, rsi_factor))
            
            # Factor MACD: relación entre MACD y su señal
            macd_factor = abs(macd / macd_signal) if macd_signal != 0 else 0
            macd_factor = min(1, macd_factor / 2)  # Normalizar
            
            # Combinar factores (ajustar pesos según importancia)
            strength = ma_diff * 0.4 + rsi_factor * 0.3 + macd_factor * 0.3
            return max(0, min(1, strength / 10))  # Normalizar a rango 0-1
        except Exception:
            return 0.0

    def _apply_filters(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """
        Filtra señales con condiciones MÍNIMAS (EXTREMADAMENTE PERMISIVO)
        
        Objetivo: Disparar de más a disparar de menos.
        Solo filtra condiciones que podrían causar errores técnicos.
        """
        try:
            is_debug = self.config.ENABLE_DEBUG_STRATEGY
            
            # ============================================
            # FILTRO 1: Evitar repeticiones excesivas (MUY permisivo)
            # ============================================
            # Solo bloquear si hay 20+ señales consecutivas del mismo tipo
            max_consecutive = 20  # Extremadamente permisivo
            
            if (
                self.last_signal
                and self.last_signal["action"] == signal["action"]
                and self.consecutive_signals >= max_consecutive
            ):
                if is_debug:
                    self.logger.warning(
                        f"🐛 [DEBUG] Filtro: Señales consecutivas ({self.consecutive_signals} >= {max_consecutive}) "
                        f"del mismo tipo ({signal['action']})"
                    )
                # En vez de rechazar, alternar la señal
                signal["action"] = "SELL" if signal["action"] == "BUY" else "BUY"
                signal["reason"] += " (alternada por repetición)"
                self.consecutive_signals = 0  # Resetear contador
                self.logger.info(f"🔄 Señal alternada para evitar repetición: {signal['action']}")

            # ============================================
            # FILTRO 2: Volumen mínimo (CASI eliminado)
            # ============================================
            # Solo rechazar si volumen es literalmente 0 (error de datos)
            min_volume = 0.01  # Prácticamente sin filtro
            
            volume = market_data.get("volume", 0)
            if volume <= min_volume:
                if is_debug:
                    self.logger.warning(
                        f"🐛 [DEBUG] Filtro: Volumen cero o negativo ({volume:.2f})"
                    )
                # No rechazar, solo loguear
                self.logger.warning(f"⚠️ Volumen muy bajo ({volume:.2f}), pero permitiendo trade")

            # ============================================
            # FILTRO 3: Horario (solo para acciones)
            # ============================================
            if self.config.MARKET == "STOCK":
                hour = market_data.get("timestamp", datetime.now()).hour
                if not (self.config.TRADING_START_HOUR <= hour < self.config.TRADING_END_HOUR):
                    if is_debug:
                        self.logger.warning(
                            f"🐛 [DEBUG] Filtro: Fuera de horario de trading "
                            f"(Hora: {hour}, Permitido: {self.config.TRADING_START_HOUR}-{self.config.TRADING_END_HOUR})"
                        )
                    # Para acciones, sí rechazar fuera de horario (no hay mercado)
                    return False

            if is_debug:
                self.logger.info("🐛 [DEBUG] ✅ Todos los filtros básicos pasados")
            
            # Aprobar siempre (excepto horario de acciones)
            return True
        except Exception as e:
            self.logger.exception(f"❌ Error aplicando filtros: {e}")
            # En caso de error, aprobar de todas formas (disparar de más)
            return True

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
            "name": "MA Crossover + RSI (Simplificado)",
            "description": "Cruce de medias móviles con RSI - BUY: EMA rápida > EMA lenta y RSI < 35 | SELL: EMA rápida < EMA lenta y RSI > 65",
            "parameters": {
                "fast_ma_period": self.config.FAST_MA_PERIOD,
                "slow_ma_period": self.config.SLOW_MA_PERIOD,
                "rsi_period": self.config.RSI_PERIOD,
                "rsi_buy_threshold": 35,
                "rsi_sell_threshold": 65,
                "stop_loss_pct": self.config.STOP_LOSS_PCT,
                "take_profit_ratio": self.config.TAKE_PROFIT_RATIO,
            },
            "last_signal": self.last_signal,
            "consecutive_signals": self.consecutive_signals,
        }

    def reset_strategy(self):
        """Reinicia el estado interno de la estrategia"""
        self.last_signal = None
        self.consecutive_signals = 0
        self.logger.info("🔄 Estrategia reiniciada")
