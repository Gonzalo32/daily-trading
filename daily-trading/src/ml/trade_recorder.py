"""
Sistema de registro de operaciones para aprendizaje del bot
Guarda todas las operaciones y sus resultados para entrenar el modelo ML
"""

import pandas as pd
import os
from datetime import datetime
from typing import Dict, Any, Optional
import json

class TradeRecorder:
    """Registra operaciones y resultados para aprendizaje del modelo"""
    
    def __init__(self, data_file: str = "src/ml/trading_history.csv"):
        self.data_file = data_file
        self.trades_history = []
        
        # Crear archivo si no existe
        if not os.path.exists(data_file):
            self._initialize_file()
    
    def _initialize_file(self):
        """Inicializar archivo CSV con columnas necesarias"""
        columns = [
            'timestamp', 'symbol', 'action', 'entry_price', 'exit_price',
            'size', 'stop_loss', 'take_profit', 'pnl', 'pnl_percent',
            'duration_minutes', 'fast_ma', 'slow_ma', 'rsi', 'macd',
            'macd_signal', 'atr', 'volume', 'volatility', 'signal_strength',
            'result'  # 1 = ganancia, 0 = pérdida
        ]
        df = pd.DataFrame(columns=columns)
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        df.to_csv(self.data_file, index=False)
    
    def record_trade(self, 
                    entry_data: Dict[str, Any],
                    exit_data: Dict[str, Any],
                    market_data_entry: Dict[str, Any],
                    market_data_exit: Optional[Dict[str, Any]] = None) -> bool:
        """
        Registra una operación completa con sus datos de entrada y salida
        
        Args:
            entry_data: Datos de entrada (precio, tamaño, stop_loss, take_profit, etc.)
            exit_data: Datos de salida (precio, pnl, etc.)
            market_data_entry: Datos de mercado al entrar (indicadores técnicos)
            market_data_exit: Datos de mercado al salir (opcional)
        """
        try:
            entry_time = entry_data.get('entry_time', datetime.now())
            exit_time = exit_data.get('exit_time', datetime.now())
            
            if isinstance(entry_time, str):
                entry_time = datetime.fromisoformat(entry_time)
            if isinstance(exit_time, str):
                exit_time = datetime.fromisoformat(exit_time)
            
            duration = (exit_time - entry_time).total_seconds() / 60  # minutos
            
            entry_price = entry_data.get('entry_price', 0)
            exit_price = exit_data.get('exit_price', exit_data.get('price', entry_price))
            pnl = exit_data.get('pnl', 0)
            pnl_percent = (pnl / (entry_price * entry_data.get('size', 1))) * 100 if entry_price > 0 else 0
            
            indicators = market_data_entry.get('indicators', {})
            
            trade_record = {
                'timestamp': entry_time.isoformat(),
                'symbol': entry_data.get('symbol', ''),
                'action': entry_data.get('action', ''),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'size': entry_data.get('size', 0),
                'stop_loss': entry_data.get('stop_loss', 0),
                'take_profit': entry_data.get('take_profit', 0),
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'duration_minutes': duration,
                'fast_ma': indicators.get('fast_ma', 0),
                'slow_ma': indicators.get('slow_ma', 0),
                'rsi': indicators.get('rsi', 0),
                'macd': indicators.get('macd', 0),
                'macd_signal': indicators.get('macd_signal', 0),
                'atr': indicators.get('atr', 0),
                'volume': market_data_entry.get('volume', 0),
                'volatility': indicators.get('atr', 0) / entry_price if entry_price > 0 else 0,
                'signal_strength': entry_data.get('strength', 0),
                'result': 1 if pnl > 0 else 0  # 1 = ganancia, 0 = pérdida
            }
            
            # Agregar al historial
            self.trades_history.append(trade_record)
            
            # Guardar en CSV
            self._save_to_csv(trade_record)
            
            return True
            
        except Exception as e:
            print(f"❌ Error registrando operación: {e}")
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

