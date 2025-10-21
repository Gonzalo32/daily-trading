"""
Configuración de logging para el bot de trading
"""

import logging
import os
from datetime import datetime
from typing import Optional

def setup_logger(log_level: str = 'INFO', log_file: Optional[str] = None) -> logging.Logger:
    """
    Configurar el sistema de logging del bot
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Archivo de log (opcional)
    
    Returns:
        Logger configurado
    """
    
    # Crear logger principal
    logger = logging.getLogger('trading_bot')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Evitar duplicar handlers
    if logger.handlers:
        return logger
    
    # Crear formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo (si se especifica)
    if log_file:
        # Crear directorio de logs si no existe
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Configurar loggers específicos
    _setup_specific_loggers()
    
    return logger

def _setup_specific_loggers():
    """Configurar loggers específicos para diferentes módulos"""
    
    # Logger para datos de mercado
    market_logger = logging.getLogger('trading_bot.market_data')
    market_logger.setLevel(logging.INFO)
    
    # Logger para estrategia
    strategy_logger = logging.getLogger('trading_bot.strategy')
    strategy_logger.setLevel(logging.INFO)
    
    # Logger para gestión de riesgo
    risk_logger = logging.getLogger('trading_bot.risk')
    risk_logger.setLevel(logging.WARNING)
    
    # Logger para ejecución de órdenes
    execution_logger = logging.getLogger('trading_bot.execution')
    execution_logger.setLevel(logging.INFO)
    
    # Logger para notificaciones
    notification_logger = logging.getLogger('trading_bot.notifications')
    notification_logger.setLevel(logging.INFO)

class TradingLogger:
    """Logger especializado para operaciones de trading"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
    def log_trade(self, trade_data: dict):
        """Registrar operación de trading"""
        try:
            message = (
                f"TRADE - {trade_data.get('action', 'UNKNOWN')} "
                f"{trade_data.get('symbol', 'UNKNOWN')} "
                f"@ {trade_data.get('price', 0):.4f} "
                f"Size: {trade_data.get('size', 0):.4f} "
                f"Reason: {trade_data.get('reason', 'N/A')}"
            )
            self.logger.info(message)
        except Exception as e:
            self.logger.error(f"Error registrando trade: {e}")
            
    def log_position_opened(self, position: dict):
        """Registrar apertura de posición"""
        try:
            message = (
                f"POSITION OPENED - {position.get('side', 'UNKNOWN')} "
                f"{position.get('symbol', 'UNKNOWN')} "
                f"@ {position.get('entry_price', 0):.4f} "
                f"Size: {position.get('size', 0):.4f} "
                f"Stop: {position.get('stop_loss', 0):.4f} "
                f"Target: {position.get('take_profit', 0):.4f}"
            )
            self.logger.info(message)
        except Exception as e:
            self.logger.error(f"Error registrando apertura de posición: {e}")
            
    def log_position_closed(self, position: dict, pnl: float):
        """Registrar cierre de posición"""
        try:
            message = (
                f"POSITION CLOSED - {position.get('side', 'UNKNOWN')} "
                f"{position.get('symbol', 'UNKNOWN')} "
                f"@ {position.get('entry_price', 0):.4f} "
                f"PnL: {pnl:.2f} "
                f"Reason: {position.get('close_reason', 'N/A')}"
            )
            self.logger.info(message)
        except Exception as e:
            self.logger.error(f"Error registrando cierre de posición: {e}")
            
    def log_risk_event(self, event_type: str, details: dict):
        """Registrar evento de riesgo"""
        try:
            message = f"RISK EVENT - {event_type}: {details}"
            self.logger.warning(message)
        except Exception as e:
            self.logger.error(f"Error registrando evento de riesgo: {e}")
            
    def log_performance(self, metrics: dict):
        """Registrar métricas de rendimiento"""
        try:
            message = (
                f"PERFORMANCE - "
                f"Daily PnL: {metrics.get('daily_pnl', 0):.2f} "
                f"Total Trades: {metrics.get('total_trades', 0)} "
                f"Win Rate: {metrics.get('win_rate', 0):.2%} "
                f"Max Drawdown: {metrics.get('max_drawdown', 0):.2%}"
            )
            self.logger.info(message)
        except Exception as e:
            self.logger.error(f"Error registrando métricas: {e}")

def get_trading_logger() -> TradingLogger:
    """Obtener logger especializado para trading"""
    logger = logging.getLogger('trading_bot')
    return TradingLogger(logger)
