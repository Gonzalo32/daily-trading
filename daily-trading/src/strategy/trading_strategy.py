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

    # ======================================================
    # 🎯 GENERACIÓN DE SEÑALES
    # ======================================================
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

            # Análisis principal
            signal = self._analyze_indicators(indicators, price)
            if not signal:
                self.consecutive_signals = 0
                return None

            # Aplicar filtros
            if not self._apply_filters(signal, market_data):
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
    def _analyze_indicators(self, indicators: Dict[str, float], price: float) -> Optional[Dict[str, Any]]:
        """Evalúa los indicadores técnicos para generar señal"""
        try:
            fast = indicators["fast_ma"]
            slow = indicators["slow_ma"]
            rsi = indicators["rsi"]
            macd = indicators["macd"]
            macd_signal = indicators["macd_signal"]

            if any(pd.isna([fast, slow, rsi, macd, macd_signal])):
                return None

            # Señal de compra
            if fast > slow and rsi < self.config.RSI_OVERBOUGHT and macd > macd_signal and macd > 0:
                strength = self._calc_strength(fast, slow, rsi, macd, macd_signal, bullish=True)
                if strength > 0.18:  # Umbral reducido de 0.3 a 0.18 para más oportunidades
                    return {
                        "action": "BUY",
                        "price": price,
                        "strength": strength,
                        "reason": "Cruce alcista + RSI + MACD",
                        "stop_loss": round(price * (1 - self.config.STOP_LOSS_PCT), 2),
                        "take_profit": round(price * (1 + self.config.STOP_LOSS_PCT * self.config.TAKE_PROFIT_RATIO), 2),
                    }

            # Señal de venta
            if fast < slow and rsi > self.config.RSI_OVERSOLD and macd < macd_signal and macd < 0:
                strength = self._calc_strength(fast, slow, rsi, macd, macd_signal, bullish=False)
                if strength > 0.18:  # Umbral reducido de 0.3 a 0.18 para más oportunidades
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

    def _apply_filters(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
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

            # Volatilidad máxima (si ATR está disponible)
            atr = market_data["indicators"].get("atr")
            if atr:
                volatility = atr / market_data["price"]
                if volatility > 0.05:
                    self.logger.info("⚠️ Volatilidad alta, señal ignorada")
                    return False

            # Volumen mínimo (reducido de 1000 a 300 para más oportunidades)
            if market_data.get("volume", 0) < 300:
                self.logger.info("⚠️ Volumen insuficiente, señal ignorada")
                return False

            # Horario (solo para acciones)
            if self.config.MARKET == "STOCK":
                hour = market_data["timestamp"].hour
                if not (self.config.TRADING_START_HOUR <= hour < self.config.TRADING_END_HOUR):
                    self.logger.info("🕒 Fuera del horario de mercado")
                    return False

            # Fuerza mínima (reducido de 0.3 a 0.18 para más oportunidades)
            if signal["strength"] < 0.18:
                self.logger.info("💤 Señal débil descartada")
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
