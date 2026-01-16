

from datetime import datetime
from typing import Dict, Optional, Any
import pandas as pd
import numpy as np

from config import Config
from src.utils.logging_setup import setup_logging


class LearningStrategy:

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(
            __name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)

        # Verificar que estamos en modo PAPER
        if config.TRADING_MODE != "PAPER":
            self.logger.warning(
                "⚠️ LearningStrategy solo debe usarse en modo PAPER. "
                "Usando en modo LIVE puede ser peligroso."
            )

        self.last_signal: Optional[Dict[str, Any]] = None
        self.consecutive_signals: int = 0
        self.last_signal_time: Optional[datetime] = None
        self.min_seconds_between_same_signal: int = 2  # Muy corto para alta frecuencia

        self.recent_signals: list = []  # Para evitar repeticiones excesivas
        self.max_recent_signals = 50

    async def generate_signal(
        self,
        market_data: Dict[str, Any],
        regime_info: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
       
        try:
            if not market_data or "indicators" not in market_data:
                return None

            indicators = market_data["indicators"]
            price = market_data.get("price", 0)

            if price <= 0:
                return None

            # Si faltan indicadores, usar valores por defecto
            required = ["fast_ma", "slow_ma", "rsi"]
            missing = [k for k in required if k not in indicators]
            if missing:
                indicators.setdefault("fast_ma", price)
                indicators.setdefault("slow_ma", price)
                indicators.setdefault("rsi", 50)

            signal = self._analyze_indicators_relative(indicators, price)

            if not signal:
                return None

            current_ts = market_data.get("timestamp")
            if isinstance(current_ts, datetime):
                now = current_ts
            else:
                now = datetime.utcnow()

            if (
                self.last_signal_time is not None
                and self.last_signal is not None
                and self.last_signal.get("action") == signal["action"]
            ):
                elapsed = (now - self.last_signal_time).total_seconds()
                if elapsed < self.min_seconds_between_same_signal:
                    return None

            if not self._apply_minimal_filters(signal, market_data):
                return None

            position_size = self._calculate_position_size(signal)
            if position_size <= 0:
                return None

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
            self.last_signal_time = now

            self.recent_signals.append({
                "action": signal["action"],
                "rsi": indicators.get("rsi", 50),
                "ema_diff_pct": signal.get("ema_diff_pct", 0),
            })
            if len(self.recent_signals) > self.max_recent_signals:
                self.recent_signals.pop(0)

            self.logger.debug(
                f"📚 [LEARNING] Señal generada: {signal['action']} {signal['symbol']} @ {price:.2f} "
                f"(RSI: {indicators.get('rsi', 50):.1f}, EMA diff: {signal.get('ema_diff_pct', 0):.4f}%)"
            )

            return signal

        except Exception as e:
            self.logger.exception(f"❌ Error generando señal learning: {e}")
            return None

    def _analyze_indicators_relative(
        self,
        indicators: Dict[str, float],
        price: float
    ) -> Optional[Dict[str, Any]]:

        try:
            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            rsi = indicators.get("rsi", 50)
            atr = indicators.get("atr", 0)

            if any(pd.isna([fast_ma, slow_ma, rsi])):
                return None


            # 1. Diferencia EMA relativa (%)
            if slow_ma > 0:
                ema_diff_pct = ((fast_ma - slow_ma) / slow_ma) * 100
            else:
                ema_diff_pct = 0

            # 2. RSI normalizado (-1 a 1, donde 0 = 50)
            # -1 (sobreventa) a 1 (sobrecompra)
            rsi_normalized = (rsi - 50) / 50

            # 3. ATR relativo (% del precio)
            atr_pct = (atr / price * 100) if price > 0 else 0

            # 4. Distancia del precio a EMAs (%)
            price_to_fast_pct = ((price - fast_ma) /
                                 fast_ma * 100) if fast_ma > 0 else 0
            price_to_slow_pct = ((price - slow_ma) /
                                 slow_ma * 100) if slow_ma > 0 else 0


            buy_condition_1 = fast_ma >= slow_ma * 0.999  # Permite hasta 0.1% de diferencia
            buy_condition_2 = rsi < 60  # Permisivo
            buy_condition_3 = rsi < 30  # Sobreventa extrema

            if (buy_condition_1 and buy_condition_2) or buy_condition_3:
                stop_loss_pct = self.config.STOP_LOSS_PCT
                take_profit_ratio = self.config.TAKE_PROFIT_RATIO

                stop_loss = round(price * (1 - stop_loss_pct), 2)
                take_profit = round(
                    price * (1 + stop_loss_pct * take_profit_ratio), 2)

                return {
                    "action": "BUY",
                    "price": price,
                    # Baja fuerza (0.3-0.6)
                    "strength": 0.3 + abs(rsi_normalized) * 0.3,
                    "reason": (
                        f"LEARNING BUY | RSI: {rsi:.1f} ({rsi_normalized:.3f} norm) | "
                        f"EMA diff: {ema_diff_pct:.4f}% | ATR: {atr_pct:.4f}%"
                    ),
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    # Features relativas para ML
                    "ema_diff_pct": ema_diff_pct,
                    "rsi_normalized": rsi_normalized,
                    "atr_pct": atr_pct,
                    "price_to_fast_pct": price_to_fast_pct,
                    "price_to_slow_pct": price_to_slow_pct,
                }


            sell_condition_1 = fast_ma <= slow_ma * \
                1.001  # Permite hasta 0.1% de diferencia
            sell_condition_2 = rsi > 40  # Permisivo
            sell_condition_3 = rsi > 70  # Sobrecompra extrema

            if (sell_condition_1 and sell_condition_2) or sell_condition_3:
                stop_loss_pct = self.config.STOP_LOSS_PCT
                take_profit_ratio = self.config.TAKE_PROFIT_RATIO

                stop_loss = round(price * (1 + stop_loss_pct), 2)
                take_profit = round(
                    price * (1 - stop_loss_pct * take_profit_ratio), 2)

                return {
                    "action": "SELL",
                    "price": price,
                    # Baja fuerza (0.3-0.6)
                    "strength": 0.3 + abs(rsi_normalized) * 0.3,
                    "reason": (
                        f"LEARNING SELL | RSI: {rsi:.1f} ({rsi_normalized:.3f} norm) | "
                        f"EMA diff: {ema_diff_pct:.4f}% | ATR: {atr_pct:.4f}%"
                    ),
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    # Features relativas para ML
                    "ema_diff_pct": ema_diff_pct,
                    "rsi_normalized": rsi_normalized,
                    "atr_pct": atr_pct,
                    "price_to_fast_pct": price_to_fast_pct,
                    "price_to_slow_pct": price_to_slow_pct,
                }

            return None

        except Exception as e:
            self.logger.exception(
                f"❌ Error analizando indicadores relativos: {e}")
            return None


    def _apply_minimal_filters(
        self,
        signal: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> bool:
        """
        Filtros mínimos: solo seguridad básica.
        NO filtra por calidad, volumen, zonas laterales, etc.
        """
        try:
            price = market_data.get("price", 0)
            if price <= 0:
                return False

            stop_loss = signal.get("stop_loss", 0)
            take_profit = signal.get("take_profit", 0)

            if signal["action"] == "BUY":
                if stop_loss >= price or take_profit <= price:
                    return False
            else:  # SELL
                if stop_loss <= price or take_profit >= price:
                    return False

            # Evitar repeticiones excesivas (diversidad)
            if len(self.recent_signals) >= 10:
                # Contar señales similares recientes
                similar_count = sum(
                    1 for s in self.recent_signals[-10:]
                    if (s["action"] == signal["action"] and
                        abs(s.get("rsi", 50) - market_data.get("indicators", {}).get("rsi", 50)) < 5)
                )
                # Si hay más de 8 señales similares en las últimas 10, rechazar
                if similar_count >= 8:
                    return False

            return True

        except Exception as e:
            self.logger.exception(f"❌ Error aplicando filtros mínimos: {e}")
            return False

    def _calculate_position_size(self, signal: Dict[str, Any]) -> float:
        """Calcula el tamaño de posición basado en riesgo"""
        try:
            if "price" not in signal or "stop_loss" not in signal:
                return 0.0

            base_capital = self.config.INITIAL_CAPITAL
            risk_per_trade = self.config.RISK_PER_TRADE

            risk_amount = base_capital * risk_per_trade
            risk_per_unit = abs(signal["price"] - signal["stop_loss"])

            if risk_per_unit <= 0:
                return 0.0

            qty = risk_amount / risk_per_unit

            # Límite de exposición (10% capital)
            max_position_value = base_capital * 0.10
            max_qty = max_position_value / signal["price"]

            final_qty = min(qty, max_qty)
            return round(final_qty, 4)

        except Exception as e:
            self.logger.exception(f"❌ Error calculando posición: {e}")
            return 0.0

    def get_strategy_info(self) -> Dict[str, Any]:
        """Retorna información de la estrategia"""
        return {
            "name": "LearningStrategy (Permisiva para ML)",
            "description": (
                "Estrategia muy permisiva diseñada para generar MUCHAS señales "
                "de diversidad para entrenar modelos ML. Usa solo features relativas "
                "para ser robusta a cambios de precio. SOLO para modo PAPER."
            ),
            "parameters": {
                "stop_loss_pct": self.config.STOP_LOSS_PCT,
                "take_profit_ratio": self.config.TAKE_PROFIT_RATIO,
                "risk_per_trade": self.config.RISK_PER_TRADE,
            },
            "last_signal": self.last_signal,
            "consecutive_signals": self.consecutive_signals,
        }

    def reset_strategy(self):
        """Reinicia el estado de la estrategia"""
        self.last_signal = None
        self.consecutive_signals = 0
        self.last_signal_time = None
        self.recent_signals = []
        self.logger.info("🔄 LearningStrategy reiniciada")

    def update_parameters_for_regime(self, regime_info: Dict[str, Any]):
  
        pass  # No-op: LearningStrategy no adapta parámetros

    def get_current_parameters(self) -> Dict[str, Any]:
        """Retorna parámetros actuales (fijos en LearningStrategy)"""
        return {
            "stop_loss_pct": self.config.STOP_LOSS_PCT,
            "take_profit_ratio": self.config.TAKE_PROFIT_RATIO,
            "risk_per_trade": self.config.RISK_PER_TRADE,
        }

    def get_decision_space(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, bool]:
       
        try:
            indicators = market_data.get("indicators", {})
            price = market_data.get("price", 0)

            if price <= 0:
                return {"buy": False, "sell": False, "hold": True}

            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            rsi = indicators.get("rsi", 50)

         
            decision_space = {
                "buy": True,   # Siempre posible en learning
                "sell": True,  # Siempre posible en learning
                "hold": True   # Siempre disponible
            }

      
            if fast_ma >= slow_ma * 0.999 and rsi < 60:
                # Condiciones favorables para BUY
                pass
            elif fast_ma <= slow_ma * 1.001 and rsi > 40:
                # Condiciones favorables para SELL
                pass
            else:
                # Condiciones neutrales, HOLD más probable
                pass

            return decision_space

        except Exception as e:
            self.logger.exception(f"❌ Error obteniendo decision_space: {e}")
            return {"buy": False, "sell": False, "hold": True}
