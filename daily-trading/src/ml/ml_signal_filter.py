"""
Filtro ML de Señales
Usa Machine Learning para filtrar señales y predecir probabilidad de éxito
"""

import os
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import joblib   # <- FIX CRÍTICO
from datetime import datetime

from src.utils.logging_setup import setup_logging


class MLSignalFilter:
    def __init__(
        self,
        model_path="models/model.pkl",
        min_probability=0.55,
        config=None
    ):
        self.model_path = model_path
        self.min_probability = min_probability
        self.model_loaded = False
        self.model = None
        self.config = config  # <- FIX #2

        # Features que el modelo debe recibir
        self.expected_features = [
            "rsi", "macd", "macd_signal",
            "fast_ma", "slow_ma",
            "atr", "ma_diff_pct",
            "rsi_normalized", "macd_strength",
            "volatility_normalized", "volume_relative",
            "hour_of_day",
            "regime_trending_bullish", "regime_trending_bearish",
            "regime_ranging", "regime_high_volatility",
            "regime_low_volatility", "regime_chaotic",
            "daily_pnl_normalized", "daily_trades",
            "consecutive_signals",
            "signal_strength", "signal_buy", "signal_sell"
        ]

        self.high_probability = 0.70
        self.logger = setup_logging(__name__)
        self.logger.info(f"🔮 Filtro ML iniciado | min_probability={min_probability}")


    def load_model(self):
        try:
            if not os.path.exists(self.model_path):
                self.logger.warning("⚠️ Modelo ML no encontrado. Se usará modo sin aprendizaje.")
                return False

            self.model = joblib.load(self.model_path)
            self.model_loaded = True
            self.logger.info("🧠 Modelo ML cargado correctamente.")
            return True

        except Exception as e:
            self.logger.exception(f"❌ Error cargando modelo ML: {e}")
            return False


    async def filter_signal(self, signal, market_data, regime_info, bot_state):
        """Filtra señal usando ML o fallback por defecto"""

        # Si no hay modelo → aprobar sin ML
        if not self.model_loaded or self.model is None:
            return self._default_approval(signal)

        features = self._build_features(signal, market_data, regime_info, bot_state)
        if features is None:
            return self._default_approval(signal)

        try:
            proba = self.model.predict_proba(features)
            p_win = proba[0][1]
        except Exception as e:
            self.logger.error(f"❌ Error en predicción ML: {e}")
            return self._default_approval(signal)

        return self._make_decision(p_win, signal, features)


    def _build_features(self, signal, market_data, regime_info, bot_state):
        """Construcción del vector de entrada del ML"""
        try:
            indicators = market_data.get("indicators", {})
            price = market_data.get("price", 0)
            volume = market_data.get("volume", 0)

            regime_str = regime_info.get("regime", "ranging")
            regime_metrics = regime_info.get("metrics", {})

            timestamp = market_data.get("timestamp", datetime.utcnow())
            hour = timestamp.hour if hasattr(timestamp, "hour") else 12

            f = {}

            # ----------- Indicadores técnicos -----------
            f["rsi"] = indicators.get("rsi", 50)
            f["macd"] = indicators.get("macd", 0)
            f["macd_signal"] = indicators.get("macd_signal", 0)
            f["fast_ma"] = indicators.get("fast_ma", price)
            f["slow_ma"] = indicators.get("slow_ma", price)
            f["atr"] = indicators.get("atr", 0)

            # Features derivadas
            f["ma_diff_pct"] = (f["fast_ma"] - f["slow_ma"]) / f["slow_ma"] * 100 if f["slow_ma"] else 0
            f["rsi_normalized"] = (f["rsi"] - 50) / 50
            f["macd_strength"] = (f["macd"] / f["macd_signal"]) if f["macd_signal"] else 0

            # ----------- Contexto de mercado -----------
            f["volatility_normalized"] = (f["atr"] / price) if price > 0 else 0

            volume_mean = regime_metrics.get("volume_mean", volume)
            f["volume_relative"] = (volume / volume_mean) if volume_mean else 1

            f["hour_of_day"] = hour

            # ----------- One-hot regime -----------
            for r in [
                "trending_bullish", "trending_bearish", "ranging",
                "high_volatility", "low_volatility", "chaotic"
            ]:
                f[f"regime_{r}"] = 1 if regime_str == r else 0

            # ----------- Estado del bot -----------
            initial_cap = getattr(self.config, "INITIAL_CAPITAL", 1000)
            daily_pnl = bot_state.get("daily_pnl", 0)

            f["daily_pnl_normalized"] = daily_pnl / initial_cap
            f["daily_trades"] = bot_state.get("daily_trades", 0)
            f["consecutive_signals"] = bot_state.get("consecutive_signals", 0)

            # ----------- Señal -----------
            f["signal_strength"] = signal.get("strength", 0)
            f["signal_buy"] = 1 if signal.get("action") == "BUY" else 0
            f["signal_sell"] = 1 if signal.get("action") == "SELL" else 0

            df = pd.DataFrame([f])

            # Asegurar todas las features esperadas
            for col in self.expected_features:
                if col not in df:
                    df[col] = 0

            return df[self.expected_features]

        except Exception as e:
            self.logger.error(f"❌ Error construyendo features ML: {e}")
            return None


    def _make_decision(self, p_win, signal, features):
        approved = p_win >= self.min_probability
        confidence = abs(p_win - 0.5) * 2

        if p_win >= self.high_probability:
            rr = 3.0
            size_mul = 1.3
        elif p_win >= 0.60:
            rr = 2.5
            size_mul = 1.1
        else:
            rr = 1.5
            size_mul = 0.8

        return {
            "approved": approved,
            "probability": p_win,
            "confidence": confidence,
            "recommended_rr": rr,
            "size_multiplier": size_mul,
            "reason": "ML decision"
        }


    def _default_approval(self, signal):
        return {
            "approved": True,
            "probability": 0.5,
            "confidence": 0.2,
            "recommended_rr": 2.0,
            "size_multiplier": 1.0,
            "reason": "Sin modelo ML"
        }
