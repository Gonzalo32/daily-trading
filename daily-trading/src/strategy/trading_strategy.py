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
        
        # Historial para umbrales dinámicos
        self.recent_volumes = []
        self.recent_volatilities = []
        self.recent_strengths = []

    # ======================================================
    # 🎯 GENERACIÓN DE SEÑALES
    # ======================================================
    def _calculate_dynamic_thresholds(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calcula umbrales dinámicos basados en condiciones del mercado"""
        try:
            volume = market_data.get("volume", 0)
            price = market_data.get("price", 1)
            indicators = market_data.get("indicators", {})
            atr = indicators.get("atr", 0)
            
            # Calcular volatilidad actual
            volatility = (atr / price) if price > 0 else 0
            
            # Mantener historial (últimos 50 valores)
            self.recent_volumes.append(volume)
            self.recent_volatilities.append(volatility)
            if len(self.recent_volumes) > 50:
                self.recent_volumes.pop(0)
                self.recent_volatilities.pop(0)
            
            # Calcular percentiles para adaptación
            if len(self.recent_volumes) >= 10:
                sorted_volumes = sorted(self.recent_volumes)
                volume_percentile_30 = sorted_volumes[int(len(sorted_volumes) * 0.3)]
                
                sorted_volatilities = sorted(self.recent_volatilities)
                volatility_percentile_70 = sorted_volatilities[int(len(sorted_volatilities) * 0.7)]
            else:
                volume_percentile_30 = 300  # Valor por defecto
                volatility_percentile_70 = 0.05  # 5% por defecto
            
            # Umbral de volumen dinámico (30% del percentil 30)
            min_volume = max(100, min(volume_percentile_30 * 0.3, 1000))
            
            # Umbral de volatilidad dinámico (70% del percentil 70)
            max_volatility = max(0.03, min(volatility_percentile_70 * 0.7, 0.08))
            
            # Umbral de fuerza dinámico (ajustado según volatilidad)
            # Mercados más volátiles = señales más fuertes requeridas
            if volatility > 0.04:
                min_strength = 0.25  # Más estricto en alta volatilidad
            elif volatility < 0.02:
                min_strength = 0.12  # Más permisivo en baja volatilidad
            else:
                min_strength = 0.18  # Valor base
            
            # RSI dinámico (ajusta según volatilidad)
            if volatility > 0.04:
                rsi_overbought = 75  # Más estricto
                rsi_oversold = 25
            elif volatility < 0.02:
                rsi_overbought = 85  # Más permisivo
                rsi_oversold = 15
            else:
                rsi_overbought = 80
                rsi_oversold = 20
            
            return {
                "min_volume": min_volume,
                "max_volatility": max_volatility,
                "min_strength": min_strength,
                "rsi_overbought": rsi_overbought,
                "rsi_oversold": rsi_oversold
            }
        except Exception as e:
            self.logger.exception(f"❌ Error calculando umbrales dinámicos: {e}")
            # Valores por defecto en caso de error
            return {
                "min_volume": 300,
                "max_volatility": 0.05,
                "min_strength": 0.18,
                "rsi_overbought": 80,
                "rsi_oversold": 20
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
                strength = self._calc_strength(fast, slow, rsi, macd, macd_signal, bullish=True)
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
                strength = self._calc_strength(fast, slow, rsi, macd, macd_signal, bullish=False)
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
                       macd_signal: float, bullish: bool) -> float:
        """Calcula fuerza de la señal (0 a 1) en base a MA, RSI y MACD"""
        try:
            ma_diff = abs(fast - slow) / slow * 100
            rsi_factor = (
                (self.config.RSI_OVERBOUGHT - rsi) / self.config.RSI_OVERBOUGHT
                if bullish else (rsi - self.config.RSI_OVERSOLD) / (100 - self.config.RSI_OVERSOLD)
            )
            macd_factor = abs(macd / macd_signal) if macd_signal != 0 else 0
            return ma_diff * 0.4 + rsi_factor * 0.3 + macd_factor * 0.3
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
