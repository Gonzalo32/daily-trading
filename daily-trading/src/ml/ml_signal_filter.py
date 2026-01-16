"""
Filtro ML de Señales
Usa Machine Learning para filtrar señales y predecir probabilidad de éxito
"""
# pylint: disable=import-error,logging-fstring-interpolation,broad-except,unused-argument

import os
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime

from src.utils.logging_setup import setup_logging

# Import opcional de joblib (no crashear si no está)
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    joblib = None


class MLSignalFilter:
    def __init__(
        self,
        model_path: str = "models/model.pkl",
        min_probability: float = 0.55
    ):
        self.model_path = model_path
        self.min_probability = min_probability

        # valores seguros por defecto
        self.high_probability = 0.70
        self.expected_features: list[str] = []

        self.model = None
        self.model_loaded = False

        self.logger = setup_logging(__name__)
        self.logger.info(
            f"🔮 Filtro ML iniciado | min_probability={self.min_probability}"
        )

        self.load_model()

    def get_model_info(self) -> dict:
        return {
            "model_path": self.model_path,
            "min_probability": self.min_probability,
            "model_loaded": self.model is not None,
        }

    # ======================================================
    # 🧠 MODELO
    # ======================================================
    def load_model(self) -> bool:
        try:
            # Verificar si joblib está disponible
            if not JOBLIB_AVAILABLE:
                self.logger.warning(
                    "⚠️ joblib no está instalado. ML deshabilitado. "
                    "Instalar con: pip install joblib"
                )
                self.model_loaded = False
                return False

            if not os.path.exists(self.model_path):
                self.logger.warning(
                    f"⚠️ Modelo ML no encontrado en {self.model_path}. "
                    "Se continúa sin ML."
                )
                self.model_loaded = False
                return False

            self.model = joblib.load(self.model_path)
            self.model_loaded = True

            # intentar inferir features si es un sklearn model
            if hasattr(self.model, "feature_names_in_"):
                self.expected_features = list(
                    self.model.feature_names_in_
                )

            self.logger.info("🧠 Modelo ML cargado correctamente.")
            return True

        except Exception as e:
            self.logger.exception(f"❌ Error cargando modelo ML: {e}")
            self.model_loaded = False
            return False

    # ======================================================
    # ✅ MÉTODO QUE FALTABA (CRÍTICO)
    # ======================================================
    def is_model_available(self) -> bool:
        return self.model_loaded and self.model is not None

    # ======================================================
    # 🔎 FILTRO PRINCIPAL
    # ======================================================
    async def filter_signal(
        self,
        signal: Dict[str, Any],
        market_data: Dict[str, Any],
        regime_info: Dict[str, Any],
        bot_state: Dict[str, Any]
    ) -> Dict[str, Any]:

        # sin modelo → aprobar por defecto
        if not self.is_model_available():
            return self._default_approval(signal)

        features = self._build_features(
            signal, market_data, regime_info, bot_state
        )

        if features is None:
            return self._default_approval(signal)

        try:
            proba = self.model.predict_proba(features)
            p_win = float(proba[0][1])
        except Exception as e:
            self.logger.error(f"❌ Error predicción ML: {e}")
            return self._default_approval(signal)

        return self._make_decision(p_win)

    # ======================================================
    # 🧩 FEATURES NORMALIZADAS/RELATIVAS (Learning-Aware)
    # ======================================================
    def _build_features(
        self,
        signal: Dict[str, Any],
        market_data: Dict[str, Any],
        regime_info: Dict[str, Any],
        bot_state: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        """
        Construye features RELATIVAS y NORMALIZADAS para ML.
        
        OBJETIVO: El modelo debe aprender ESTRATEGIAS, no valores absolutos.
        Features relativas permiten generalizar a otros activos y precios futuros.
        """
        try:
            price = market_data.get("price", 0)
            indicators = market_data.get("indicators", {})
            
            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            rsi = indicators.get("rsi", 50)
            atr = indicators.get("atr", 0)
            macd = indicators.get("macd", 0)
            
            # FEATURES RELATIVAS (no valores absolutos)
            # 1. Retornos porcentuales (normalizados)
            # 2. Distancias relativas a medias móviles
            # 3. RSI normalizado (ya está en 0-100, pero podemos centrarlo)
            # 4. Volatilidad relativa (ATR como % del precio)
            # 5. Pendientes de EMAs (cambio relativo)
            
            # Calcular features relativas
            ema_fast_diff_pct = ((fast_ma - price) / price * 100) if price > 0 else 0
            ema_slow_diff_pct = ((slow_ma - price) / price * 100) if price > 0 else 0
            ema_cross_diff_pct = ((fast_ma - slow_ma) / slow_ma * 100) if slow_ma > 0 else 0
            atr_pct = (atr / price * 100) if price > 0 else 0
            
            # RSI normalizado (centrado en 50, rango -1 a 1)
            rsi_normalized = (rsi - 50) / 50  # -1 (oversold) a +1 (overbought)
            
            # MACD relativo al precio
            macd_pct = (macd / price * 100) if price > 0 and price != 0 else 0
            
            # Contexto de mercado (tendencia/rango)
            # Si fast_ma > slow_ma -> tendencia alcista (1), si no -> lateral/bajista (-1)
            trend_direction = 1.0 if fast_ma > slow_ma else -1.0
            
            # Fuerza de la tendencia (distancia relativa entre EMAs)
            trend_strength = abs(ema_cross_diff_pct) / 100.0  # Normalizado a 0-1
            
            # Señal de acción (one-hot)
            signal_buy = 1 if signal.get("action") == "BUY" else 0
            signal_sell = 1 if signal.get("action") == "SELL" else 0
            
            # Contexto del bot (normalizado)
            daily_pnl_normalized = bot_state.get("daily_pnl_normalized", 0.0)
            consecutive_signals = bot_state.get("consecutive_signals", 0)
            daily_trades_normalized = bot_state.get("daily_trades", 0) / 200.0  # Normalizar a 0-1 (asumiendo max ~200)
            
            # Construir DataFrame con features relativas
            data = {
                # Features relativas (CRÍTICAS para generalización)
                "ema_fast_diff_pct": ema_fast_diff_pct,
                "ema_slow_diff_pct": ema_slow_diff_pct,
                "ema_cross_diff_pct": ema_cross_diff_pct,
                "atr_pct": atr_pct,
                "rsi_normalized": rsi_normalized,
                "macd_pct": macd_pct,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                
                # Señal (discreta)
                "signal_buy": signal_buy,
                "signal_sell": signal_sell,
                
                # Contexto del bot (normalizado)
                "daily_pnl_normalized": daily_pnl_normalized,
                "consecutive_signals": consecutive_signals,
                "daily_trades_normalized": daily_trades_normalized,
                
                # Características temporales
                "hour": datetime.utcnow().hour / 24.0,  # Normalizado 0-1
            }
            
            # Mantener compatibilidad con modelos antiguos (features absolutas)
            # Si el modelo espera features absolutas, incluirlas también
            if "price" in self.expected_features or len(self.expected_features) == 0:
                data.update({
                    "price": price,
                    "rsi": rsi,
                    "atr": atr,
                })

            df = pd.DataFrame([data])

            # si el modelo espera columnas específicas
            for col in self.expected_features:
                if col not in df.columns:
                    df[col] = 0

            if self.expected_features:
                df = df[self.expected_features]

            return df

        except Exception as e:
            self.logger.error(f"❌ Error armando features: {e}")
            return None

    # ======================================================
    # 🧠 DECISIÓN
    # ======================================================
    def _make_decision(self, p_win: float) -> Dict[str, Any]:

        approved = p_win >= self.min_probability
        confidence = abs(p_win - 0.5) * 2

        return {
            "approved": approved,
            "probability": p_win,
            "confidence": confidence,
            "recommended_rr": 2.0,
            "size_multiplier": 1.0 if approved else 0.0,
            "reason": (
                "Aprobado por ML"
                if approved
                else "Probabilidad insuficiente"
            ),
        }

    # ======================================================
    # 🛟 FALLBACK
    # ======================================================
    def _default_approval(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "approved": True,
            "probability": 0.5,
            "confidence": 0.3,
            "recommended_rr": 2.0,
            "size_multiplier": 1.0,
            "reason": "Sin ML (fallback)",
        }
