"""
Sistema de logging unificado para el bot de trading.
Incluye:
- Logging rotativo en archivo y consola.
- Loggers especializados por módulo (mercado, estrategia, riesgo, ejecución, notificaciones).
- Clase TradingLogger para registrar eventos específicos de trading.
"""

import logging
import os
from logging.handlers import RotatingFileHandler, BaseRotatingHandler
from datetime import datetime
from typing import Optional


                                                        
                                  
                                                        
class LineRotatingFileHandler(BaseRotatingHandler):
    """
    Handler que rota el archivo de log cuando alcanza un número máximo de líneas.
    """
    
    def __init__(self, filename, max_lines=100, backup_count=3, encoding='utf-8'):
        """
        Args:
            filename: Ruta del archivo de log
            max_lines: Número máximo de líneas antes de rotar (default: 100)
            backup_count: Número de archivos de backup a mantener (default: 3)
            encoding: Codificación del archivo (default: utf-8)
        """
        super().__init__(filename, 'a', encoding=encoding, delay=False)
        self.max_lines = max_lines
        self.backup_count = backup_count
        self.line_count = 0
        self._count_existing_lines()
    
    def _count_existing_lines(self):
        """Cuenta las líneas existentes en el archivo"""
        try:
            if os.path.exists(self.baseFilename):
                with open(self.baseFilename, 'r', encoding=self.encoding) as f:
                    self.line_count = sum(1 for _ in f)
        except Exception:
            self.line_count = 0
    
    def _truncate_file_to_lines(self, filepath, max_lines):
        """
        Trunca un archivo manteniendo solo las últimas max_lines líneas.
        
        Args:
            filepath: Ruta del archivo a truncar
            max_lines: Número máximo de líneas a mantener
        """
        try:
            if not os.path.exists(filepath):
                return
            
                                   
            with open(filepath, 'r', encoding=self.encoding) as f:
                lines = f.readlines()
            
                                                                              
            if len(lines) > max_lines:
                lines_to_keep = lines[-max_lines:]
                
                                                  
                with open(filepath, 'w', encoding=self.encoding) as f:
                    f.writelines(lines_to_keep)
        except Exception as e:
                                                                                            
            pass
    
    def shouldRollover(self, record):
        """Determina si debe rotar el archivo"""
        return self.line_count >= self.max_lines
    
    def doRollover(self):
        """Ejecuta la rotación del archivo"""
        try:
                                            
            if self.stream:
                try:
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
            
                                                                  
            for i in range(1, self.backup_count + 1):
                backup_file = f"{self.baseFilename}.{i}"
                if os.path.exists(backup_file):
                    self._truncate_file_to_lines(backup_file, self.max_lines)
            
                                      
            for i in range(self.backup_count - 1, 0, -1):
                sfn = f"{self.baseFilename}.{i}"
                dfn = f"{self.baseFilename}.{i + 1}"
                if os.path.exists(sfn):
                                                                
                    self._truncate_file_to_lines(sfn, self.max_lines)
                    
                    if os.path.exists(dfn):
                        try:
                            os.remove(dfn)
                        except Exception:
                            pass
                    try:
                        os.rename(sfn, dfn)
                                                                       
                        self._truncate_file_to_lines(dfn, self.max_lines)
                    except Exception:
                        pass
            
                                                   
            dfn = f"{self.baseFilename}.1"
            if os.path.exists(self.baseFilename):
                                                            
                self._truncate_file_to_lines(self.baseFilename, self.max_lines)
                
                if os.path.exists(dfn):
                    try:
                        os.remove(dfn)
                    except Exception:
                        pass
                try:
                    os.rename(self.baseFilename, dfn)
                                                              
                    self._truncate_file_to_lines(dfn, self.max_lines)
                except Exception:
                    pass
            
                               
            self.line_count = 0
            
                                 
            if not self.delay:
                try:
                    self.stream = self._open()
                except Exception as e:
                    print(f"ERROR al abrir archivo de log después de rotación: {e}")
                    self.stream = None
        except Exception as e:
            print(f"ERROR en rotación de log: {e}")
                                                       
            if not self.delay and self.stream is None:
                try:
                    self.stream = self._open()
                except Exception:
                    self.stream = None
    
    def emit(self, record):
        """Escribe el registro y actualiza el contador"""
        try:
            if self.shouldRollover(record):
                self.doRollover()
            
                                                 
            if self.stream is None:
                self.stream = self._open()
            
            msg = self.format(record)
            stream = self.stream
            
            if stream is None:
                                                         
                self.stream = self._open()
                stream = self.stream
            
            if stream is not None:
                stream.write(msg + self.terminator)
                self.flush()
                
                                                
                self.line_count += 1
            else:
                                                                                
                print(f"ERROR: No se pudo abrir el archivo de log: {self.baseFilename}")
            
        except Exception as e:
            self.handleError(record)


                                                        
                                  
                                                        
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

                                                     
    if logger.handlers:
        return logger

                                        
    log_dir = os.path.dirname(logfile)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

                               
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

                        
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

                                                                   
    file_handler = LineRotatingFileHandler(logfile, max_lines=100, backup_count=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

                                              
    _setup_specific_loggers()

    logger.info("✅ Sistema de logging inicializado correctamente.")
    return logger


                                                        
                                
                                                        
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


                                                        
                       
                                                        
def get_trading_logger() -> TradingLogger:
    """Devuelve un logger especializado para registrar eventos de trading"""
    logger = logging.getLogger("trading_bot")
    return TradingLogger(logger)
