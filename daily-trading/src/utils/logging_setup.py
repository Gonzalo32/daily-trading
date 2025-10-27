"""
Sistema de logging unificado para el bot de trading.
Incluye:
- Logging rotativo en archivo y consola.
- Loggers especializados por módulo (mercado, estrategia, riesgo, ejecución, notificaciones).
- Clase TradingLogger para registrar eventos específicos de trading.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional


# ======================================================
# CONFIGURACIÓN GENERAL DE LOGGING
# ======================================================
def setup_logging(name: str = __name__, logfile: str = "logs/trading_bot.log", log_level: str = "INFO") -> logging.Logger:
    """
    Configura el logger principal del bot con formato unificado y rotación de archivos.

    Args:
        name: Nombre del logger (por defecto, módulo actual).
        logfile: Ruta del archivo de log.
        log_level: Nivel de detalle (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Logger configurado.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Evitar duplicar handlers si ya está configurado
    if logger.handlers:
        return logger

    # Crear carpeta de logs si no existe
    log_dir = os.path.dirname(logfile)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Formato unificado de logs
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Handler rotativo de archivo
    file_handler = RotatingFileHandler(logfile, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(fmt)
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Configurar loggers secundarios (módulos)
    _setup_specific_loggers()

    logger.info("✅ Sistema de logging inicializado correctamente.")
    return logger


# ======================================================
# LOGGERS ESPECÍFICOS POR MÓDULO
# ======================================================
def _setup_specific_loggers():
    """Crea loggers específicos para distintos módulos del bot"""
    module_loggers = {
        "trading_bot.market_data": logging.INFO,
        "trading_bot.strategy": logging.INFO,
        "trading_bot.risk": logging.WARNING,
        "trading_bot.execution": logging.INFO,
        "trading_bot.notifications": logging.INFO,
    }

    for name, level in module_loggers.items():
        mod_logger = logging.getLogger(name)
        mod_logger.setLevel(level)


# ======================================================
# CLASES ESPECIALIZADAS
# ======================================================
class TradingLogger:
    """Logger especializado para registrar eventos de trading (operaciones, riesgo, rendimiento, etc.)"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("trading_bot")

    def log_trade(self, trade_data: dict):
        """Registrar una operación de trading"""
        try:
            msg = (
                f"TRADE - {trade_data.get('action', 'UNKNOWN')} "
                f"{trade_data.get('symbol', 'UNKNOWN')} "
                f"@ {trade_data.get('price', 0):.4f} | "
                f"Size: {trade_data.get('size', 0):.4f} | "
                f"Reason: {trade_data.get('reason', 'N/A')}"
            )
            self.logger.info(msg)
        except Exception as e:
            self.logger.error(f"Error registrando trade: {e}")

    def log_position_opened(self, position: dict):
        """Registrar apertura de posición"""
        try:
            msg = (
                f"POSITION OPENED - {position.get('side', 'UNKNOWN')} "
                f"{position.get('symbol', 'UNKNOWN')} "
                f"@ {position.get('entry_price', 0):.4f} | "
                f"Size: {position.get('size', 0):.4f} | "
                f"Stop: {position.get('stop_loss', 0):.4f} | "
                f"Target: {position.get('take_profit', 0):.4f}"
            )
            self.logger.info(msg)
        except Exception as e:
            self.logger.error(f"Error registrando apertura de posición: {e}")

    def log_position_closed(self, position: dict, pnl: float):
        """Registrar cierre de posición"""
        try:
            msg = (
                f"POSITION CLOSED - {position.get('side', 'UNKNOWN')} "
                f"{position.get('symbol', 'UNKNOWN')} "
                f"PnL: {pnl:.2f} | "
                f"Reason: {position.get('close_reason', 'N/A')}"
            )
            self.logger.info(msg)
        except Exception as e:
            self.logger.error(f"Error registrando cierre de posición: {e}")

    def log_risk_event(self, event_type: str, details: dict):
        """Registrar evento de riesgo"""
        try:
            msg = f"RISK EVENT - {event_type}: {details}"
            self.logger.warning(msg)
        except Exception as e:
            self.logger.error(f"Error registrando evento de riesgo: {e}")

    def log_performance(self, metrics: dict):
        """Registrar métricas de rendimiento"""
        try:
            msg = (
                f"PERFORMANCE - Daily PnL: {metrics.get('daily_pnl', 0):.2f} | "
                f"Trades: {metrics.get('total_trades', 0)} | "
                f"Win Rate: {metrics.get('win_rate', 0):.2%} | "
                f"Max DD: {metrics.get('max_drawdown', 0):.2%}"
            )
            self.logger.info(msg)
        except Exception as e:
            self.logger.error(f"Error registrando métricas de rendimiento: {e}")


# ======================================================
# FUNCIONES DE UTILIDAD
# ======================================================
def get_trading_logger() -> TradingLogger:
    """Devuelve un logger especializado para registrar eventos de trading"""
    logger = logging.getLogger("trading_bot")
    return TradingLogger(logger)
