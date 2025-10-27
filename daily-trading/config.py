"""
Configuración principal del Bot de Day Trading
Incluye variables de entorno y valores por defecto
Compatible con Binance Testnet (cripto) y Alpaca Paper Trading (acciones)
"""

import os
from dotenv import load_dotenv

# Cargar variables del archivo .env si existe
load_dotenv()


class Config:
    # ==============================
    # 🧩 CONFIGURACIÓN GENERAL
    # ==============================
    TRADING_MODE = os.getenv("TRADING_MODE", "PAPER").upper()  # PAPER | LIVE
    MARKET = os.getenv("MARKET", "CRYPTO").upper()             # CRYPTO | STOCK
    SYMBOL = os.getenv("SYMBOL", "BTC/USDT")
    TIMEFRAME = os.getenv("TIMEFRAME", "1h")

    # ==============================
    # 💰 RIESGO Y CAPITAL
    # ==============================
    INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "10000"))
    MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "3"))

    # Gestión de riesgo porcentual
    RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.02"))  # 2% del capital por trade
    MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "0.03"))   # 3%
    MAX_DAILY_GAIN = float(os.getenv("MAX_DAILY_GAIN", "0.05"))   # 5%

    # Alternativas compatibles con versiones previas
    MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "3"))
    MAX_POSITION_RISK_PCT = float(os.getenv("MAX_POSITION_RISK_PCT", "1.5"))

    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.01"))      # 1%
    TAKE_PROFIT_RATIO = float(os.getenv("TAKE_PROFIT_RATIO", "2.0"))  # 2:1 ratio

    # ==============================
    # 📈 ESTRATEGIA TÉCNICA
    # ==============================
    FAST_MA_PERIOD = int(os.getenv("FAST_MA_PERIOD", "9"))
    SLOW_MA_PERIOD = int(os.getenv("SLOW_MA_PERIOD", "21"))
    RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
    RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70"))
    RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))

    # ==============================
    # 🕓 HORARIOS (acciones)
    # ==============================
    TRADING_START_HOUR = int(os.getenv("TRADING_START_HOUR", "9"))
    TRADING_END_HOUR = int(os.getenv("TRADING_END_HOUR", "16"))

    # ==============================
    # 🌐 APIs DE MERCADO
    # ==============================
    # Binance (para cripto)
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
    BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

    # Alpaca (para acciones)
    ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
    ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
    ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    # ==============================
    # 🗄️ BASE DE DATOS
    # ==============================
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trading_bot.db")

    # ==============================
    # 🧾 LOGGING Y MONITOREO
    # ==============================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FILE = os.getenv("LOG_FILE", "logs/trading_bot.log")

    ENABLE_DASHBOARD = os.getenv("ENABLE_DASHBOARD", "true").lower() == "true"
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8000"))

    # ==============================
    # 📢 NOTIFICACIONES
    # ==============================
    ENABLE_NOTIFICATIONS = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() == "true"
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # ==============================
    # 🧠 MACHINE LEARNING
    # ==============================
    ENABLE_ML = os.getenv("ENABLE_ML", "false").lower() == "true"
    ML_MODEL_PATH = os.getenv("ML_MODEL_PATH", "models/")
    RETRAIN_FREQUENCY = int(os.getenv("RETRAIN_FREQUENCY", "7"))  # días

    # ==============================
    # 📆 BACKTESTING
    # ==============================
    BACKTEST_START_DATE = os.getenv("BACKTEST_START_DATE", "2023-01-01")
    BACKTEST_END_DATE = os.getenv("BACKTEST_END_DATE", "2023-12-31")

    # ==============================
    # 🛡️ SEGURIDAD / CONEXIONES
    # ==============================
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))
    CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))

    # ==============================
    # 🔧 FUNCIONES ÚTILES
    # ==============================
    @classmethod
    def is_crypto(cls):
        return cls.MARKET == "CRYPTO"

    @classmethod
    def is_paper_mode(cls):
        return cls.TRADING_MODE == "PAPER"

    @classmethod
    def summary(cls):
        """Imprime un resumen de la configuración cargada"""
        summary_data = {
            "Trading Mode": cls.TRADING_MODE,
            "Market": cls.MARKET,
            "Symbol": cls.SYMBOL,
            "Timeframe": cls.TIMEFRAME,
            "Risk per Trade": f"{cls.RISK_PER_TRADE * 100:.1f}%",
            "Testnet": cls.BINANCE_TESTNET,
            "Database": cls.DATABASE_URL,
            "Logging": cls.LOG_FILE,
        }
        for k, v in summary_data.items():
            print(f"{k:20}: {v}")
