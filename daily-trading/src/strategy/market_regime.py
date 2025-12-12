"""
Clasificador de Régimen de Mercado
Analiza el mercado diariamente y clasifica el régimen actual para adaptar la estrategia
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import pandas as pd
import numpy as np
from src.utils.logging_setup import setup_logging


class MarketRegime(Enum):
    """Tipos de régimen de mercado"""
    TRENDING_BULLISH = "trending_bullish"
    TRENDING_BEARISH = "trending_bearish"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CHAOTIC = "chaotic"


class MarketRegimeClassifier:
    """
    Clasifica el régimen de mercado diario basándose en:
    - Tendencia (pendiente de medias largas)
    - Volatilidad (ATR relativo)
    - Volumen (distribución y media)
    - Rango diario (High-Low)
    - Breakouts
    """

    def __init__(self, config):
        self.config = config
        self.logger = setup_logging(__name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        
        # Estado actual
        self.current_regime: Optional[MarketRegime] = None
        self.regime_confidence: float = 0.0
        self.regime_metrics: Dict[str, Any] = {}
        
        # Histórico para análisis
        self.historical_data: Optional[pd.DataFrame] = None
        self.last_analysis_date: Optional[datetime] = None

    async def analyze_daily_regime(self, historical_data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Análisis diario completo del régimen de mercado
        
        Args:
            historical_data: DataFrame con OHLCV y indicadores (últimos 30-90 días)
            symbol: Símbolo del activo
            
        Returns:
            Dict con régimen, confianza y métricas
        """
        try:
            self.logger.info(f"🔍 Analizando régimen de mercado para {symbol}...")
            
            if historical_data is None or len(historical_data) < 20:
                self.logger.warning("⚠️ Datos insuficientes para análisis de régimen")
                return self._default_regime()
            
            self.historical_data = historical_data.copy()
            self.last_analysis_date = datetime.now()
            
            # Calcular métricas clave
            metrics = self._calculate_regime_metrics(historical_data)
            
            # Clasificar régimen
            regime = self._classify_regime(metrics)
            
            # Calcular confianza
            confidence = self._calculate_confidence(metrics)
            
            self.current_regime = regime
            self.regime_confidence = confidence
            self.regime_metrics = metrics
            
            result = {
                "regime": regime.value,
                "confidence": confidence,
                "metrics": metrics,
                "analysis_date": self.last_analysis_date,
                "symbol": symbol
            }
            
            self.logger.info(
                f"✅ Régimen detectado: {regime.value.upper()} "
                f"(confianza: {confidence:.2%})"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando régimen: {e}")
            return self._default_regime()

    def _calculate_regime_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calcula todas las métricas necesarias para clasificar el régimen"""
        try:
            metrics = {}
            
            # 1. TENDENCIA: Pendiente de medias largas (EMA50, EMA200)
            if 'close' in df.columns and len(df) >= 50:
                df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
                if len(df) >= 200:
                    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
                else:
                    df['ema_200'] = df['close'].ewm(span=len(df), adjust=False).mean()
                
                # Pendiente de EMA50 (últimos 20 períodos)
                recent_ema50 = df['ema_50'].tail(20)
                if len(recent_ema50) >= 2:
                    ema50_slope = (recent_ema50.iloc[-1] - recent_ema50.iloc[0]) / len(recent_ema50)
                    ema50_slope_pct = (ema50_slope / recent_ema50.iloc[0]) * 100 if recent_ema50.iloc[0] != 0 else 0
                else:
                    ema50_slope_pct = 0
                
                # Relación EMA50 vs EMA200
                current_ema50 = df['ema_50'].iloc[-1]
                current_ema200 = df['ema_200'].iloc[-1]
                ema_diff_pct = ((current_ema50 - current_ema200) / current_ema200) * 100 if current_ema200 != 0 else 0
                
                metrics['ema50_slope_pct'] = ema50_slope_pct
                metrics['ema_diff_pct'] = ema_diff_pct
                metrics['trend_direction'] = 'bullish' if ema_diff_pct > 1 else ('bearish' if ema_diff_pct < -1 else 'neutral')
            
            # 2. VOLATILIDAD: ATR relativo
            if 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
                # Calcular ATR (14 períodos)
                df['tr'] = np.maximum(
                    df['high'] - df['low'],
                    np.maximum(
                        abs(df['high'] - df['close'].shift(1)),
                        abs(df['low'] - df['close'].shift(1))
                    )
                )
                df['atr'] = df['tr'].rolling(window=14).mean()
                
                # ATR relativo (ATR / precio)
                current_price = df['close'].iloc[-1]
                current_atr = df['atr'].iloc[-1]
                atr_relative = (current_atr / current_price) if current_price > 0 else 0
                
                # Comparar con ATR histórico (percentil)
                atr_percentile = (df['atr'].iloc[-1] > df['atr']).sum() / len(df['atr']) * 100
                
                metrics['atr_relative'] = atr_relative
                metrics['atr_percentile'] = atr_percentile
                metrics['volatility_level'] = 'high' if atr_percentile > 75 else ('low' if atr_percentile < 25 else 'medium')
            
            # 3. VOLUMEN: Media y distribución
            if 'volume' in df.columns:
                volume_mean = df['volume'].mean()
                volume_std = df['volume'].std()
                current_volume = df['volume'].iloc[-1]
                
                # Volumen relativo
                volume_relative = (current_volume / volume_mean) if volume_mean > 0 else 1
                
                # Tendencia de volumen (últimos 20 períodos vs anteriores)
                recent_volume = df['volume'].tail(20).mean()
                previous_volume = df['volume'].tail(40).head(20).mean()
                volume_trend = (recent_volume / previous_volume - 1) if previous_volume > 0 else 0
                
                metrics['volume_mean'] = volume_mean
                metrics['volume_relative'] = volume_relative
                metrics['volume_trend'] = volume_trend
            
            # 4. RANGO DIARIO: High-Low promedio
            if 'high' in df.columns and 'low' in df.columns:
                df['daily_range'] = df['high'] - df['low']
                df['daily_range_pct'] = (df['daily_range'] / df['close']) * 100
                
                avg_range_pct = df['daily_range_pct'].tail(20).mean()
                current_range_pct = df['daily_range_pct'].iloc[-1]
                
                metrics['avg_daily_range_pct'] = avg_range_pct
                metrics['current_range_pct'] = current_range_pct
            
            # 5. BREAKOUTS: Máximos/mínimos recientes
            if 'high' in df.columns and 'low' in df.columns:
                # Máximo/mínimo de 20 períodos
                high_20 = df['high'].tail(20).max()
                low_20 = df['low'].tail(20).min()
                current_high = df['high'].iloc[-1]
                current_low = df['low'].iloc[-1]
                
                # ¿Estamos cerca de un breakout?
                near_high_breakout = (current_high / high_20) > 0.98
                near_low_breakout = (current_low / low_20) < 1.02
                
                metrics['near_high_breakout'] = near_high_breakout
                metrics['near_low_breakout'] = near_low_breakout
            
            # 6. EFICIENCIA DE TENDENCIA (qué tan "limpia" es la tendencia)
            if 'close' in df.columns and len(df) >= 20:
                # Comparar movimiento real vs movimiento neto
                price_change = abs(df['close'].iloc[-1] - df['close'].iloc[-20])
                cumulative_movement = df['close'].diff().abs().tail(20).sum()
                
                trend_efficiency = (price_change / cumulative_movement) if cumulative_movement > 0 else 0
                metrics['trend_efficiency'] = trend_efficiency
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas de régimen: {e}")
            return {}

    def _classify_regime(self, metrics: Dict[str, Any]) -> MarketRegime:
        """Clasifica el régimen basándose en las métricas"""
        try:
            # Extraer métricas clave
            ema_diff = metrics.get('ema_diff_pct', 0)
            ema_slope = metrics.get('ema50_slope_pct', 0)
            atr_relative = metrics.get('atr_relative', 0)
            atr_percentile = metrics.get('atr_percentile', 50)
            trend_efficiency = metrics.get('trend_efficiency', 0)
            
            # Prioridad 1: CAÓTICO (alta volatilidad + baja eficiencia)
            if atr_percentile > 85 and trend_efficiency < 0.3:
                return MarketRegime.CHAOTIC
            
            # Prioridad 2: ALTA VOLATILIDAD (pero con algo de tendencia)
            if atr_percentile > 75:
                return MarketRegime.HIGH_VOLATILITY
            
            # Prioridad 3: BAJA VOLATILIDAD
            if atr_percentile < 20:
                return MarketRegime.LOW_VOLATILITY
            
            # Prioridad 4: TENDENCIAS (si hay eficiencia y pendiente clara)
            if trend_efficiency > 0.5:
                if ema_diff > 2 and ema_slope > 0:
                    return MarketRegime.TRENDING_BULLISH
                elif ema_diff < -2 and ema_slope < 0:
                    return MarketRegime.TRENDING_BEARISH
            
            # Prioridad 5: RANGO (por defecto si no hay tendencia clara)
            return MarketRegime.RANGING
            
        except Exception as e:
            self.logger.error(f"❌ Error clasificando régimen: {e}")
            return MarketRegime.RANGING

    def _calculate_confidence(self, metrics: Dict[str, Any]) -> float:
        """Calcula la confianza de la clasificación del régimen"""
        try:
            confidence_factors = []
            
            # Factor 1: Claridad de tendencia
            ema_diff = abs(metrics.get('ema_diff_pct', 0))
            trend_confidence = min(1.0, ema_diff / 5)  # 5% = 100% confianza
            confidence_factors.append(trend_confidence)
            
            # Factor 2: Consistencia de volatilidad
            atr_percentile = metrics.get('atr_percentile', 50)
            volatility_confidence = abs(atr_percentile - 50) / 50  # Extremos = más confianza
            confidence_factors.append(volatility_confidence)
            
            # Factor 3: Eficiencia de tendencia
            trend_efficiency = metrics.get('trend_efficiency', 0)
            confidence_factors.append(trend_efficiency)
            
            # Factor 4: Volumen (más volumen = más confianza)
            volume_relative = metrics.get('volume_relative', 1)
            volume_confidence = min(1.0, volume_relative)
            confidence_factors.append(volume_confidence)
            
            # Promedio ponderado
            total_confidence = np.mean(confidence_factors)
            
            return max(0.3, min(1.0, total_confidence))  # Entre 30% y 100%
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando confianza: {e}")
            return 0.5

    def _default_regime(self) -> Dict[str, Any]:
        """Retorna un régimen por defecto cuando no hay datos suficientes"""
        return {
            "regime": MarketRegime.RANGING.value,
            "confidence": 0.3,
            "metrics": {},
            "analysis_date": datetime.now(),
            "symbol": "UNKNOWN"
        }

    def get_current_regime(self) -> Optional[MarketRegime]:
        """Retorna el régimen actual"""
        return self.current_regime

    def get_regime_metrics(self) -> Dict[str, Any]:
        """Retorna las métricas del régimen actual"""
        return self.regime_metrics

    def should_reanalyze(self) -> bool:
        """Determina si es necesario re-analizar el régimen (una vez por día)"""
        if self.last_analysis_date is None:
            return True
        
        # Re-analizar si pasó más de 1 día
        return (datetime.now() - self.last_analysis_date) > timedelta(days=1)

