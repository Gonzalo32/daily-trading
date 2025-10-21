"""
Estrategia de trading automatizada
Implementa la lógica de decisión de compra/venta basada en indicadores técnicos
"""

import logging
from typing import Dict, Optional, Any
import pandas as pd
import numpy as np
from config import Config

class TradingStrategy:
    """Estrategia de trading basada en medias móviles y RSI"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Estado de la estrategia
        self.last_signal = None
        self.signal_strength = 0.0
        self.consecutive_signals = 0
        
    async def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generar señal de trading basada en los datos de mercado"""
        try:
            if not market_data or 'indicators' not in market_data:
                return None
                
            indicators = market_data['indicators']
            price = market_data['price']
            
            # Verificar que tenemos todos los indicadores necesarios
            required_indicators = ['fast_ma', 'slow_ma', 'rsi', 'macd', 'macd_signal']
            if not all(ind in indicators for ind in required_indicators):
                self.logger.warning("⚠️ Indicadores técnicos incompletos")
                return None
                
            # Generar señal principal
            signal = self._analyze_technical_indicators(indicators, price)
            
            if signal:
                # Aplicar filtros adicionales
                if self._apply_filters(signal, market_data):
                    # Calcular tamaño de posición
                    position_size = self._calculate_position_size(signal, market_data)
                    
                    if position_size > 0:
                        signal['position_size'] = position_size
                        signal['timestamp'] = market_data['timestamp']
                        signal['symbol'] = market_data['symbol']
                        
                        # Actualizar estado
                        self.last_signal = signal
                        self.consecutive_signals += 1
                        
                        self.logger.info(f"📊 Señal generada: {signal['action']} {signal['symbol']} - Fuerza: {signal['strength']:.2f}")
                        return signal
                    else:
                        self.logger.info("ℹ️ Señal rechazada: tamaño de posición insuficiente")
                else:
                    self.logger.info("ℹ️ Señal rechazada: no pasa filtros adicionales")
            else:
                self.consecutive_signals = 0
                
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error generando señal: {e}")
            return None
            
    def _analyze_technical_indicators(self, indicators: Dict[str, float], price: float) -> Optional[Dict[str, Any]]:
        """Analizar indicadores técnicos para generar señal"""
        try:
            fast_ma = indicators['fast_ma']
            slow_ma = indicators['slow_ma']
            rsi = indicators['rsi']
            macd = indicators['macd']
            macd_signal = indicators['macd_signal']
            
            # Verificar que los valores no sean NaN
            if any(pd.isna([fast_ma, slow_ma, rsi, macd, macd_signal])):
                return None
                
            signal = None
            strength = 0.0
            
            # Señal de compra: MA rápida cruza por encima de MA lenta + RSI no sobrecomprado + MACD positivo
            if (fast_ma > slow_ma and 
                rsi < self.config.RSI_OVERBOUGHT and 
                macd > macd_signal and
                macd > 0):
                
                # Calcular fuerza de la señal
                ma_strength = (fast_ma - slow_ma) / slow_ma * 100
                rsi_strength = (self.config.RSI_OVERBOUGHT - rsi) / self.config.RSI_OVERBOUGHT
                macd_strength = macd / abs(macd_signal) if macd_signal != 0 else 0
                
                strength = (ma_strength * 0.4 + rsi_strength * 0.3 + macd_strength * 0.3)
                
                if strength > 0.3:  # Umbral mínimo de fuerza
                    signal = {
                        'action': 'BUY',
                        'price': price,
                        'strength': strength,
                        'reason': 'MA crossover + RSI + MACD bullish',
                        'stop_loss': price * (1 - self.config.STOP_LOSS_PCT),
                        'take_profit': price * (1 + self.config.STOP_LOSS_PCT * self.config.TAKE_PROFIT_RATIO)
                    }
                    
            # Señal de venta: MA rápida cruza por debajo de MA lenta + RSI no sobrevendido + MACD negativo
            elif (fast_ma < slow_ma and 
                  rsi > self.config.RSI_OVERSOLD and 
                  macd < macd_signal and
                  macd < 0):
                
                # Calcular fuerza de la señal
                ma_strength = (slow_ma - fast_ma) / slow_ma * 100
                rsi_strength = (rsi - self.config.RSI_OVERSOLD) / (100 - self.config.RSI_OVERSOLD)
                macd_strength = abs(macd) / abs(macd_signal) if macd_signal != 0 else 0
                
                strength = (ma_strength * 0.4 + rsi_strength * 0.3 + macd_strength * 0.3)
                
                if strength > 0.3:  # Umbral mínimo de fuerza
                    signal = {
                        'action': 'SELL',
                        'price': price,
                        'strength': strength,
                        'reason': 'MA crossover + RSI + MACD bearish',
                        'stop_loss': price * (1 + self.config.STOP_LOSS_PCT),
                        'take_profit': price * (1 - self.config.STOP_LOSS_PCT * self.config.TAKE_PROFIT_RATIO)
                    }
                    
            return signal
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando indicadores técnicos: {e}")
            return None
            
    def _apply_filters(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """Aplicar filtros adicionales a la señal"""
        try:
            # Filtro 1: Evitar señales consecutivas del mismo tipo
            if (self.last_signal and 
                self.last_signal['action'] == signal['action'] and 
                self.consecutive_signals >= 3):
                self.logger.info("ℹ️ Filtro: demasiadas señales consecutivas del mismo tipo")
                return False
                
            # Filtro 2: Verificar volatilidad (usando ATR si está disponible)
            if 'atr' in market_data['indicators']:
                atr = market_data['indicators']['atr']
                price = market_data['price']
                volatility = atr / price
                
                if volatility > 0.05:  # 5% de volatilidad máxima
                    self.logger.info("ℹ️ Filtro: volatilidad demasiado alta")
                    return False
                    
            # Filtro 3: Verificar volumen (si está disponible)
            if 'volume' in market_data:
                volume = market_data['volume']
                if volume < 1000:  # Volumen mínimo
                    self.logger.info("ℹ️ Filtro: volumen insuficiente")
                    return False
                    
            # Filtro 4: Verificar horario de trading (para acciones)
            if self.config.MARKET == 'STOCK':
                current_hour = market_data['timestamp'].hour
                if not (self.config.TRADING_START_HOUR <= current_hour < self.config.TRADING_END_HOUR):
                    self.logger.info("ℹ️ Filtro: fuera del horario de trading")
                    return False
                    
            # Filtro 5: Verificar fuerza mínima de la señal
            if signal['strength'] < 0.3:
                self.logger.info("ℹ️ Filtro: fuerza de señal insuficiente")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error aplicando filtros: {e}")
            return False
            
    def _calculate_position_size(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> float:
        """Calcular tamaño de posición basado en el riesgo"""
        try:
            # Obtener capital disponible (simulado por ahora)
            available_capital = 10000  # TODO: Obtener del balance real
            
            # Calcular riesgo por trade
            risk_amount = available_capital * self.config.RISK_PER_TRADE
            
            # Calcular distancia al stop loss
            price = signal['price']
            stop_loss = signal['stop_loss']
            risk_per_unit = abs(price - stop_loss)
            
            if risk_per_unit == 0:
                return 0
                
            # Calcular cantidad de unidades
            position_size = risk_amount / risk_per_unit
            
            # Aplicar límites
            max_position_size = available_capital * 0.1 / price  # Máximo 10% del capital
            position_size = min(position_size, max_position_size)
            
            # Redondear a 2 decimales
            return round(position_size, 2)
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando tamaño de posición: {e}")
            return 0
            
    def get_strategy_info(self) -> Dict[str, Any]:
        """Obtener información sobre la estrategia"""
        return {
            'name': 'MA Crossover + RSI + MACD',
            'description': 'Estrategia basada en cruce de medias móviles con confirmación de RSI y MACD',
            'parameters': {
                'fast_ma_period': self.config.FAST_MA_PERIOD,
                'slow_ma_period': self.config.SLOW_MA_PERIOD,
                'rsi_period': self.config.RSI_PERIOD,
                'rsi_overbought': self.config.RSI_OVERBOUGHT,
                'rsi_oversold': self.config.RSI_OVERSOLD,
                'stop_loss_pct': self.config.STOP_LOSS_PCT,
                'take_profit_ratio': self.config.TAKE_PROFIT_RATIO
            },
            'last_signal': self.last_signal,
            'consecutive_signals': self.consecutive_signals
        }
        
    def reset_strategy(self):
        """Reiniciar estado de la estrategia"""
        self.last_signal = None
        self.signal_strength = 0.0
        self.consecutive_signals = 0
        self.logger.info("🔄 Estrategia reiniciada")
