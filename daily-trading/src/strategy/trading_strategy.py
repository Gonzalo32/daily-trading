"""
Estrategia de trading automatizada
Basada en cruce de medias móviles, RSI y MACD con filtros dinámicos.
"""

from datetime import datetime
from typing import Dict, Optional, Any
import pandas as pd

from config import Config
from src.utils.logging_setup import setup_logging


class TradingStrategy:
    """Estrategia de trading basada en medias móviles, RSI y MACD"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(__name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)

        # Estado de la estrategia
        self.last_signal: Optional[Dict[str, Any]] = None
        self.consecutive_signals: int = 0
        
        # Historial para umbrales dinámicos (ampliado para mejor adaptación)
        self.recent_volumes = []
        self.recent_volatilities = []
        self.recent_strengths = []
        self.recent_rsi_values = []
        self.recent_ma_diffs = []  # Diferencias entre fast_ma y slow_ma
        self.recent_macd_values = []
        self.recent_prices = []

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
            
            self.logger.debug(
                f"📊 Umbrales dinámicos calculados: "
                f"vol={min_volume:.2f}, volatl={max_volatility:.4f}, "
                f"fuerza={min_strength:.3f}, RSI=[{rsi_oversold:.1f}, {rsi_overbought:.1f}]"
            )
            
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
    
    async def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Genera señal de compra o venta según indicadores técnicos"""
        try:
            if not market_data or "indicators" not in market_data:
                return None

            indicators = market_data["indicators"]
            price = market_data["price"]

            required = ["fast_ma", "slow_ma", "rsi", "macd", "macd_signal"]
            if not all(k in indicators for k in required):
                self.logger.warning("⚠️ Faltan indicadores necesarios para generar señal")
                return None

            # Calcular umbrales dinámicos
            dynamic_thresholds = self._calculate_dynamic_thresholds(market_data)
            
            # Análisis principal con umbrales dinámicos
            signal = self._analyze_indicators(indicators, price, dynamic_thresholds)
            if not signal:
                self.consecutive_signals = 0
                return None

            # Aplicar filtros con umbrales dinámicos
            if not self._apply_filters(signal, market_data, dynamic_thresholds):
                return None

            # Calcular tamaño de posición (proporcional a fuerza)
            position_size = self._calculate_position_size(signal)
            if position_size <= 0:
                self.logger.info("ℹ️ Tamaño de posición insuficiente para operar")
                return None

            # Completar datos de la señal
            signal.update({
                "position_size": position_size,
                "timestamp": market_data["timestamp"],
                "symbol": market_data["symbol"],
            })

            self.last_signal = signal
            self.consecutive_signals += 1

            self.logger.info(
                f"📈 Señal generada: {signal['action']} {signal['symbol']} | "
                f"{signal['reason']} | Fuerza={signal['strength']:.2f}"
            )
            return signal

        except Exception as e:
            self.logger.exception(f"❌ Error generando señal: {e}")
            return None

    # ======================================================
    # ⚙️ ANÁLISIS DE INDICADORES
    # ======================================================
    def _analyze_indicators(self, indicators: Dict[str, float], price: float, thresholds: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """Evalúa los indicadores técnicos para generar señal"""
        try:
            fast = indicators["fast_ma"]
            slow = indicators["slow_ma"]
            rsi = indicators["rsi"]
            macd = indicators["macd"]
            macd_signal = indicators["macd_signal"]

            if any(pd.isna([fast, slow, rsi, macd, macd_signal])):
                return None

            # Señal de compra (usando umbrales dinámicos)
            rsi_overbought = thresholds.get("rsi_overbought", self.config.RSI_OVERBOUGHT)
            min_strength = thresholds.get("min_strength", 0.18)
            
            if fast > slow and rsi < rsi_overbought and macd > macd_signal and macd > 0:
                strength = self._calc_strength(fast, slow, rsi, macd, macd_signal, bullish=True, thresholds=thresholds)
                if strength > min_strength:
                    return {
                        "action": "BUY",
                        "price": price,
                        "strength": strength,
                        "reason": "Cruce alcista + RSI + MACD",
                        "stop_loss": round(price * (1 - self.config.STOP_LOSS_PCT), 2),
                        "take_profit": round(price * (1 + self.config.STOP_LOSS_PCT * self.config.TAKE_PROFIT_RATIO), 2),
                    }

            # Señal de venta (usando umbrales dinámicos)
            rsi_oversold = thresholds.get("rsi_oversold", self.config.RSI_OVERSOLD)
            
            if fast < slow and rsi > rsi_oversold and macd < macd_signal and macd < 0:
                strength = self._calc_strength(fast, slow, rsi, macd, macd_signal, bullish=False, thresholds=thresholds)
                if strength > min_strength:
                    return {
                        "action": "SELL",
                        "price": price,
                        "strength": strength,
                        "reason": "Cruce bajista + RSI + MACD",
                        "stop_loss": round(price * (1 + self.config.STOP_LOSS_PCT), 2),
                        "take_profit": round(price * (1 - self.config.STOP_LOSS_PCT * self.config.TAKE_PROFIT_RATIO), 2),
                    }

            return None

        except Exception as e:
            self.logger.exception(f"❌ Error analizando indicadores: {e}")
            return None

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

    def _apply_filters(self, signal: Dict[str, Any], market_data: Dict[str, Any], thresholds: Dict[str, float]) -> bool:
        """Filtra señales débiles o condiciones no óptimas"""
        try:
            # Evitar repeticiones excesivas
            if (
                self.last_signal
                and self.last_signal["action"] == signal["action"]
                and self.consecutive_signals >= 5  # Aumentado de 3 a 5 para aprovechar tendencias fuertes
            ):
                self.logger.info("⛔ Señales consecutivas del mismo tipo ignoradas")
                return False

            # Volatilidad máxima dinámica
            atr = market_data["indicators"].get("atr")
            max_volatility = thresholds.get("max_volatility", 0.05)
            if atr:
                volatility = atr / market_data["price"]
                if volatility > max_volatility:
                    self.logger.info(f"⚠️ Volatilidad alta ({volatility:.4f} > {max_volatility:.4f}), señal ignorada")
                    return False

            # Volumen mínimo dinámico
            min_volume = thresholds.get("min_volume", 300)
            if market_data.get("volume", 0) < min_volume:
                self.logger.info(f"⚠️ Volumen insuficiente ({market_data.get('volume', 0):.2f} < {min_volume:.2f}), señal ignorada")
                return False

            # Horario (solo para acciones)
            if self.config.MARKET == "STOCK":
                hour = market_data["timestamp"].hour
                if not (self.config.TRADING_START_HOUR <= hour < self.config.TRADING_END_HOUR):
                    self.logger.info("🕒 Fuera del horario de mercado")
                    return False

            # Fuerza mínima dinámica
            min_strength = thresholds.get("min_strength", 0.18)
            if signal["strength"] < min_strength:
                self.logger.info(f"💤 Señal débil descartada (fuerza: {signal['strength']:.3f} < {min_strength:.3f})")
                return False

            return True
        except Exception as e:
            self.logger.exception(f"❌ Error aplicando filtros: {e}")
            return False

    def _calculate_position_size(self, signal: Dict[str, Any]) -> float:
        """Calcula el tamaño de posición basado en el riesgo y fuerza de señal"""
        try:
            base_capital = self.config.INITIAL_CAPITAL
            risk_amount = base_capital * self.config.RISK_PER_TRADE
            risk_per_unit = abs(signal["price"] - signal["stop_loss"])
            if risk_per_unit == 0:
                return 0.0
            qty = risk_amount / risk_per_unit
            qty *= signal["strength"]  # ajusta por fuerza
            return round(min(qty, (base_capital * 0.1) / signal["price"]), 2)
        except Exception as e:
            self.logger.exception(f"❌ Error calculando posición: {e}")
            return 0.0

    # ======================================================
    # 📊 UTILIDADES
    # ======================================================
    def get_strategy_info(self) -> Dict[str, Any]:
        """Retorna configuración y último estado"""
        return {
            "name": "MA Crossover + RSI + MACD",
            "description": "Cruce de medias móviles con confirmación de RSI y MACD",
            "parameters": {
                "fast_ma_period": self.config.FAST_MA_PERIOD,
                "slow_ma_period": self.config.SLOW_MA_PERIOD,
                "rsi_period": self.config.RSI_PERIOD,
                "rsi_overbought": self.config.RSI_OVERBOUGHT,
                "rsi_oversold": self.config.RSI_OVERSOLD,
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
