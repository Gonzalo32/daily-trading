"""
Filtro ML de Señales
Usa Machine Learning para filtrar señales y predecir probabilidad de éxito
"""

import os
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from datetime import datetime

from src.ml.ml_model import TradingMLModel
from src.utils.logging_setup import setup_logging


class MLSignalFilter:
    """
    Filtro inteligente de señales usando Machine Learning
    
    Funciones:
    - Predecir probabilidad de éxito de una señal (p_win)
    - Recomendar ajustes de RR (risk/reward) óptimo
    - Filtrar señales de baja calidad
    """

    def __init__(self, config):
        self.config = config
        self.logger = setup_logging(__name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        
        # Modelo principal (probabilidad de éxito)
        self.model: Optional[TradingMLModel] = None
        self.model_loaded = False
        
        # Umbrales
        self.min_probability = 0.55  # Mínimo 55% de probabilidad para operar
        self.high_probability = 0.70  # 70%+ = señal muy fuerte
        
        # Features esperadas por el modelo
        self.expected_features = [
            # Técnicos
            'rsi', 'macd', 'macd_signal', 'fast_ma', 'slow_ma', 'atr',
            'ma_diff_pct', 'rsi_normalized', 'macd_strength',
            # Contexto
            'volatility_normalized', 'volume_relative', 'hour_of_day',
            'regime_trending_bullish', 'regime_trending_bearish', 'regime_ranging',
            'regime_high_volatility', 'regime_low_volatility', 'regime_chaotic',
            # Estado del bot
            'daily_pnl_normalized', 'daily_trades', 'consecutive_signals',
            # Señal
            'signal_strength', 'signal_buy', 'signal_sell',
        ]
        
        # Intentar cargar modelo si existe
        self._try_load_model()

    def _try_load_model(self):
        """Intenta cargar el modelo ML si existe"""
        try:
            if not self.config.ENABLE_ML:
                self.logger.info("ℹ️ ML deshabilitado en configuración")
                return
            
            model_path = os.path.join(self.config.ML_MODEL_PATH, "signal_filter_model.pkl")
            
            if os.path.exists(model_path):
                self.model = TradingMLModel(model_path=model_path)
                self.model.load_model()
                self.model_loaded = True
                self.logger.info(f"✅ Modelo ML cargado desde {model_path}")
            else:
                self.logger.warning(f"⚠️ Modelo ML no encontrado en {model_path}")
                self.logger.info("ℹ️ El bot operará sin filtro ML hasta que se entrene un modelo")
                
        except Exception as e:
            self.logger.error(f"❌ Error cargando modelo ML: {e}")
            self.model_loaded = False

    async def filter_signal(
        self, 
        signal: Dict[str, Any], 
        market_data: Dict[str, Any],
        regime_info: Dict[str, Any],
        bot_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Filtra una señal usando ML
        
        Args:
            signal: Señal generada por la estrategia
            market_data: Datos actuales del mercado
            regime_info: Información del régimen de mercado
            bot_state: Estado actual del bot (PnL, trades, etc.)
            
        Returns:
            Dict con decisión y probabilidades:
            {
                'approved': bool,
                'probability': float,
                'confidence': float,
                'recommended_rr': float,
                'size_multiplier': float,
                'reason': str
            }
        """
        try:
            # Si no hay modelo, aprobar por defecto (modo conservador)
            if not self.model_loaded or self.model is None:
                return self._default_approval(signal)
            
            # Construir features
            features = self._build_features(signal, market_data, regime_info, bot_state)
            
            if features is None:
                self.logger.warning("⚠️ No se pudieron construir features, aprobando señal por defecto")
                return self._default_approval(signal)
            
            # Predecir probabilidad de éxito
            try:
                proba = self.model.predict_proba(features)
                p_win = proba[0][1]  # Probabilidad de clase positiva (trade exitoso)
            except Exception as e:
                self.logger.error(f"❌ Error en predicción ML: {e}")
                return self._default_approval(signal)
            
            # Tomar decisión
            decision = self._make_decision(p_win, signal, features)
            
            self.logger.info(
                f"🧠 ML Filter: {signal['action']} - "
                f"P(win)={p_win:.2%} - "
                f"{'✅ APPROVED' if decision['approved'] else '❌ REJECTED'}"
            )
            
            return decision
            
        except Exception as e:
            self.logger.error(f"❌ Error en filtro ML: {e}")
            return self._default_approval(signal)

    def _build_features(
        self,
        signal: Dict[str, Any],
        market_data: Dict[str, Any],
        regime_info: Dict[str, Any],
        bot_state: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        """Construye el vector de features para el modelo"""
        try:
            indicators = market_data.get('indicators', {})
            price = market_data.get('price', 0)
            volume = market_data.get('volume', 0)
            
            # Obtener métricas de régimen
            regime_metrics = regime_info.get('metrics', {})
            regime_str = regime_info.get('regime', 'ranging')
            
            # Timestamp para hora del día
            timestamp = market_data.get('timestamp', datetime.now())
            hour_of_day = timestamp.hour if hasattr(timestamp, 'hour') else 12
            
            # Construir features
            features_dict = {}
            
            # 1. TÉCNICOS
            features_dict['rsi'] = indicators.get('rsi', 50)
            features_dict['macd'] = indicators.get('macd', 0)
            features_dict['macd_signal'] = indicators.get('macd_signal', 0)
            features_dict['fast_ma'] = indicators.get('fast_ma', price)
            features_dict['slow_ma'] = indicators.get('slow_ma', price)
            features_dict['atr'] = indicators.get('atr', 0)
            
            # Features derivadas
            slow_ma = features_dict['slow_ma']
            features_dict['ma_diff_pct'] = ((features_dict['fast_ma'] - slow_ma) / slow_ma * 100) if slow_ma != 0 else 0
            features_dict['rsi_normalized'] = (features_dict['rsi'] - 50) / 50  # Normalizar a [-1, 1]
            
            macd_signal = features_dict['macd_signal']
            features_dict['macd_strength'] = (features_dict['macd'] / macd_signal) if macd_signal != 0 else 0
            
            # 2. CONTEXTO DE MERCADO
            atr = features_dict['atr']
            features_dict['volatility_normalized'] = (atr / price) if price > 0 else 0
            
            volume_mean = regime_metrics.get('volume_mean', volume)
            features_dict['volume_relative'] = (volume / volume_mean) if volume_mean > 0 else 1.0
            
            features_dict['hour_of_day'] = hour_of_day
            
            # 3. RÉGIMEN DE MERCADO (one-hot encoding)
            features_dict['regime_trending_bullish'] = 1 if regime_str == 'trending_bullish' else 0
            features_dict['regime_trending_bearish'] = 1 if regime_str == 'trending_bearish' else 0
            features_dict['regime_ranging'] = 1 if regime_str == 'ranging' else 0
            features_dict['regime_high_volatility'] = 1 if regime_str == 'high_volatility' else 0
            features_dict['regime_low_volatility'] = 1 if regime_str == 'low_volatility' else 0
            features_dict['regime_chaotic'] = 1 if regime_str == 'chaotic' else 0
            
            # 4. ESTADO DEL BOT
            daily_pnl = bot_state.get('daily_pnl', 0)
            initial_capital = self.config.INITIAL_CAPITAL
            features_dict['daily_pnl_normalized'] = (daily_pnl / initial_capital) if initial_capital > 0 else 0
            features_dict['daily_trades'] = bot_state.get('daily_trades', 0)
            features_dict['consecutive_signals'] = bot_state.get('consecutive_signals', 0)
            
            # 5. SEÑAL
            features_dict['signal_strength'] = signal.get('strength', 0)
            features_dict['signal_buy'] = 1 if signal.get('action') == 'BUY' else 0
            features_dict['signal_sell'] = 1 if signal.get('action') == 'SELL' else 0
            
            # Crear DataFrame con las features en el orden esperado
            df = pd.DataFrame([features_dict])
            
            # Asegurar que todas las features esperadas estén presentes
            for feature in self.expected_features:
                if feature not in df.columns:
                    df[feature] = 0  # Rellenar con 0 si falta
            
            # Mantener solo las features esperadas en el orden correcto
            df = df[self.expected_features]
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error construyendo features: {e}")
            return None

    def _make_decision(self, p_win: float, signal: Dict[str, Any], features: pd.DataFrame) -> Dict[str, Any]:
        """Toma la decisión final basada en la probabilidad"""
        
        # Decisión base: aprobar si p_win > umbral mínimo
        approved = p_win >= self.min_probability
        
        # Confianza de la predicción
        confidence = abs(p_win - 0.5) * 2  # 0.5 = sin confianza, 0/1 = máxima confianza
        
        # Recommended Risk/Reward basado en probabilidad
        # Mayor probabilidad = más agresivo en TP
        if p_win >= self.high_probability:
            recommended_rr = 3.0  # Muy buena señal = dejar correr
        elif p_win >= 0.60:
            recommended_rr = 2.5  # Buena señal
        else:
            recommended_rr = 1.5  # Señal marginal = conservador
        
        # Size multiplier basado en probabilidad y confianza
        # p_win alto + confianza alta = tamaño mayor (dentro de límites de riesgo)
        if p_win >= self.high_probability and confidence > 0.6:
            size_multiplier = 1.3  # 30% más grande
        elif p_win >= 0.60:
            size_multiplier = 1.1  # 10% más grande
        elif p_win < self.min_probability:
            size_multiplier = 0.0  # No operar
        else:
            size_multiplier = 0.8  # 20% más pequeño (señal débil)
        
        # Razón de la decisión
        if not approved:
            reason = f"Probabilidad baja ({p_win:.2%} < {self.min_probability:.2%})"
        elif p_win >= self.high_probability:
            reason = f"Señal muy fuerte ({p_win:.2%})"
        elif p_win >= 0.60:
            reason = f"Señal buena ({p_win:.2%})"
        else:
            reason = f"Señal aceptable ({p_win:.2%})"
        
        return {
            'approved': approved,
            'probability': p_win,
            'confidence': confidence,
            'recommended_rr': recommended_rr,
            'size_multiplier': size_multiplier,
            'reason': reason
        }

    def _default_approval(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Aprobación por defecto cuando no hay modelo"""
        return {
            'approved': True,  # Aprobar por defecto
            'probability': 0.5,  # Neutral
            'confidence': 0.3,  # Baja confianza
            'recommended_rr': 2.0,  # RR estándar
            'size_multiplier': 1.0,  # Tamaño normal
            'reason': 'Sin modelo ML - aprobación por defecto'
        }

    def set_min_probability(self, min_prob: float):
        """Ajusta el umbral mínimo de probabilidad"""
        self.min_probability = max(0.5, min(0.9, min_prob))
        self.logger.info(f"🔧 Umbral mínimo de probabilidad ajustado a {self.min_probability:.2%}")

    def is_model_available(self) -> bool:
        """Verifica si el modelo está cargado y disponible"""
        return self.model_loaded and self.model is not None

    def get_model_info(self) -> Dict[str, Any]:
        """Retorna información sobre el modelo"""
        return {
            'loaded': self.model_loaded,
            'min_probability': self.min_probability,
            'high_probability': self.high_probability,
            'expected_features': len(self.expected_features),
            'model_path': os.path.join(self.config.ML_MODEL_PATH, "signal_filter_model.pkl") if self.config.ENABLE_ML else None
        }

