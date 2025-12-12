"""
Gestor de Parámetros Dinámicos
Adapta los parámetros de trading según el régimen de mercado detectado
"""

from typing import Dict, Any
from src.strategy.market_regime import MarketRegime
from src.utils.logging_setup import setup_logging


class DynamicParameterManager:
    """
    Adapta parámetros de trading según el régimen de mercado:
    - Umbrales de volumen
    - Umbrales de volatilidad
    - Fuerza mínima de señal
    - Umbrales RSI
    - Stop Loss y Take Profit
    - Máximo de trades permitidos
    """

    def __init__(self, config):
        self.config = config
        self.logger = setup_logging(__name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        
        # Parámetros base (de configuración)
        self.base_params = {
            'risk_per_trade': config.RISK_PER_TRADE,
            'stop_loss_pct': config.STOP_LOSS_PCT,
            'take_profit_ratio': config.TAKE_PROFIT_RATIO,
            'rsi_overbought': config.RSI_OVERBOUGHT,
            'rsi_oversold': config.RSI_OVERSOLD,
            'max_daily_loss': config.MAX_DAILY_LOSS,
        }
        
        # Parámetros actuales (adaptados)
        self.current_params: Dict[str, Any] = self.base_params.copy()

    def adapt_parameters(self, regime_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapta todos los parámetros según el régimen de mercado
        
        Args:
            regime_info: Dict con régimen, confianza y métricas
            
        Returns:
            Dict con parámetros adaptados
        """
        try:
            regime_str = regime_info.get('regime', 'ranging')
            confidence = regime_info.get('confidence', 0.5)
            metrics = regime_info.get('metrics', {})
            
            # Convertir string a enum
            regime = MarketRegime(regime_str)
            
            self.logger.info(f"🔧 Adaptando parámetros para régimen: {regime.value}")
            
            # Copiar parámetros base
            adapted = self.base_params.copy()
            
            # Adaptar según régimen
            if regime == MarketRegime.HIGH_VOLATILITY or regime == MarketRegime.CHAOTIC:
                adapted = self._adapt_high_volatility(adapted, metrics, confidence)
                
            elif regime == MarketRegime.LOW_VOLATILITY:
                adapted = self._adapt_low_volatility(adapted, metrics, confidence)
                
            elif regime == MarketRegime.TRENDING_BULLISH:
                adapted = self._adapt_trending_bullish(adapted, metrics, confidence)
                
            elif regime == MarketRegime.TRENDING_BEARISH:
                adapted = self._adapt_trending_bearish(adapted, metrics, confidence)
                
            elif regime == MarketRegime.RANGING:
                adapted = self._adapt_ranging(adapted, metrics, confidence)
            
            # Agregar configuración de trading style
            adapted['trading_style'] = self._determine_trading_style(regime)
            adapted['regime'] = regime.value
            adapted['confidence'] = confidence
            
            self.current_params = adapted
            
            self.logger.info(
                f"✅ Parámetros adaptados: "
                f"SL={adapted['stop_loss_pct']:.3%}, "
                f"TP={adapted['take_profit_ratio']:.1f}R, "
                f"Risk={adapted['risk_per_trade']:.2%}, "
                f"Style={adapted['trading_style']}"
            )
            
            return adapted
            
        except Exception as e:
            self.logger.error(f"❌ Error adaptando parámetros: {e}")
            return self.base_params.copy()

    def _adapt_high_volatility(self, params: Dict[str, Any], metrics: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Parámetros para alta volatilidad / mercado caótico"""
        
        # Stop Loss más amplio (pero menor tamaño de posición)
        atr_relative = metrics.get('atr_relative', 0.02)
        params['stop_loss_pct'] = max(0.015, min(0.03, atr_relative * 1.5))
        
        # Riesgo reducido por trade
        params['risk_per_trade'] = self.base_params['risk_per_trade'] * 0.7  # 30% menos riesgo
        
        # Take Profit más conservador
        params['take_profit_ratio'] = 1.5  # 1.5R en vez de 2.5R
        
        # Umbrales RSI más estrictos (evitar extremos)
        params['rsi_overbought'] = 75  # Más estricto
        params['rsi_oversold'] = 25
        
        # Fuerza mínima más alta (señales más selectivas)
        params['min_signal_strength'] = 0.25
        
        # Menos trades permitidos
        params['max_daily_trades'] = 3
        
        # Umbrales de filtrado
        params['min_volume_multiplier'] = 1.2  # 20% más volumen requerido
        params['max_volatility_multiplier'] = 2.0  # Permitir hasta 2x la volatilidad normal
        
        return params

    def _adapt_low_volatility(self, params: Dict[str, Any], metrics: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Parámetros para baja volatilidad"""
        
        # Stop Loss más ajustado
        atr_relative = metrics.get('atr_relative', 0.02)
        params['stop_loss_pct'] = max(0.005, min(0.015, atr_relative * 1.2))
        
        # Take Profit más chico (movimientos limitados)
        params['take_profit_ratio'] = 1.5  # 1.5R
        
        # Riesgo normal
        params['risk_per_trade'] = self.base_params['risk_per_trade']
        
        # RSI más permisivo (menos señales en mercado tranquilo)
        params['rsi_overbought'] = 85
        params['rsi_oversold'] = 15
        
        # Fuerza mínima más baja (aceptar señales más débiles)
        params['min_signal_strength'] = 0.10
        
        # Filtrar mercados con muy poco movimiento
        avg_range = metrics.get('avg_daily_range_pct', 1.0)
        params['min_daily_range_pct'] = avg_range * 0.5  # Al menos 50% del rango promedio
        
        # Más trades permitidos (aprovechar oportunidades)
        params['max_daily_trades'] = 6
        
        # Umbrales de filtrado
        params['min_volume_multiplier'] = 0.8  # Aceptar menos volumen
        params['max_volatility_multiplier'] = 1.5
        
        return params

    def _adapt_trending_bullish(self, params: Dict[str, Any], metrics: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Parámetros para tendencia alcista fuerte"""
        
        # Stop Loss normal a ajustado
        params['stop_loss_pct'] = self.base_params['stop_loss_pct']
        
        # Take Profit más ambicioso (dejar correr ganancias)
        params['take_profit_ratio'] = 3.0  # 3R en tendencia fuerte
        
        # Riesgo puede ser ligeramente mayor
        params['risk_per_trade'] = self.base_params['risk_per_trade'] * 1.1  # 10% más
        
        # RSI más permisivo en compras
        params['rsi_overbought'] = 85  # Permitir compras en momentum
        params['rsi_oversold'] = 25
        
        # Fuerza mínima moderada
        params['min_signal_strength'] = 0.15
        
        # Más trades permitidos (aprovechar tendencia)
        params['max_daily_trades'] = 5
        
        # Preferencias de dirección
        params['allow_long'] = True
        params['allow_short'] = False  # Evitar contra-tendencia
        
        # Umbrales de filtrado
        params['min_volume_multiplier'] = 1.0
        params['max_volatility_multiplier'] = 1.8
        
        return params

    def _adapt_trending_bearish(self, params: Dict[str, Any], metrics: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Parámetros para tendencia bajista fuerte"""
        
        # Stop Loss normal
        params['stop_loss_pct'] = self.base_params['stop_loss_pct']
        
        # Take Profit más ambicioso
        params['take_profit_ratio'] = 3.0  # 3R
        
        # Riesgo ligeramente mayor
        params['risk_per_trade'] = self.base_params['risk_per_trade'] * 1.1
        
        # RSI más permisivo en ventas
        params['rsi_overbought'] = 75
        params['rsi_oversold'] = 15  # Permitir ventas en momentum bajista
        
        # Fuerza mínima moderada
        params['min_signal_strength'] = 0.15
        
        # Más trades permitidos
        params['max_daily_trades'] = 5
        
        # Preferencias de dirección
        params['allow_long'] = False  # Evitar contra-tendencia
        params['allow_short'] = True
        
        # Umbrales de filtrado
        params['min_volume_multiplier'] = 1.0
        params['max_volatility_multiplier'] = 1.8
        
        return params

    def _adapt_ranging(self, params: Dict[str, Any], metrics: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Parámetros para mercado en rango lateral"""
        
        # Stop Loss ajustado (operaciones más precisas)
        params['stop_loss_pct'] = self.base_params['stop_loss_pct'] * 0.9
        
        # Take Profit más conservador (movimientos limitados)
        params['take_profit_ratio'] = 1.8  # 1.8R
        
        # Riesgo normal
        params['risk_per_trade'] = self.base_params['risk_per_trade']
        
        # RSI más estricto (operar en extremos del rango)
        params['rsi_overbought'] = 72  # Comprar en sobreventa, vender en sobrecompra
        params['rsi_oversold'] = 28
        
        # Fuerza mínima moderada
        params['min_signal_strength'] = 0.18
        
        # Trades moderados
        params['max_daily_trades'] = 4
        
        # Permitir ambas direcciones (reversión a la media)
        params['allow_long'] = True
        params['allow_short'] = True
        
        # Umbrales de filtrado
        params['min_volume_multiplier'] = 1.0
        params['max_volatility_multiplier'] = 1.5
        
        return params

    def _determine_trading_style(self, regime: MarketRegime) -> str:
        """Determina el estilo de trading según el régimen"""
        style_map = {
            MarketRegime.TRENDING_BULLISH: "follow_trend_long",
            MarketRegime.TRENDING_BEARISH: "follow_trend_short",
            MarketRegime.RANGING: "mean_reversion",
            MarketRegime.HIGH_VOLATILITY: "conservative",
            MarketRegime.LOW_VOLATILITY: "patient",
            MarketRegime.CHAOTIC: "very_conservative",
        }
        return style_map.get(regime, "balanced")

    def get_current_parameters(self) -> Dict[str, Any]:
        """Retorna los parámetros actuales adaptados"""
        return self.current_params.copy()

    def should_trade(self, signal_action: str) -> bool:
        """
        Verifica si se debe permitir un trade según el régimen y dirección
        
        Args:
            signal_action: 'BUY' o 'SELL'
            
        Returns:
            True si se permite el trade
        """
        params = self.current_params
        
        if signal_action == "BUY":
            return params.get('allow_long', True)
        elif signal_action == "SELL":
            return params.get('allow_short', True)
        
        return True

    def get_max_daily_trades(self) -> int:
        """Retorna el máximo de trades diarios según régimen"""
        return self.current_params.get('max_daily_trades', 5)

    def get_min_signal_strength(self) -> float:
        """Retorna la fuerza mínima de señal requerida"""
        return self.current_params.get('min_signal_strength', 0.15)

