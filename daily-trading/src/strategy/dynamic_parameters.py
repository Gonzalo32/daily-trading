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
        
                                            
        self.base_params = {
            'risk_per_trade': config.RISK_PER_TRADE,
            'stop_loss_pct': config.STOP_LOSS_PCT,
            'take_profit_ratio': config.TAKE_PROFIT_RATIO,
            'rsi_overbought': config.RSI_OVERBOUGHT,
            'rsi_oversold': config.RSI_OVERSOLD,
            'max_daily_loss': config.MAX_DAILY_LOSS,
        }
        
                                         
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
            
                                     
            regime = MarketRegime(regime_str)
            
            self.logger.info(f"🔧 Adaptando parámetros para régimen: {regime.value}")
            
                                    
            adapted = self.base_params.copy()
            
                                   
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
        
                                                              
        atr_relative = metrics.get('atr_relative', 0.02)
        params['stop_loss_pct'] = max(0.015, min(0.03, atr_relative * 1.5))
        
                                   
        params['risk_per_trade'] = self.base_params['risk_per_trade'] * 0.7                    
        
                                     
        params['take_profit_ratio'] = 1.5                       
        
                                                      
        params['rsi_overbought'] = 75                
        params['rsi_oversold'] = 25
        
                                                         
        params['min_signal_strength'] = 0.25
        
                                 
        params['max_daily_trades'] = 3
        
                              
        params['min_volume_multiplier'] = 1.2                             
        params['max_volatility_multiplier'] = 2.0                                           
        
        return params

    def _adapt_low_volatility(self, params: Dict[str, Any], metrics: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Parámetros para baja volatilidad"""
        
                                
        atr_relative = metrics.get('atr_relative', 0.02)
        params['stop_loss_pct'] = max(0.005, min(0.015, atr_relative * 1.2))
        
                                                       
        params['take_profit_ratio'] = 1.5        
        
                       
        params['risk_per_trade'] = self.base_params['risk_per_trade']
        
                                                                
        params['rsi_overbought'] = 85
        params['rsi_oversold'] = 15
        
                                                              
        params['min_signal_strength'] = 0.10
        
                                                  
        avg_range = metrics.get('avg_daily_range_pct', 1.0)
        params['min_daily_range_pct'] = avg_range * 0.5                                   
        
                                                          
        params['max_daily_trades'] = 6
        
                              
        params['min_volume_multiplier'] = 0.8                         
        params['max_volatility_multiplier'] = 1.5
        
        return params

    def _adapt_trending_bullish(self, params: Dict[str, Any], metrics: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Parámetros para tendencia alcista fuerte"""
        
                                     
        params['stop_loss_pct'] = self.base_params['stop_loss_pct']
        
                                                            
        params['take_profit_ratio'] = 3.0                          
        
                                            
        params['risk_per_trade'] = self.base_params['risk_per_trade'] * 1.1           
        
                                      
        params['rsi_overbought'] = 85                                
        params['rsi_oversold'] = 25
        
                                
        params['min_signal_strength'] = 0.15
        
                                                      
        params['max_daily_trades'] = 5
        
                                   
        params['allow_long'] = True
        params['allow_short'] = False                           
        
                              
        params['min_volume_multiplier'] = 1.0
        params['max_volatility_multiplier'] = 1.8
        
        return params

    def _adapt_trending_bearish(self, params: Dict[str, Any], metrics: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Parámetros para tendencia bajista fuerte"""
        
                          
        params['stop_loss_pct'] = self.base_params['stop_loss_pct']
        
                                   
        params['take_profit_ratio'] = 3.0      
        
                                  
        params['risk_per_trade'] = self.base_params['risk_per_trade'] * 1.1
        
                                     
        params['rsi_overbought'] = 75
        params['rsi_oversold'] = 15                                       
        
                                
        params['min_signal_strength'] = 0.15
        
                               
        params['max_daily_trades'] = 5
        
                                   
        params['allow_long'] = False                           
        params['allow_short'] = True
        
                              
        params['min_volume_multiplier'] = 1.0
        params['max_volatility_multiplier'] = 1.8
        
        return params

    def _adapt_ranging(self, params: Dict[str, Any], metrics: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Parámetros para mercado en rango lateral"""
        
                                                       
        params['stop_loss_pct'] = self.base_params['stop_loss_pct'] * 0.9
        
                                                             
        params['take_profit_ratio'] = 1.8        
        
                       
        params['risk_per_trade'] = self.base_params['risk_per_trade']
        
                                                         
        params['rsi_overbought'] = 72                                                
        params['rsi_oversold'] = 28
        
                                
        params['min_signal_strength'] = 0.18
        
                          
        params['max_daily_trades'] = 4
        
                                                           
        params['allow_long'] = True
        params['allow_short'] = True
        
                              
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

