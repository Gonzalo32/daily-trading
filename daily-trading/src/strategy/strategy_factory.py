
from typing import Union
from config import Config
from src.utils.logging_setup import setup_logging
from src.strategy.trading_strategy import TradingStrategy, ProductionStrategy
from src.strategy.learning_strategy import LearningStrategy


class StrategyFactory:

    @staticmethod
    def create_strategy(config: Config) -> Union[ProductionStrategy, LearningStrategy]:
 
        logger = setup_logging(__name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        
        if config.TRADING_MODE == "PAPER":
            logger.info("=" * 60)
            logger.info("📚 MODO PAPER: Usando LearningStrategy")
            logger.info("   - Estrategia permisiva para generar muchos datos")
            logger.info("   - Optimiza diversidad, no rentabilidad")
            logger.info("   - Usa solo features relativas (robusto a cambios de precio)")
            logger.info("=" * 60)
            return LearningStrategy(config)
        else:
            logger.info("=" * 60)
            logger.info("🏭 MODO LIVE: Usando ProductionStrategy")
            logger.info("   - Estrategia selectiva de alta probabilidad")
            logger.info("   - Genera pocas señales de alta calidad")
            logger.info("   - Optimiza rentabilidad y protección de capital")
            logger.info("=" * 60)
            return ProductionStrategy(config)
