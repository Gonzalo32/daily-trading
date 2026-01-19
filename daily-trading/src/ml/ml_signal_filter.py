"""
Filtro ML de Señales
Usa Machine Learning para filtrar señales y predecir probabilidad de éxito
"""
                                                                                         

import os
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime

from src.utils.logging_setup import setup_logging

                                                    
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

                                                            
              
                                                            
    def load_model(self) -> bool:
        try:
                                                 
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

                                                            
                                    
                                                            
    def is_model_available(self) -> bool:
        return self.model_loaded and self.model is not None

                                                            
                        
                                                            
    async def filter_signal(
        self,
        signal: Dict[str, Any],
        market_data: Dict[str, Any],
        regime_info: Dict[str, Any],
        bot_state: Dict[str, Any]
    ) -> Dict[str, Any]:

                                          
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
            
                                                       
                                                     
                                                      
                                                                           
                                                             
                                                     
            
                                         
            ema_fast_diff_pct = ((fast_ma - price) / price * 100) if price > 0 else 0
            ema_slow_diff_pct = ((slow_ma - price) / price * 100) if price > 0 else 0
            ema_cross_diff_pct = ((fast_ma - slow_ma) / slow_ma * 100) if slow_ma > 0 else 0
            atr_pct = (atr / price * 100) if price > 0 else 0
            
                                                            
            rsi_normalized = (rsi - 50) / 50                                   
            
                                     
            macd_pct = (macd / price * 100) if price > 0 and price != 0 else 0
            
                                                   
                                                                                          
            trend_direction = 1.0 if fast_ma > slow_ma else -1.0
            
                                                                    
            trend_strength = abs(ema_cross_diff_pct) / 100.0                     
            
                                       
            signal_buy = 1 if signal.get("action") == "BUY" else 0
            signal_sell = 1 if signal.get("action") == "SELL" else 0
            
                                            
            daily_pnl_normalized = bot_state.get("daily_pnl_normalized", 0.0)
            consecutive_signals = bot_state.get("consecutive_signals", 0)
            daily_trades_normalized = bot_state.get("daily_trades", 0) / 200.0                                         
            
                                                        
            data = {
                                                                   
                "ema_fast_diff_pct": ema_fast_diff_pct,
                "ema_slow_diff_pct": ema_slow_diff_pct,
                "ema_cross_diff_pct": ema_cross_diff_pct,
                "atr_pct": atr_pct,
                "rsi_normalized": rsi_normalized,
                "macd_pct": macd_pct,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                
                                  
                "signal_buy": signal_buy,
                "signal_sell": signal_sell,
                
                                                
                "daily_pnl_normalized": daily_pnl_normalized,
                "consecutive_signals": consecutive_signals,
                "daily_trades_normalized": daily_trades_normalized,
                
                                            
                "hour": datetime.utcnow().hour / 24.0,                   
            }
            
                                                                               
                                                                        
            forbidden = {"price", "rsi", "atr"}
            if self.expected_features and any(f in forbidden for f in self.expected_features):
                self.logger.warning(
                    "⚠️ Modelo ML espera features absolutas (price/rsi/atr). "
                    "Se enviarán como 0 para evitar aprendizaje por valor absoluto."
                )

            df = pd.DataFrame([data])

                                                      
            for col in self.expected_features:
                if col not in df.columns:
                    df[col] = 0

            if self.expected_features:
                df = df[self.expected_features]

            return df

        except Exception as e:
            self.logger.error(f"❌ Error armando features: {e}")
            return None

                                                            
                
                                                            
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

                                                            
                
                                                            
    def _default_approval(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "approved": True,
            "probability": 0.5,
            "confidence": 0.3,
            "recommended_rr": 2.0,
            "size_multiplier": 1.0,
            "reason": "Sin ML (fallback)",
        }
