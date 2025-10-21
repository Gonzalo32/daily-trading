"""
Proveedor de datos de mercado
Maneja la obtención de datos en tiempo real y históricos
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import ccxt
import requests
from config import Config

class MarketDataProvider:
    """Proveedor de datos de mercado para diferentes exchanges"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Inicializar exchange
        self.exchange = None
        self.market_data_cache = {}
        self.last_update = None
        
    async def initialize(self):
        """Inicializar el proveedor de datos"""
        try:
            if self.config.MARKET == 'CRYPTO':
                await self._initialize_crypto_exchange()
            elif self.config.MARKET == 'STOCK':
                await self._initialize_stock_api()
            else:
                raise ValueError(f"Mercado no soportado: {self.config.MARKET}")
                
            self.logger.info("✅ Proveedor de datos inicializado correctamente")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando proveedor de datos: {e}")
            raise
            
    async def _initialize_crypto_exchange(self):
        """Inicializar exchange de criptomonedas"""
        try:
            # Configurar Binance
            self.exchange = ccxt.binance({
                'apiKey': self.config.BINANCE_API_KEY,
                'secret': self.config.BINANCE_SECRET_KEY,
                'sandbox': self.config.BINANCE_TESTNET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            # Verificar conexión
            await self.exchange.load_markets()
            self.logger.info("✅ Conexión con Binance establecida")
            
        except Exception as e:
            self.logger.error(f"❌ Error conectando con Binance: {e}")
            raise
            
    async def _initialize_stock_api(self):
        """Inicializar API de acciones"""
        # Para acciones, usaríamos Alpaca o similar
        # Por ahora, implementación básica
        self.logger.info("✅ API de acciones configurada")
        
    async def get_latest_data(self) -> Optional[Dict[str, Any]]:
        """Obtener datos más recientes del mercado"""
        try:
            if self.config.MARKET == 'CRYPTO':
                return await self._get_crypto_data()
            elif self.config.MARKET == 'STOCK':
                return await self._get_stock_data()
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo datos de mercado: {e}")
            return None
            
    async def _get_crypto_data(self) -> Dict[str, Any]:
        """Obtener datos de criptomonedas"""
        try:
            # Obtener ticker actual
            ticker = await self.exchange.fetch_ticker(self.config.SYMBOL)
            
            # Obtener velas recientes para indicadores técnicos
            ohlcv = await self.exchange.fetch_ohlcv(
                self.config.SYMBOL, 
                self.config.TIMEFRAME, 
                limit=100
            )
            
            # Convertir a DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Calcular indicadores técnicos
            df = self._calculate_technical_indicators(df)
            
            # Preparar datos de salida
            latest_data = {
                'symbol': self.config.SYMBOL,
                'timestamp': datetime.now(),
                'price': ticker['last'],
                'open': ticker['open'],
                'high': ticker['high'],
                'low': ticker['low'],
                'volume': ticker['baseVolume'],
                'change': ticker['change'],
                'change_percent': ticker['percentage'],
                'indicators': {
                    'fast_ma': df['fast_ma'].iloc[-1],
                    'slow_ma': df['slow_ma'].iloc[-1],
                    'rsi': df['rsi'].iloc[-1],
                    'atr': df['atr'].iloc[-1],
                    'macd': df['macd'].iloc[-1],
                    'macd_signal': df['macd_signal'].iloc[-1]
                },
                'dataframe': df
            }
            
            # Actualizar caché
            self.market_data_cache = latest_data
            self.last_update = datetime.now()
            
            return latest_data
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo datos de cripto: {e}")
            return None
            
    async def _get_stock_data(self) -> Dict[str, Any]:
        """Obtener datos de acciones"""
        # Implementación para acciones usando Alpaca
        # Por ahora, retornar datos simulados
        return {
            'symbol': self.config.SYMBOL,
            'timestamp': datetime.now(),
            'price': 100.0,
            'indicators': {
                'fast_ma': 101.0,
                'slow_ma': 99.0,
                'rsi': 50.0,
                'atr': 2.0,
                'macd': 0.5,
                'macd_signal': 0.3
            }
        }
        
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular indicadores técnicos"""
        try:
            # Medias móviles
            df['fast_ma'] = df['close'].rolling(window=self.config.FAST_MA_PERIOD).mean()
            df['slow_ma'] = df['close'].rolling(window=self.config.SLOW_MA_PERIOD).mean()
            
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'], self.config.RSI_PERIOD)
            
            # ATR (Average True Range)
            df['atr'] = self._calculate_atr(df, 14)
            
            # MACD
            macd_data = self._calculate_macd(df['close'])
            df['macd'] = macd_data['macd']
            df['macd_signal'] = macd_data['signal']
            df['macd_histogram'] = macd_data['histogram']
            
            # Bollinger Bands
            bb_data = self._calculate_bollinger_bands(df['close'])
            df['bb_upper'] = bb_data['upper']
            df['bb_middle'] = bb_data['middle']
            df['bb_lower'] = bb_data['lower']
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando indicadores técnicos: {e}")
            return df
            
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcular RSI (Relative Strength Index)"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando RSI: {e}")
            return pd.Series(index=prices.index, dtype=float)
            
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcular ATR (Average True Range)"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(window=period).mean()
            
            return atr
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando ATR: {e}")
            return pd.Series(index=df.index, dtype=float)
            
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calcular MACD (Moving Average Convergence Divergence)"""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=signal).mean()
            histogram = macd - signal_line
            
            return {
                'macd': macd,
                'signal': signal_line,
                'histogram': histogram
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando MACD: {e}")
            return {
                'macd': pd.Series(index=prices.index, dtype=float),
                'signal': pd.Series(index=prices.index, dtype=float),
                'histogram': pd.Series(index=prices.index, dtype=float)
            }
            
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Calcular Bollinger Bands"""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            
            return {
                'upper': sma + (std * std_dev),
                'middle': sma,
                'lower': sma - (std * std_dev)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando Bollinger Bands: {e}")
            return {
                'upper': pd.Series(index=prices.index, dtype=float),
                'middle': pd.Series(index=prices.index, dtype=float),
                'lower': pd.Series(index=prices.index, dtype=float)
            }
            
    async def get_historical_data(self, symbol: str, timeframe: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Obtener datos históricos"""
        try:
            if self.config.MARKET == 'CRYPTO':
                ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                return df
            else:
                # Implementar para acciones
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo datos históricos: {e}")
            return None
            
    def get_cached_data(self) -> Optional[Dict[str, Any]]:
        """Obtener datos del caché"""
        if self.last_update and (datetime.now() - self.last_update).seconds < 60:
            return self.market_data_cache
        return None
        
    async def close(self):
        """Cerrar conexiones"""
        try:
            if self.exchange:
                await self.exchange.close()
            self.logger.info("✅ Conexiones cerradas correctamente")
        except Exception as e:
            self.logger.error(f"❌ Error cerrando conexiones: {e}")
