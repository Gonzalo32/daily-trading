"""
Alias para mantener compatibilidad con imports
"""

from src.utils.logging_setup import setup_logging as setup_logger, TradingLogger, get_trading_logger

__all__ = ['setup_logger', 'TradingLogger', 'get_trading_logger']

