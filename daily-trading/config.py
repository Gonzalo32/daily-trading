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

    @staticmethod
    def _resolve_model_file(path: str, default_filename: str) -> str:
        if not path:
            return os.path.join("models", default_filename)
        normalized = path.strip()
        if normalized.endswith("/") or normalized.endswith("\\") or os.path.isdir(normalized):
            return os.path.join(normalized, default_filename)
        if normalized.lower().endswith(".pkl"):
            return normalized
        return os.path.join(normalized, default_filename)

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

    # ⚠️ IMPORTANTE: MAX_DAILY_TRADES solo afecta ejecución de órdenes REALES
    # En PAPER, DecisionSamples SIEMPRE se crean (ilimitados para ML)
    # Solo limita cuántas órdenes reales se ejecutan por día
    MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "200"))
    # Informativo, no bloquea DecisionSamples
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
    STATE_PATH = os.getenv("STATE_PATH", "data/state.json")

    ENABLE_DASHBOARD = os.getenv("ENABLE_DASHBOARD", "true").lower() == "true"
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8000"))

    ENABLE_NOTIFICATIONS = os.getenv(
        "ENABLE_NOTIFICATIONS", "false").lower() == "true"
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    ENABLE_ML = os.getenv("ENABLE_ML", "false").lower() == "true"
    ENABLE_LEGACY_ML_FILTER = os.getenv(
        "ENABLE_LEGACY_ML_FILTER",
        "true" if ENABLE_ML else "false"
    ).lower() == "true"
    ML_MODEL_PATH = os.getenv("ML_MODEL_PATH", "models/model.pkl")
    ML_LEGACY_MODEL_FILE = _resolve_model_file(ML_MODEL_PATH, "model.pkl")
    ML_V2_MODEL_FILE = os.getenv("ML_V2_MODEL_FILE", "models/ml_v2_model.pkl")
    RETRAIN_FREQUENCY = int(os.getenv("RETRAIN_FREQUENCY", "7"))
    TRAINING_MODE = True

    ML_MIN_PROBABILITY = float(os.getenv("ML_MIN_PROBABILITY", "0.55"))
    ML_ENABLED = os.getenv("ML_ENABLED", "true").lower() == "true"
    ML_MODE = os.getenv("ML_MODE", "shadow").lower()
    ML_THRESHOLD = float(os.getenv("ML_THRESHOLD", "0.55"))
    MODEL_VERSION = os.getenv("MODEL_VERSION", "shadow_stub_v1")
    FEATURE_VERSION = os.getenv("FEATURE_VERSION", "v1")
    ML_DECISIONS_DB_PATH = os.getenv(
        "ML_DECISIONS_DB_PATH", "data/ml_decisions.db"
    )
    ML_GATING_LIVE_ENABLED = os.getenv(
        "ML_GATING_LIVE_ENABLED", "false"
    ).lower() == "true"
    ML_GATING_MODE = os.getenv("ML_GATING_MODE", "legacy").lower()
    ML_GATING_STRATEGY = os.getenv("ML_GATING_STRATEGY", "block").lower()
    ENABLE_AUTO_TRAIN = os.getenv("ENABLE_AUTO_TRAIN", "false").lower() == "true"
    ENABLE_TRAINING_SCHEMA_MIGRATION = os.getenv(
        "ENABLE_TRAINING_SCHEMA_MIGRATION", "false"
    ).lower() == "true"
    ML_AUDIT_EVERY_N_DECISIONS = int(
        os.getenv("ML_AUDIT_EVERY_N_DECISIONS", "200")
    )

    ML_LABEL_PROFIT_THRESHOLD_R = float(
        os.getenv("ML_LABEL_PROFIT_THRESHOLD_R", "0.0")
    )

    ENABLE_DEBUG_STRATEGY = os.getenv(
        "ENABLE_DEBUG_STRATEGY", "false").lower() == "true"

    MVP_MODE_ENABLED = os.getenv("MVP_MODE_ENABLED", "true").lower() == "true"
    MVP_MIN_TRADES_FOR_ADVANCED_FEATURES = int(
        os.getenv("MVP_MIN_TRADES_FOR_ADVANCED_FEATURES", "500"))

    MIN_COOLDOWN_BETWEEN_TRADES = float(
        os.getenv("MIN_COOLDOWN_BETWEEN_TRADES", "5.0"))

    DATA_COLLECTION_MODE = os.getenv(
        "DATA_COLLECTION_MODE", "false").lower() == "true"
    DATA_COLLECTION_RELAX_FACTOR = float(
        os.getenv("DATA_COLLECTION_RELAX_FACTOR", "1.0"))
    DATA_COLLECTION_MAX_TRADES_PER_DAY = int(
        os.getenv("DATA_COLLECTION_MAX_TRADES_PER_DAY", "500"))

    DECISION_HOLD_SAMPLE_RATE = int(
        os.getenv("DECISION_HOLD_SAMPLE_RATE", "10"))

    BACKTEST_START_DATE = os.getenv("BACKTEST_START_DATE", "2023-01-01")
    BACKTEST_END_DATE = os.getenv("BACKTEST_END_DATE", "2023-12-31")

    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))
    CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))

    ML_RETRAIN_EVERY = 500

    FORCE_CLOSE_TIMEOUT = 15

    if TRADING_MODE == "PAPER" and DATA_COLLECTION_MODE:
        relax_factor = max(DATA_COLLECTION_RELAX_FACTOR, 1.0)
        PAPER_MAX_DAILY_TRADES = max(
            PAPER_MAX_DAILY_TRADES, DATA_COLLECTION_MAX_TRADES_PER_DAY)
        EMA_DIFF_PCT_MIN = EMA_DIFF_PCT_MIN / relax_factor
        RSI_OVERBOUGHT = RSI_OVERBOUGHT + 5
        RSI_OVERSOLD = RSI_OVERSOLD - 5
        MIN_COOLDOWN_BETWEEN_TRADES = max(
            1.0, MIN_COOLDOWN_BETWEEN_TRADES / relax_factor)

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
