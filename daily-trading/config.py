"""
Configuración principal del Bot de Day Trading
Contiene todas las variables de configuración del sistema
"""

import os

# Cargar variables de entorno si dotenv está disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Si dotenv no está disponible, usar variables de entorno del sistema
    pass

class Config:
    # Configuración de Trading
    TRADING_MODE = os.getenv('TRADING_MODE', 'PAPER')  # PAPER, LIVE
    MAX_POSITIONS = int(os.getenv('MAX_POSITIONS', '3'))
    MAX_DAILY_LOSS = float(os.getenv('MAX_DAILY_LOSS', '0.03'))  # 3% del capital
    MAX_DAILY_GAIN = float(os.getenv('MAX_DAILY_GAIN', '0.05'))  # 5% del capital
    RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', '0.02'))  # 2% del capital por trade
    
    # Configuración de Mercado
    MARKET = os.getenv('MARKET', 'CRYPTO')  # STOCK, CRYPTO
    SYMBOL = os.getenv('SYMBOL', 'BTC/USDT')
    TIMEFRAME = os.getenv('TIMEFRAME', '1m')
    
    # Configuración de Estrategia
    FAST_MA_PERIOD = int(os.getenv('FAST_MA_PERIOD', '5'))
    SLOW_MA_PERIOD = int(os.getenv('SLOW_MA_PERIOD', '20'))
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
    RSI_OVERBOUGHT = float(os.getenv('RSI_OVERBOUGHT', '70'))
    RSI_OVERSOLD = float(os.getenv('RSI_OVERSOLD', '30'))
    
    # Configuración de Stop Loss y Take Profit
    STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', '0.01'))  # 1%
    TAKE_PROFIT_RATIO = float(os.getenv('TAKE_PROFIT_RATIO', '2.0'))  # 2:1 ratio
    
    # Configuración de Horarios (para acciones)
    TRADING_START_HOUR = int(os.getenv('TRADING_START_HOUR', '9'))
    TRADING_END_HOUR = int(os.getenv('TRADING_END_HOUR', '16'))
    
    # Configuración de APIs
    # Binance
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
    BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'True').lower() == 'true'
    
    # Alpaca (para acciones)
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
    ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
    ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    
    # Configuración de Base de Datos
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trading_bot.db')
    
    # Configuración de Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'trading_bot.log')
    
    # Configuración de Notificaciones
    ENABLE_NOTIFICATIONS = os.getenv('ENABLE_NOTIFICATIONS', 'True').lower() == 'true'
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Configuración de ML
    ENABLE_ML = os.getenv('ENABLE_ML', 'False').lower() == 'true'
    ML_MODEL_PATH = os.getenv('ML_MODEL_PATH', 'models/')
    RETRAIN_FREQUENCY = int(os.getenv('RETRAIN_FREQUENCY', '7'))  # días
    
    # Configuración de Backtesting
    BACKTEST_START_DATE = os.getenv('BACKTEST_START_DATE', '2023-01-01')
    BACKTEST_END_DATE = os.getenv('BACKTEST_END_DATE', '2023-12-31')
    INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', '10000'))
    
    # Configuración de Monitoreo
    ENABLE_DASHBOARD = os.getenv('ENABLE_DASHBOARD', 'True').lower() == 'true'
    DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', '8000'))
    
    # Configuración de Seguridad
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))  # segundos
    CONNECTION_TIMEOUT = int(os.getenv('CONNECTION_TIMEOUT', '30'))  # segundos
