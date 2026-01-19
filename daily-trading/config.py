"""
Configuración principal del Bot de Day Trading
Incluye variables de entorno y valores por defecto
Compatible con Binance Testnet (cripto) y Alpaca Paper Trading (acciones)
"""

import os

                                             
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass                                                              


class Config:
    """Configuración centralizada del bot de trading."""
                                    
                             
                                    
    TRADING_MODE = os.getenv("TRADING_MODE", "PAPER").upper()                
    MARKET = os.getenv("MARKET", "CRYPTO").upper()                             
    SYMBOL = os.getenv("SYMBOL", "BTC/USDT")
    TIMEFRAME = os.getenv("TIMEFRAME", "5m")
    POLL_INTERVAL = 1.0
                                    
                        
                                    
    INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "10000"))
    MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "2"))

                                                
                                                        
    RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.01"))
    MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "200.0"))                
    MAX_DAILY_GAIN = float(os.getenv("MAX_DAILY_GAIN", "0.05"))       

                                                                
    MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "200"))
    PAPER_MAX_DAILY_TRADES = int(os.getenv("PAPER_MAX_DAILY_TRADES", "100"))
                                                    
    MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "3"))
    MAX_POSITION_RISK_PCT = float(os.getenv("MAX_POSITION_RISK_PCT", "0.5"))

    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.005"))                                 
                                        
    TAKE_PROFIT_RATIO = float(os.getenv("TAKE_PROFIT_RATIO", "3.0"))

                                    
                          
                                    
    FAST_MA_PERIOD = int(os.getenv("FAST_MA_PERIOD", "5"))
    SLOW_MA_PERIOD = int(os.getenv("SLOW_MA_PERIOD", "13"))
    RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
                                         
    RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "60"))
                                        
    RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "40"))
                                                                
    EMA_DIFF_PCT_MIN = float(os.getenv("EMA_DIFF_PCT_MIN", "0.02"))

                                    
                           
                                    
    TRADING_START_HOUR = int(os.getenv("TRADING_START_HOUR", "9"))
    TRADING_END_HOUR = int(os.getenv("TRADING_END_HOUR", "16"))

                                    
                       
                                    
                           
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
    BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

                            
    ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
    ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
    ALPACA_BASE_URL = os.getenv(
        "ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

                                    
                      
                                    
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trading_bot.db")

                                    
                           
                                    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FILE = os.getenv("LOG_FILE", "logs/trading_bot.log")

    ENABLE_DASHBOARD = os.getenv("ENABLE_DASHBOARD", "true").lower() == "true"
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8000"))

                                    
                      
                                    
    ENABLE_NOTIFICATIONS = os.getenv(
        "ENABLE_NOTIFICATIONS", "false").lower() == "true"
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

                                    
                        
                                    
    ENABLE_ML = os.getenv("ENABLE_ML", "false").lower() == "true"
    ML_MODEL_PATH = os.getenv("ML_MODEL_PATH", "models/")
    RETRAIN_FREQUENCY = int(os.getenv("RETRAIN_FREQUENCY", "7"))        
    TRAINING_MODE = True
                                                                   
    ML_MIN_PROBABILITY = float(os.getenv("ML_MIN_PROBABILITY", "0.55"))
                                                                               
    ML_LABEL_PROFIT_THRESHOLD_R = float(
        os.getenv("ML_LABEL_PROFIT_THRESHOLD_R", "0.0")
    )

                                    
                  
                                    
    ENABLE_DEBUG_STRATEGY = os.getenv(
        "ENABLE_DEBUG_STRATEGY", "false").lower() == "true"

                                    
                                         
                                    
    MVP_MODE_ENABLED = os.getenv("MVP_MODE_ENABLED", "true").lower() == "true"
    MVP_MIN_TRADES_FOR_ADVANCED_FEATURES = int(
        os.getenv("MVP_MIN_TRADES_FOR_ADVANCED_FEATURES", "500"))

                                    
                                     
                                    
                                                                               
    MIN_COOLDOWN_BETWEEN_TRADES = float(os.getenv("MIN_COOLDOWN_BETWEEN_TRADES", "5.0"))                          

    DECISION_HOLD_SAMPLE_RATE = int(os.getenv("DECISION_HOLD_SAMPLE_RATE", "10"))
                                                           
                                         

                                    
                   
                                    
    BACKTEST_START_DATE = os.getenv("BACKTEST_START_DATE", "2023-01-01")
    BACKTEST_END_DATE = os.getenv("BACKTEST_END_DATE", "2023-12-31")

                                    
                               
                                    
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))
    CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))

    ML_RETRAIN_EVERY = 500


    FORCE_CLOSE_TIMEOUT = 15
                                    
                        
                                    

    @classmethod
    def is_crypto(cls):
        """Verifica si el mercado es cripto."""
        return cls.MARKET == "CRYPTO"

    @classmethod
    def is_paper_mode(cls):
        """Verifica si está en modo paper trading."""
        return cls.TRADING_MODE == "PAPER"

    @classmethod
    def summary(cls):
        """Imprime un resumen de la configuración cargada."""
        summary_data = {
            "Trading Mode": cls.TRADING_MODE,
            "Market": cls.MARKET,
            "Symbol": cls.SYMBOL,
            "Timeframe": cls.TIMEFRAME,
            "Testnet": cls.BINANCE_TESTNET,
            "Database": cls.DATABASE_URL,
            "Logging": cls.LOG_FILE,
        }
        for k, v in summary_data.items():
            print(f"{k:20}: {v}")
