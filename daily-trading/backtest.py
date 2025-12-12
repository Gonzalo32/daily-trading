"""
Script de Backtesting para el Bot de Day Trading
Permite probar estrategias con datos históricos antes del trading real
"""

import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from config import Config
from src.data.market_data import MarketDataProvider
from src.strategy.trading_strategy import TradingStrategy
from src.risk.risk_manager import RiskManager
from src.utils.logger import setup_logger

class Backtester:
    """Backtester para probar estrategias de trading"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger('INFO', 'logs/backtest.log')
        
        # Inicializar componentes
        self.market_data = MarketDataProvider(config)
        self.strategy = TradingStrategy(config)
        self.risk_manager = RiskManager(config)
        
        # Resultados del backtest
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        self.metrics = {}
        
    async def run_backtest(self, start_date: str, end_date: str, initial_capital: float = 10000):
        """Ejecutar backtest completo"""
        try:
            self.logger.info(f"🚀 Iniciando backtest desde {start_date} hasta {end_date}")
            
            # Obtener datos históricos
            historical_data = await self._get_historical_data(start_date, end_date)
            if historical_data is None or historical_data.empty:
                self.logger.error("❌ No se pudieron obtener datos históricos")
                return
                
            self.logger.info(f"📊 Datos obtenidos: {len(historical_data)} velas")
            
            # Ejecutar simulación
            await self._simulate_trading(historical_data, initial_capital)
            
            # Calcular métricas
            self._calculate_metrics(initial_capital)
            
            # Generar reporte
            self._generate_report()
            
            # Generar gráficos
            self._generate_charts()
            
            self.logger.info("✅ Backtest completado exitosamente")
            
        except Exception as e:
            self.logger.error(f"❌ Error en backtest: {e}")
            raise
            
    async def _get_historical_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Obtener datos históricos"""
        try:
            # Convertir fechas
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Calcular días de diferencia
            days_diff = (end_dt - start_dt).days
            
            # Obtener datos (limitado a 1000 velas por simplicidad)
            limit = min(1000, days_diff * 24 * 60)  # 1 minuto por vela
            
            if self.config.MARKET == 'CRYPTO':
                # Obtener datos de Binance
                ohlcv = await self.market_data.exchange.fetch_ohlcv(
                    self.config.SYMBOL,
                    self.config.TIMEFRAME,
                    limit=limit
                )
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Calcular indicadores técnicos
                df = self._calculate_indicators(df)
                
                return df
            else:
                # Para acciones, generar datos simulados
                return self._generate_simulated_data(start_dt, end_dt)
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo datos históricos: {e}")
            return None
            
    def _generate_simulated_data(self, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
        """Generar datos simulados para backtesting"""
        try:
            # Generar timestamps
            timestamps = pd.date_range(start=start_dt, end=end_dt, freq='1min')
            
            # Generar precios simulados (random walk)
            np.random.seed(42)
            returns = np.random.normal(0, 0.001, len(timestamps))
            prices = 100 * np.exp(np.cumsum(returns))
            
            # Generar OHLCV
            data = []
            for i, (ts, price) in enumerate(zip(timestamps, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.005)))
                low = price * (1 - abs(np.random.normal(0, 0.005)))
                open_price = price * (1 + np.random.normal(0, 0.002))
                volume = np.random.uniform(1000, 10000)
                
                data.append({
                    'timestamp': ts,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
                
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            # Calcular indicadores técnicos
            df = self._calculate_indicators(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error generando datos simulados: {e}")
            return None
            
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular indicadores técnicos"""
        try:
            # Medias móviles
            df['fast_ma'] = df['close'].rolling(window=self.config.FAST_MA_PERIOD).mean()
            df['slow_ma'] = df['close'].rolling(window=self.config.SLOW_MA_PERIOD).mean()
            
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'], self.config.RSI_PERIOD)
            
            # MACD
            macd_data = self._calculate_macd(df['close'])
            df['macd'] = macd_data['macd']
            df['macd_signal'] = macd_data['signal']
            
            # ATR
            df['atr'] = self._calculate_atr(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando indicadores: {e}")
            return df
            
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcular RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return pd.Series(index=prices.index, dtype=float)
            
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calcular MACD"""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=signal).mean()
            return {'macd': macd, 'signal': signal_line}
        except:
            return {'macd': pd.Series(index=prices.index, dtype=float), 'signal': pd.Series(index=prices.index, dtype=float)}
            
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcular ATR"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(window=period).mean()
            return atr
        except:
            return pd.Series(index=df.index, dtype=float)
            
    async def _simulate_trading(self, data: pd.DataFrame, initial_capital: float):
        """Simular trading con datos históricos"""
        try:
            capital = initial_capital
            position = None
            equity_curve = [initial_capital]
            
            self.logger.info("🔄 Simulando trading...")
            
            for i in range(len(data)):
                if i < self.config.SLOW_MA_PERIOD:
                    continue
                    
                # Obtener datos actuales
                current_data = data.iloc[i]
                
                # Preparar datos de mercado
                market_data = {
                    'symbol': self.config.SYMBOL,
                    'timestamp': current_data.name,
                    'price': current_data['close'],
                    'indicators': {
                        'fast_ma': current_data['fast_ma'],
                        'slow_ma': current_data['slow_ma'],
                        'rsi': current_data['rsi'],
                        'macd': current_data['macd'],
                        'macd_signal': current_data['macd_signal'],
                        'atr': current_data['atr']
                    }
                }
                
                # Verificar si hay posición abierta
                if position:
                    # Verificar si cerrar posición
                    if self.risk_manager.should_close_position(position, market_data):
                        # Cerrar posición
                        pnl = self._calculate_pnl(position, current_data['close'])
                        capital += pnl
                        
                        # Registrar trade
                        trade = {
                            'entry_time': position['entry_time'],
                            'exit_time': current_data.name,
                            'symbol': position['symbol'],
                            'side': position['side'],
                            'entry_price': position['entry_price'],
                            'exit_price': current_data['close'],
                            'size': position['size'],
                            'pnl': pnl,
                            'duration': (current_data.name - position['entry_time']).total_seconds() / 60
                        }
                        self.trades.append(trade)
                        
                        position = None
                        
                else:
                    # Generar señal de trading
                    signal = await self.strategy.generate_signal(market_data)
                    
                    if signal and self.risk_manager.validate_trade(signal, []):
                        # Abrir posición
                        position_size = signal['position_size']
                        position = {
                            'symbol': signal['symbol'],
                            'side': signal['action'],
                            'entry_price': signal['price'],
                            'size': position_size,
                            'entry_time': current_data.name,
                            'stop_loss': signal['stop_loss'],
                            'take_profit': signal['take_profit']
                        }
                        
                # Actualizar curva de capital
                if position:
                    unrealized_pnl = self._calculate_pnl(position, current_data['close'])
                    equity_curve.append(capital + unrealized_pnl)
                else:
                    equity_curve.append(capital)
                    
            # Cerrar posición final si existe
            if position:
                pnl = self._calculate_pnl(position, data['close'].iloc[-1])
                capital += pnl
                
                trade = {
                    'entry_time': position['entry_time'],
                    'exit_time': data.index[-1],
                    'symbol': position['symbol'],
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': data['close'].iloc[-1],
                    'size': position['size'],
                    'pnl': pnl,
                    'duration': (data.index[-1] - position['entry_time']).total_seconds() / 60
                }
                self.trades.append(trade)
                
            self.equity_curve = equity_curve
            self.final_capital = capital
            
        except Exception as e:
            self.logger.error(f"❌ Error en simulación: {e}")
            raise
            
    def _calculate_pnl(self, position: Dict[str, Any], current_price: float) -> float:
        """Calcular PnL de una posición"""
        try:
            if position['side'] == 'BUY':
                return (current_price - position['entry_price']) * position['size']
            else:
                return (position['entry_price'] - current_price) * position['size']
        except:
            return 0.0
            
    def _calculate_metrics(self, initial_capital: float):
        """Calcular métricas de rendimiento"""
        try:
            if not self.trades:
                self.metrics = {'error': 'No hay trades para analizar'}
                return
                
            # Métricas básicas
            total_trades = len(self.trades)
            winning_trades = len([t for t in self.trades if t['pnl'] > 0])
            losing_trades = len([t for t in self.trades if t['pnl'] < 0])
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # PnL
            total_pnl = sum(t['pnl'] for t in self.trades)
            total_return = (self.final_capital - initial_capital) / initial_capital
            
            # Drawdown
            equity_series = pd.Series(self.equity_curve)
            rolling_max = equity_series.expanding().max()
            drawdown = (equity_series - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # Sharpe ratio
            if len(self.trades) > 1:
                returns = [t['pnl'] for t in self.trades]
                sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            else:
                sharpe_ratio = 0
                
            # Profit factor
            gross_profit = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in self.trades if t['pnl'] < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            self.metrics = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'profit_factor': profit_factor,
                'initial_capital': initial_capital,
                'final_capital': self.final_capital
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas: {e}")
            self.metrics = {'error': str(e)}
            
    def _generate_report(self):
        """Generar reporte de backtesting"""
        try:
            print("\n" + "="*60)
            print("📊 REPORTE DE BACKTESTING")
            print("="*60)
            
            if 'error' in self.metrics:
                print(f"❌ Error: {self.metrics['error']}")
                return
                
            print(f"💰 Capital Inicial: ${self.metrics['initial_capital']:,.2f}")
            print(f"💰 Capital Final: ${self.metrics['final_capital']:,.2f}")
            print(f"📈 Retorno Total: {self.metrics['total_return']:.2%}")
            print(f"💵 PnL Total: ${self.metrics['total_pnl']:,.2f}")
            print()
            
            print(f"📊 Total de Operaciones: {self.metrics['total_trades']}")
            print(f"✅ Operaciones Ganadoras: {self.metrics['winning_trades']}")
            print(f"❌ Operaciones Perdedoras: {self.metrics['losing_trades']}")
            print(f"🎯 Win Rate: {self.metrics['win_rate']:.2%}")
            print()
            
            print(f"📉 Drawdown Máximo: {self.metrics['max_drawdown']:.2%}")
            print(f"📊 Sharpe Ratio: {self.metrics['sharpe_ratio']:.2f}")
            print(f"💰 Profit Factor: {self.metrics['profit_factor']:.2f}")
            print()
            
            if self.trades:
                print("🔍 Últimas 5 Operaciones:")
                print("-" * 60)
                for trade in self.trades[-5:]:
                    pnl_str = f"+${trade['pnl']:.2f}" if trade['pnl'] > 0 else f"-${abs(trade['pnl']):.2f}"
                    print(f"{trade['side']} {trade['symbol']} @ ${trade['entry_price']:.4f} -> ${trade['exit_price']:.4f} | {pnl_str}")
                    
            print("="*60)
            
        except Exception as e:
            self.logger.error(f"❌ Error generando reporte: {e}")
            
    def _generate_charts(self):
        """Generar gráficos de backtesting"""
        try:
            if not self.trades:
                return
                
            # Configurar estilo
            plt.style.use('dark_background')
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('📊 Análisis de Backtesting', fontsize=16, color='white')
            
            # Gráfico 1: Curva de capital
            axes[0, 0].plot(self.equity_curve, color='#4CAF50', linewidth=2)
            axes[0, 0].set_title('Curva de Capital', color='white')
            axes[0, 0].set_ylabel('Capital ($)', color='white')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Gráfico 2: Distribución de PnL
            pnl_values = [t['pnl'] for t in self.trades]
            axes[0, 1].hist(pnl_values, bins=20, color='#2196F3', alpha=0.7)
            axes[0, 1].set_title('Distribución de PnL', color='white')
            axes[0, 1].set_xlabel('PnL ($)', color='white')
            axes[0, 1].set_ylabel('Frecuencia', color='white')
            axes[0, 1].grid(True, alpha=0.3)
            
            # Gráfico 3: PnL acumulado
            cumulative_pnl = np.cumsum(pnl_values)
            axes[1, 0].plot(cumulative_pnl, color='#FF9800', linewidth=2)
            axes[1, 0].set_title('PnL Acumulado', color='white')
            axes[1, 0].set_xlabel('Operación', color='white')
            axes[1, 0].set_ylabel('PnL Acumulado ($)', color='white')
            axes[1, 0].grid(True, alpha=0.3)
            
            # Gráfico 4: Drawdown
            equity_series = pd.Series(self.equity_curve)
            rolling_max = equity_series.expanding().max()
            drawdown = (equity_series - rolling_max) / rolling_max
            axes[1, 1].fill_between(range(len(drawdown)), drawdown, 0, color='#f44336', alpha=0.7)
            axes[1, 1].set_title('Drawdown', color='white')
            axes[1, 1].set_xlabel('Tiempo', color='white')
            axes[1, 1].set_ylabel('Drawdown (%)', color='white')
            axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig('backtest_results.png', dpi=300, bbox_inches='tight')
            plt.show()
            
            self.logger.info("📊 Gráficos generados: backtest_results.png")
            
        except Exception as e:
            self.logger.error(f"❌ Error generando gráficos: {e}")

async def main():
    """Función principal del backtester"""
    parser = argparse.ArgumentParser(description='Backtester del Bot de Day Trading')
    parser.add_argument('--start-date', type=str, default='2023-01-01', help='Fecha de inicio (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2023-12-31', help='Fecha de fin (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=10000, help='Capital inicial')
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='Símbolo a operar')
    
    args = parser.parse_args()
    
    # Configurar
    config = Config()
    config.SYMBOL = args.symbol
    
    # Ejecutar backtest
    backtester = Backtester(config)
    await backtester.run_backtest(args.start_date, args.end_date, args.capital)

if __name__ == "__main__":
    asyncio.run(main())
