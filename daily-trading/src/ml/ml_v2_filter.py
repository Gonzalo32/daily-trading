"""
ML v2 Confidence Filter
Uses percentile-based filtering (not fixed probability threshold)
Target: r_multiple > 0 (market-dependent)
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime

from src.utils.logging_setup import setup_logging

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    joblib = None


class MLV2Filter:
    """
    ML v2 Confidence Filter
    
    Filters signals based on percentile ranking of ML scores.
    - PAPER mode: top 30% (default)
    - LIVE mode: top 20% (default)
    
    Does NOT make decisions, only gates execution.
    Original strategy signal is preserved in DecisionSample.
    """
    
    def __init__(
        self,
        model_path: str = "models/ml_v2_model.pkl",
        paper_threshold_percentile: float = 70.0,
        live_threshold_percentile: float = 80.0,
        trading_mode: str = "PAPER"
    ):
        self.model_path = model_path
        self.paper_threshold_percentile = paper_threshold_percentile
        self.live_threshold_percentile = live_threshold_percentile
        self.trading_mode = trading_mode.upper()
        
        self.model = None
        self.model_loaded = False
        self.expected_features = []
        self.score_history = []
        
        self.logger = setup_logging(__name__)
        self.logger.info(
            f"ML v2 Filter iniciado | Mode: {self.trading_mode} | "
            f"Threshold: {self._get_threshold_percentile()}%"
        )
        
        self.load_model()
    
    def _get_threshold_percentile(self) -> float:
        """Get threshold percentile based on trading mode"""
        if self.trading_mode == "LIVE":
            return self.live_threshold_percentile
        return self.paper_threshold_percentile
    
    def load_model(self) -> bool:
        """Load ML v2 model"""
        try:
            if not JOBLIB_AVAILABLE:
                self.logger.warning(
                    "joblib no disponible. ML v2 deshabilitado."
                )
                self.model_loaded = False
                return False
            
            if not os.path.exists(self.model_path):
                self.logger.warning(
                    f"Modelo ML v2 no encontrado en {self.model_path}. "
                    "Se continúa sin ML v2."
                )
                self.model_loaded = False
                return False
            
            self.model = joblib.load(self.model_path)
            self.model_loaded = True
            
            if hasattr(self.model, "feature_names_in_"):
                self.expected_features = list(self.model.feature_names_in_)
            
            self.logger.info("Modelo ML v2 cargado correctamente.")
            return True
            
        except Exception as e:
            self.logger.exception(f"Error cargando modelo ML v2: {e}")
            self.model_loaded = False
            return False
    
    def is_model_available(self) -> bool:
        """Check if model is loaded and available"""
        return self.model_loaded and self.model is not None
    
    def _build_features(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Build features for ML v2 model.
        Features must match ml_v2_dataset.csv schema.
        """
        try:
            price = market_data.get("price", 0)
            indicators = market_data.get("indicators", {})
            regime_info = market_data.get("regime_info", {})
            
            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            atr = indicators.get("atr", 0)
            
            ema_cross_diff_pct = ((fast_ma - slow_ma) / slow_ma * 100) if slow_ma > 0 else 0
            atr_pct = (atr / price * 100) if price > 0 else 0
            price_to_fast_pct = ((price - fast_ma) / fast_ma * 100) if fast_ma > 0 else 0
            price_to_slow_pct = ((price - slow_ma) / slow_ma * 100) if slow_ma > 0 else 0
            
            trend_direction = 1.0 if fast_ma > slow_ma else (-1.0 if fast_ma < slow_ma else 0.0)
            trend_strength = abs(ema_cross_diff_pct) / 100.0
            
            regime = regime_info.get("regime", "unknown")
            volatility_level = regime_info.get("volatility", "normal")
            if isinstance(volatility_level, (int, float)):
                if volatility_level > 0.7:
                    volatility_level = "high"
                elif volatility_level < 0.3:
                    volatility_level = "low"
                else:
                    volatility_level = "normal"
            
            strategy_signal = signal.get("action", "NONE").upper()
            
            data = {
                "ema_cross_diff_pct": ema_cross_diff_pct,
                "atr_pct": atr_pct,
                "price_to_fast_pct": price_to_fast_pct,
                "price_to_slow_pct": price_to_slow_pct,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                "regime": regime,
                "volatility_level": volatility_level,
                "strategy_signal": strategy_signal
            }
            
            df = pd.DataFrame([data])
            
            regime_dummies = pd.get_dummies(df["regime"], prefix="regime", dummy_na=False)
            volatility_dummies = pd.get_dummies(df["volatility_level"], prefix="volatility_level", dummy_na=False)
            signal_dummies = pd.get_dummies(df["strategy_signal"], prefix="strategy_signal", dummy_na=False)
            
            df = pd.concat([df, regime_dummies, volatility_dummies, signal_dummies], axis=1)
            df = df.drop(columns=["regime", "volatility_level", "strategy_signal"])
            
            if self.expected_features:
                for col in self.expected_features:
                    if col not in df.columns:
                        df[col] = 0
                df = df[self.expected_features]
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error construyendo features ML v2: {e}")
            return None
    
    def _calculate_percentile(self, score: float) -> float:
        """
        Calculate percentile of current score relative to history.
        If no history, assume it's in top 50% (pass).
        """
        if len(self.score_history) < 10:
            return 50.0
        
        history_array = np.array(self.score_history)
        percentile = (history_array < score).sum() / len(history_array) * 100.0
        return percentile
    
    async def filter_signal(
        self,
        signal: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Filter signal based on ML v2 confidence percentile.
        
        Returns:
            {
                "approved": bool,
                "ml_score": float,
                "percentile": float,
                "threshold_percentile": float,
                "reason": str
            }
        """
        if not self.is_model_available():
            return {
                "approved": True,
                "ml_score": 0.5,
                "percentile": 50.0,
                "threshold_percentile": self._get_threshold_percentile(),
                "reason": "ML v2 no disponible (fallback: aprobar)"
            }
        
        features = self._build_features(signal, market_data)
        
        if features is None:
            return {
                "approved": True,
                "ml_score": 0.5,
                "percentile": 50.0,
                "threshold_percentile": self._get_threshold_percentile(),
                "reason": "Error construyendo features (fallback: aprobar)"
            }
        
        try:
            proba = self.model.predict_proba(features)
            ml_score = float(proba[0][1])
            
            self.score_history.append(ml_score)
            if len(self.score_history) > 1000:
                self.score_history = self.score_history[-1000:]
            
            percentile = self._calculate_percentile(ml_score)
            threshold = self._get_threshold_percentile()
            
            approved = percentile >= threshold
            
            reason = (
                f"ML v2 aprobado (percentil: {percentile:.1f}% >= {threshold}%)"
                if approved
                else f"ML v2 rechazado (percentil: {percentile:.1f}% < {threshold}%)"
            )
            
            self.logger.info(
                f"ML v2 Filter | Score: {ml_score:.4f} | "
                f"Percentil: {percentile:.1f}% | "
                f"Threshold: {threshold}% | "
                f"Aprobado: {approved}"
            )
            
            return {
                "approved": approved,
                "ml_score": ml_score,
                "percentile": percentile,
                "threshold_percentile": threshold,
                "reason": reason
            }
            
        except Exception as e:
            self.logger.error(f"Error en predicción ML v2: {e}")
            return {
                "approved": True,
                "ml_score": 0.5,
                "percentile": 50.0,
                "threshold_percentile": self._get_threshold_percentile(),
                "reason": f"Error en predicción (fallback: aprobar): {str(e)}"
            }
