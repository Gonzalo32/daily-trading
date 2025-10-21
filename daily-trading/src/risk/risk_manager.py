"""
Gestor de riesgo del bot de trading
Implementa controles de riesgo y límites de exposición
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from config import Config

class RiskManager:
    """Gestor de riesgo para el bot de trading"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Estado del gestor de riesgo
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_drawdown = 0.0
        self.peak_balance = 0.0
        self.current_balance = 0.0
        self.risk_metrics = {}
        
        # Historial de operaciones
        self.trade_history = []
        self.daily_history = []
        
    def validate_trade(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """Validar si una operación cumple con los límites de riesgo"""
        try:
            # Verificar límites diarios
            if not self.check_daily_limits(self.daily_pnl, self.daily_trades):
                self.logger.warning("⚠️ Límites diarios alcanzados")
                return False
                
            # Verificar número máximo de posiciones
            if len(current_positions) >= self.config.MAX_POSITIONS:
                self.logger.warning("⚠️ Número máximo de posiciones alcanzado")
                return False
                
            # Verificar exposición total
            if not self._check_total_exposure(signal, current_positions):
                self.logger.warning("⚠️ Exposición total excede límites")
                return False
                
            # Verificar correlación entre posiciones
            if not self._check_position_correlation(signal, current_positions):
                self.logger.warning("⚠️ Posición altamente correlacionada con existentes")
                return False
                
            # Verificar volatilidad del mercado
            if not self._check_market_volatility(signal):
                self.logger.warning("⚠️ Volatilidad del mercado demasiado alta")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error validando operación: {e}")
            return False
            
    def check_daily_limits(self, daily_pnl: float, daily_trades: int) -> bool:
        """Verificar límites diarios de pérdida y número de operaciones"""
        try:
            # Verificar límite de pérdida diaria
            if daily_pnl < -self.config.MAX_DAILY_LOSS * self.current_balance:
                self.logger.warning(f"⚠️ Límite de pérdida diaria alcanzado: {daily_pnl:.2f}")
                return False
                
            # Verificar límite de ganancia diaria (opcional)
            if daily_pnl > self.config.MAX_DAILY_GAIN * self.current_balance:
                self.logger.info(f"ℹ️ Límite de ganancia diaria alcanzado: {daily_pnl:.2f}")
                return False
                
            # Verificar número máximo de operaciones diarias
            max_daily_trades = 50  # Configurable
            if daily_trades >= max_daily_trades:
                self.logger.warning(f"⚠️ Límite de operaciones diarias alcanzado: {daily_trades}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error verificando límites diarios: {e}")
            return False
            
    def should_close_position(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """Determinar si una posición debe cerrarse por riesgo"""
        try:
            current_price = market_data['price']
            entry_price = position['entry_price']
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            
            # Verificar stop loss
            if position['side'] == 'BUY' and current_price <= stop_loss:
                self.logger.info(f"🛑 Stop loss activado: {current_price} <= {stop_loss}")
                return True
                
            if position['side'] == 'SELL' and current_price >= stop_loss:
                self.logger.info(f"🛑 Stop loss activado: {current_price} >= {stop_loss}")
                return True
                
            # Verificar take profit
            if position['side'] == 'BUY' and current_price >= take_profit:
                self.logger.info(f"🎯 Take profit activado: {current_price} >= {take_profit}")
                return True
                
            if position['side'] == 'SELL' and current_price <= take_profit:
                self.logger.info(f"🎯 Take profit activado: {current_price} <= {take_profit}")
                return True
                
            # Verificar trailing stop (si está habilitado)
            if self._check_trailing_stop(position, current_price):
                self.logger.info("🔄 Trailing stop activado")
                return True
                
            # Verificar tiempo máximo de posición
            if self._check_max_position_time(position):
                self.logger.info("⏰ Tiempo máximo de posición alcanzado")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error verificando cierre de posición: {e}")
            return False
            
    def _check_total_exposure(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """Verificar exposición total del portafolio"""
        try:
            # Calcular exposición actual
            current_exposure = sum(pos['position_size'] * pos['entry_price'] for pos in current_positions)
            
            # Calcular nueva exposición
            new_exposure = signal['position_size'] * signal['price']
            
            # Verificar límite de exposición total (ej. 50% del capital)
            max_exposure = self.current_balance * 0.5
            total_exposure = current_exposure + new_exposure
            
            if total_exposure > max_exposure:
                self.logger.warning(f"⚠️ Exposición total excede límite: {total_exposure:.2f} > {max_exposure:.2f}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error verificando exposición total: {e}")
            return False
            
    def _check_position_correlation(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """Verificar correlación entre posiciones"""
        try:
            # Por simplicidad, asumimos que posiciones del mismo símbolo están correlacionadas
            signal_symbol = signal['symbol']
            
            # Contar posiciones del mismo símbolo
            same_symbol_positions = [pos for pos in current_positions if pos['symbol'] == signal_symbol]
            
            # Límite de posiciones por símbolo
            max_positions_per_symbol = 1
            if len(same_symbol_positions) >= max_positions_per_symbol:
                self.logger.warning(f"⚠️ Ya existe posición para {signal_symbol}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error verificando correlación: {e}")
            return False
            
    def _check_market_volatility(self, signal: Dict[str, Any]) -> bool:
        """Verificar volatilidad del mercado"""
        try:
            # Por simplicidad, asumimos que la volatilidad está en el signal
            # En una implementación real, se calcularía basándose en ATR o similar
            volatility_threshold = 0.05  # 5%
            
            # Simular verificación de volatilidad
            # En implementación real, usaríamos datos de mercado reales
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error verificando volatilidad: {e}")
            return False
            
    def _check_trailing_stop(self, position: Dict[str, Any], current_price: float) -> bool:
        """Verificar trailing stop"""
        try:
            if 'trailing_stop' not in position:
                return False
                
            trailing_stop = position['trailing_stop']
            entry_price = position['entry_price']
            
            # Calcular trailing stop dinámico
            if position['side'] == 'BUY':
                # Para posiciones largas, el trailing stop sube con el precio
                new_trailing_stop = current_price * (1 - self.config.STOP_LOSS_PCT)
                if new_trailing_stop > trailing_stop:
                    position['trailing_stop'] = new_trailing_stop
                    return False
                else:
                    return current_price <= trailing_stop
            else:
                # Para posiciones cortas, el trailing stop baja con el precio
                new_trailing_stop = current_price * (1 + self.config.STOP_LOSS_PCT)
                if new_trailing_stop < trailing_stop:
                    position['trailing_stop'] = new_trailing_stop
                    return False
                else:
                    return current_price >= trailing_stop
                    
        except Exception as e:
            self.logger.error(f"❌ Error verificando trailing stop: {e}")
            return False
            
    def _check_max_position_time(self, position: Dict[str, Any]) -> bool:
        """Verificar tiempo máximo de posición"""
        try:
            if 'entry_time' not in position:
                return False
                
            entry_time = position['entry_time']
            max_position_time = timedelta(hours=4)  # 4 horas máximo
            
            return datetime.now() - entry_time > max_position_time
            
        except Exception as e:
            self.logger.error(f"❌ Error verificando tiempo máximo: {e}")
            return False
            
    def update_balance(self, new_balance: float):
        """Actualizar balance actual"""
        self.current_balance = new_balance
        
        # Actualizar peak balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
            
        # Calcular drawdown actual
        current_drawdown = (self.peak_balance - new_balance) / self.peak_balance
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
            
    def record_trade(self, trade_data: Dict[str, Any]):
        """Registrar operación en el historial"""
        try:
            trade_record = {
                'timestamp': datetime.now(),
                'symbol': trade_data['symbol'],
                'action': trade_data['action'],
                'price': trade_data['price'],
                'size': trade_data['position_size'],
                'pnl': trade_data.get('pnl', 0.0),
                'reason': trade_data.get('reason', '')
            }
            
            self.trade_history.append(trade_record)
            
            # Mantener solo los últimos 1000 trades
            if len(self.trade_history) > 1000:
                self.trade_history = self.trade_history[-1000:]
                
        except Exception as e:
            self.logger.error(f"❌ Error registrando operación: {e}")
            
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Obtener métricas de riesgo actuales"""
        try:
            # Calcular métricas básicas
            total_trades = len(self.trade_history)
            winning_trades = len([t for t in self.trade_history if t['pnl'] > 0])
            losing_trades = len([t for t in self.trade_history if t['pnl'] < 0])
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Calcular PnL total
            total_pnl = sum(t['pnl'] for t in self.trade_history)
            
            # Calcular Sharpe ratio (simplificado)
            if total_trades > 1:
                returns = [t['pnl'] for t in self.trade_history]
                sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            else:
                sharpe_ratio = 0
                
            return {
                'daily_pnl': self.daily_pnl,
                'daily_trades': self.daily_trades,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'max_drawdown': self.max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'current_balance': self.current_balance,
                'peak_balance': self.peak_balance
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas de riesgo: {e}")
            return {}
            
    def reset_daily_metrics(self):
        """Reiniciar métricas diarias"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.logger.info("🔄 Métricas diarias reiniciadas")
        
    def emergency_stop(self):
        """Parada de emergencia del trading"""
        self.logger.critical("🚨 PARADA DE EMERGENCIA ACTIVADA")
        # Aquí se implementaría la lógica para cerrar todas las posiciones
        # y detener el trading inmediatamente
