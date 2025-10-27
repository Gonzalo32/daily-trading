"""
Proveedor de datos de mercado
Maneja la obtención de datos en tiempo real y cálculo de indicadores técnicos
Compatible con Binance (Testnet o Live) y estructura para acciones (Alpaca)
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional, Any

import pandas as pd
import numpy as np
import ccxt.async_support as ccxt  # ✅ versión asíncrona

from config import Config
from src.utils.logging_setup import setup_logging


class MarketDataProvider:
    """Proveedor de datos de mercado para diferentes exchanges (Cripto / Acciones)"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(__name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        self.exchange: Optional[ccxt.binance] = None
        self.market_data_cache: Dict[str, Any] = {}
        self.last_update: Optional[datetime] = None

    # ======================================================
    # 🔧 INICIALIZACIÓN
    # ======================================================
    async def initialize(self):
        """Inicializar el proveedor de datos según el mercado"""
        try:
            if self.config.MARKET == "CRYPTO":
                await self._initialize_crypto_exchange()
            elif self.config.MARKET == "STOCK":
                await self._initialize_stock_api()
            else:
                raise ValueError(f"Mercado no soportado: {self.config.MARKET}")

            self.logger.info("✅ Proveedor de datos inicializado correctamente")

        except Exception as e:
            self.logger.exception(f"❌ Error inicializando proveedor de datos: {e}")
            raise

    async def _initialize_crypto_exchange(self):
        """Inicializar conexión con Binance"""
        try:
            self.exchange = ccxt.binance({
                "apiKey": self.config.BINANCE_API_KEY,
                "secret": self.config.BINANCE_SECRET_KEY,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            })
            if self.config.BINANCE_TESTNET:
                self.exchange.set_sandbox_mode(True)

            await self.exchange.load_markets()
            self.logger.info("✅ Conexión con Binance establecida (modo testnet: %s)", self.config.BINANCE_TESTNET)

        except Exception as e:
            self.logger.exception(f"❌ Error conectando con Binance: {e}")
            raise

    async def _initialize_stock_api(self):
        """Inicializar API de acciones (Alpaca u otra futura implementación)"""
        self.logger.info("ℹ️ Inicialización de API de acciones pendiente de implementación")

    # ======================================================
    # 📈 DATOS DE MERCADO
    # ======================================================
    async def get_latest_data(self) -> Optional[Dict[str, Any]]:
        """Obtener los datos más recientes del mercado"""
        try:
            if self.config.MARKET == "CRYPTO":
                return await self._get_crypto_data()
            elif self.config.MARKET == "STOCK":
                return await self._get_stock_data()
            else:
                return None
        except Exception as e:
            self.logger.exception(f"❌ Error obteniendo datos de mercado: {e}")
            return None

    async def _get_crypto_data(self) -> Dict[str, Any]:
        """Obtener datos de criptomonedas en tiempo real"""
        try:
            ticker = await self.exchange.fetch_ticker(self.config.SYMBOL)
            ohlcv = await self.exchange.fetch_ohlcv(self.config.SYMBOL, self.config.TIMEFRAME, limit=200)

            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df = self._calculate_indicators(df)

            latest_data = {
                "symbol": self.config.SYMBOL,
                "timestamp": datetime.now(),
                "price": ticker.get("last"),
                "open": ticker.get("open"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "volume": ticker.get("baseVolume"),
                "change": ticker.get("change"),
                "change_percent": ticker.get("percentage"),
                "indicators": {
                    "fast_ma": df["fast_ma"].iloc[-1],
                    "slow_ma": df["slow_ma"].iloc[-1],
                    "rsi": df["rsi"].iloc[-1],
                    "atr": df["atr"].iloc[-1],
                    "macd": df["macd"].iloc[-1],
                    "macd_signal": df["macd_signal"].iloc[-1],
                    "bb_upper": df["bb_upper"].iloc[-1],
                    "bb_lower": df["bb_lower"].iloc[-1],
                },
                "dataframe": df,
            }

            self.market_data_cache = latest_data
            self.last_update = datetime.now()

            self.logger.debug(f"📊 Datos actualizados para {self.config.SYMBOL}")
            return latest_data

        except Exception as e:
            self.logger.exception(f"❌ Error obteniendo datos de cripto: {e}")
            return None

    async def _get_stock_data(self) -> Dict[str, Any]:
        """Simulación temporal de datos para acciones"""
        simulated = {
            "symbol": self.config.SYMBOL,
            "timestamp": datetime.now(),
            "price": 100.0,
            "indicators": {
                "fast_ma": 101.0,
                "slow_ma": 99.0,
                "rsi": 50.0,
                "atr": 2.0,
                "macd": 0.5,
                "macd_signal": 0.3,
                "bb_upper": 102.0,
                "bb_lower": 98.0,
            },
        }
        self.logger.info(f"📈 Datos simulados para acciones: {self.config.SYMBOL}")
        return simulated

    # ======================================================
    # 📊 INDICADORES TÉCNICOS
    # ======================================================
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular todos los indicadores técnicos relevantes"""
        try:
            df["fast_ma"] = df["close"].rolling(self.config.FAST_MA_PERIOD).mean()
            df["slow_ma"] = df["close"].rolling(self.config.SLOW_MA_PERIOD).mean()
            df["rsi"] = self._rsi(df["close"], self.config.RSI_PERIOD)
            df["atr"] = self._atr(df, 14)

            macd, signal, hist = self._macd(df["close"])
            df["macd"], df["macd_signal"], df["macd_hist"] = macd, signal, hist

            # Bandas de Bollinger
            mid = df["close"].rolling(20).mean()
            std = df["close"].rolling(20).std()
            df["bb_upper"], df["bb_middle"], df["bb_lower"] = mid + 2 * std, mid, mid - 2 * std

            return df.dropna()
        except Exception as e:
            self.logger.exception(f"❌ Error calculando indicadores técnicos: {e}")
            return df

    @staticmethod
    def _rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        return tr.rolling(period).mean()

    @staticmethod
    def _macd(prices: pd.Series, fast=12, slow=26, signal=9):
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        hist = macd - signal_line
        return macd, signal_line, hist

    # ======================================================
    # 🕰️ HISTÓRICO Y CIERRE
    # ======================================================
    async def get_historical_data(self, symbol: str, timeframe: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Obtener datos históricos de un símbolo"""
        try:
            if self.config.MARKET != "CRYPTO":
                return None

            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df

        except Exception as e:
            self.logger.exception(f"❌ Error obteniendo datos históricos: {e}")
            return None

    def get_cached_data(self) -> Optional[Dict[str, Any]]:
        """Obtener datos recientes del caché si no han expirado"""
        if self.last_update and (datetime.now() - self.last_update).seconds < 60:
            return self.market_data_cache
        return None

    async def close(self):
        """Cerrar conexiones de forma segura"""
        try:
            if self.exchange is not None:
                await self.exchange.close()
            self.logger.info("✅ Conexión de datos cerrada correctamente")
        except Exception as e:
            self.logger.exception(f"❌ Error cerrando MarketDataProvider: {e}")
