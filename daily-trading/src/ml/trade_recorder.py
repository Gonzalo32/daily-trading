"""
Sistema de registro COMPLETO de operaciones para aprendizaje del bot
Guarda todas las operaciones con todas las features necesarias para ML
"""

import pandas as pd
import os
from datetime import datetime
from typing import Dict, Any, Optional
import json
from src.utils.logging_setup import setup_logging

class TradeRecorder:
    """
    Registra operaciones completas con:
    - Features técnicas (RSI, MACD, EMAs, etc.)
    - Contexto de mercado (volatilidad, volumen, régimen)
    - Estado del bot (PnL, trades previos)
    - Resultados (PnL, MFE, MAE, duración)
    """
    
    def __init__(self, data_file: str = "src/ml/trading_history.csv", config=None):
        self.data_file = data_file
        self.trades_history = []
        self.logger = setup_logging(__name__) if config is None else setup_logging(__name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        
        # Crear archivo si no existe
        if not os.path.exists(data_file):
            self._initialize_file()
    
    def _initialize_file(self):
        """Inicializar archivo CSV con TODAS las columnas necesarias para ML"""
        columns = [
            # Identificación y timing
            'timestamp', 'symbol', 'action', 'exit_time',
            
            # Precios y resultados
            'entry_price', 'exit_price', 'size', 'stop_loss', 'take_profit',
            'pnl', 'pnl_percent', 'r_multiple', 'duration_minutes',
            
            # MFE/MAE (Max Favorable/Adverse Excursion)
            'max_favorable_excursion', 'max_adverse_excursion',
            'exit_type',  # 'stop_loss', 'take_profit', 'manual', 'time_stop'
            
            # Features técnicas (en ENTRADA)
            'rsi', 'macd', 'macd_signal', 'fast_ma', 'slow_ma', 'atr',
            'ma_diff_pct', 'rsi_normalized', 'macd_strength',
            'vwap', 'ema_200',
            
            # Contexto de mercado
            'volatility_normalized', 'volume', 'volume_relative',
            'hour_of_day', 'day_of_week',
            'avg_daily_range_pct', 'current_range_pct',
            
            # Régimen de mercado
            'regime', 'regime_confidence',
            'regime_trending_bullish', 'regime_trending_bearish', 'regime_ranging',
            'regime_high_volatility', 'regime_low_volatility', 'regime_chaotic',
            
            # Estado del bot
            'daily_pnl_normalized', 'daily_trades', 'consecutive_signals',
            
            # Señal
            'signal_strength', 'signal_buy', 'signal_sell',
            
            # ML prediction (si disponible)
            'ml_probability', 'ml_approved',
            
            # Target para entrenar
            'target',  # 1 = trade exitoso (alcanzó al menos 1R), 0 = no exitoso
            'target_multiclass'  # 0 = malo, 1 = decente, 2 = excelente
        ]
        df = pd.DataFrame(columns=columns)
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        df.to_csv(self.data_file, index=False)
        self.logger.info(f"✅ Archivo de trading history inicializado: {self.data_file}")
    
    def record_trade(self, 
                    entry_data: Dict[str, Any],
                    exit_data: Dict[str, Any],
                    market_data_entry: Dict[str, Any],
                    market_data_exit: Optional[Dict[str, Any]] = None,
                    regime_info: Optional[Dict[str, Any]] = None,
                    bot_state: Optional[Dict[str, Any]] = None,
                    ml_decision: Optional[Dict[str, Any]] = None,
                    position_stats: Optional[Dict[str, Any]] = None) -> bool:
        """
        Registra una operación completa con TODAS las features necesarias para ML
        
        Args:
            entry_data: Datos de entrada (precio, tamaño, stop_loss, take_profit, strength, etc.)
            exit_data: Datos de salida (precio, pnl, exit_type, etc.)
            market_data_entry: Datos de mercado al entrar (indicadores técnicos)
            market_data_exit: Datos de mercado al salir (opcional)
            regime_info: Información del régimen de mercado
            bot_state: Estado del bot (daily_pnl, daily_trades, consecutive_signals)
            ml_decision: Decisión del filtro ML (probability, approved, etc.)
            position_stats: Estadísticas de la posición (MFE, MAE, etc.)
        """
        try:
            # Procesar tiempos
            entry_time = entry_data.get('entry_time', datetime.now())
            exit_time = exit_data.get('exit_time', datetime.now())
            
            if isinstance(entry_time, str):
                entry_time = datetime.fromisoformat(entry_time)
            if isinstance(exit_time, str):
                exit_time = datetime.fromisoformat(exit_time)
            
            duration = (exit_time - entry_time).total_seconds() / 60  # minutos
            
            # Precios y PnL
            entry_price = entry_data.get('entry_price', 0)
            exit_price = exit_data.get('exit_price', exit_data.get('price', entry_price))
            stop_loss = entry_data.get('stop_loss', entry_price)
            take_profit = entry_data.get('take_profit', entry_price)
            
            pnl = exit_data.get('pnl', 0)
            size = entry_data.get('size', 0)
            pnl_percent = (pnl / (entry_price * size)) * 100 if entry_price > 0 and size > 0 else 0
            
            # Calcular R múltiple
            risk = abs(entry_price - stop_loss)
            r_multiple = (pnl / (risk * size)) if risk > 0 and size > 0 else 0
            
            # Indicadores técnicos
            indicators = market_data_entry.get('indicators', {})
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            fast_ma = indicators.get('fast_ma', entry_price)
            slow_ma = indicators.get('slow_ma', entry_price)
            atr = indicators.get('atr', 0)
            
            # Features derivadas
            ma_diff_pct = ((fast_ma - slow_ma) / slow_ma * 100) if slow_ma > 0 else 0
            rsi_normalized = (rsi - 50) / 50
            macd_strength = (macd / macd_signal) if macd_signal != 0 else 0
            volatility_normalized = (atr / entry_price) if entry_price > 0 else 0
            
            # Volumen
            volume = market_data_entry.get('volume', 0)
            volume_relative = entry_data.get('volume_relative', 1.0)
            
            # Timing
            hour_of_day = entry_time.hour
            day_of_week = entry_time.weekday()
            
            # Régimen de mercado
            regime_info = regime_info or {}
            regime_str = regime_info.get('regime', 'ranging')
            regime_confidence = regime_info.get('confidence', 0.5)
            regime_metrics = regime_info.get('metrics', {})
            
            # ML decision
            ml_decision = ml_decision or {}
            ml_probability = ml_decision.get('probability', 0.5)
            ml_approved = 1 if ml_decision.get('approved', True) else 0
            
            # Bot state
            bot_state = bot_state or {}
            daily_pnl_normalized = bot_state.get('daily_pnl_normalized', 0)
            daily_trades = bot_state.get('daily_trades', 0)
            consecutive_signals = bot_state.get('consecutive_signals', 0)
            
            # Position stats (MFE/MAE)
            position_stats = position_stats or {}
            mfe = position_stats.get('max_favorable_excursion', 0)
            mae = position_stats.get('max_adverse_excursion', 0)
            
            # Exit type
            exit_type = exit_data.get('exit_type', 'unknown')
            
            # Signal
            action = entry_data.get('action', 'BUY')
            signal_strength = entry_data.get('strength', 0)
            
            # Target para ML
            # Target binario: 1 si alcanzó al menos 1R, 0 si no
            target = 1 if r_multiple >= 1.0 else 0
            
            # Target multi-clase:
            # 0 = malo (pérdida o < 0.5R)
            # 1 = decente (0.5R - 2R)
            # 2 = excelente (> 2R)
            if r_multiple < 0.5:
                target_multiclass = 0
            elif r_multiple < 2.0:
                target_multiclass = 1
            else:
                target_multiclass = 2
            
            # Construir registro completo
            trade_record = {
                # Identificación
                'timestamp': entry_time.isoformat(),
                'symbol': entry_data.get('symbol', ''),
                'action': action,
                'exit_time': exit_time.isoformat(),
                
                # Precios y resultados
                'entry_price': entry_price,
                'exit_price': exit_price,
                'size': size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'r_multiple': r_multiple,
                'duration_minutes': duration,
                
                # MFE/MAE
                'max_favorable_excursion': mfe,
                'max_adverse_excursion': mae,
                'exit_type': exit_type,
                
                # Features técnicas
                'rsi': rsi,
                'macd': macd,
                'macd_signal': macd_signal,
                'fast_ma': fast_ma,
                'slow_ma': slow_ma,
                'atr': atr,
                'ma_diff_pct': ma_diff_pct,
                'rsi_normalized': rsi_normalized,
                'macd_strength': macd_strength,
                'vwap': indicators.get('vwap', entry_price),
                'ema_200': indicators.get('ema_200', entry_price),
                
                # Contexto
                'volatility_normalized': volatility_normalized,
                'volume': volume,
                'volume_relative': volume_relative,
                'hour_of_day': hour_of_day,
                'day_of_week': day_of_week,
                'avg_daily_range_pct': regime_metrics.get('avg_daily_range_pct', 0),
                'current_range_pct': regime_metrics.get('current_range_pct', 0),
                
                # Régimen (one-hot)
                'regime': regime_str,
                'regime_confidence': regime_confidence,
                'regime_trending_bullish': 1 if regime_str == 'trending_bullish' else 0,
                'regime_trending_bearish': 1 if regime_str == 'trending_bearish' else 0,
                'regime_ranging': 1 if regime_str == 'ranging' else 0,
                'regime_high_volatility': 1 if regime_str == 'high_volatility' else 0,
                'regime_low_volatility': 1 if regime_str == 'low_volatility' else 0,
                'regime_chaotic': 1 if regime_str == 'chaotic' else 0,
                
                # Estado del bot
                'daily_pnl_normalized': daily_pnl_normalized,
                'daily_trades': daily_trades,
                'consecutive_signals': consecutive_signals,
                
                # Señal
                'signal_strength': signal_strength,
                'signal_buy': 1 if action == 'BUY' else 0,
                'signal_sell': 1 if action == 'SELL' else 0,
                
                # ML
                'ml_probability': ml_probability,
                'ml_approved': ml_approved,
                
                # Targets
                'target': target,
                'target_multiclass': target_multiclass,
            }
            
            # Agregar al historial
            self.trades_history.append(trade_record)
            
            # Guardar en CSV
            self._save_to_csv(trade_record)
            
            self.logger.info(
                f"📝 Trade registrado: {action} {entry_data.get('symbol')} - "
                f"PnL={pnl:.2f} ({r_multiple:.2f}R) - Target={target}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error registrando operación: {e}")
            return False
    
    def _save_to_csv(self, trade_record: Dict[str, Any]):
        """Guardar registro en CSV"""
        try:
            df = pd.DataFrame([trade_record])
            df.to_csv(self.data_file, mode='a', header=False, index=False)
        except Exception as e:
            print(f"❌ Error guardando en CSV: {e}")
    
    def get_training_data(self) -> pd.DataFrame:
        """Obtener todos los datos históricos para entrenamiento"""
        try:
            if not os.path.exists(self.data_file):
                return pd.DataFrame()
            
            df = pd.read_csv(self.data_file)
            return df
        except Exception as e:
            print(f"❌ Error leyendo datos de entrenamiento: {e}")
            return pd.DataFrame()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del historial de operaciones"""
        try:
            df = self.get_training_data()
            if df.empty:
                return {
                    'total_trades': 0,
                    'win_rate': 0,
                    'avg_pnl': 0,
                    'total_pnl': 0
                }
            
            total_trades = len(df)
            winning_trades = len(df[df['result'] == 1])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_pnl = df['pnl'].mean() if 'pnl' in df.columns else 0
            total_pnl = df['pnl'].sum() if 'pnl' in df.columns else 0
            
            return {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'total_pnl': total_pnl,
                'best_trade': df['pnl'].max() if 'pnl' in df.columns else 0,
                'worst_trade': df['pnl'].min() if 'pnl' in df.columns else 0
            }
        except Exception as e:
            print(f"❌ Error calculando estadísticas: {e}")
            return {}

