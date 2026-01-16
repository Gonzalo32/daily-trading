"""
Sistema de seguimiento de progreso para Machine Learning
Monitorea cuántos datos se han recopilado y cuándo el modelo está listo para LIVE trading
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional

from src.utils.logging_setup import setup_logging


class MLProgressTracker:
    """
    Rastrea el progreso de recopilación de datos y entrenamiento ML.
    
    Determina cuando el sistema está listo para operar en modo LIVE basado en:
    - Cantidad de trades ejecutados
    - Calidad de los datos
    - Performance del modelo entrenado
    """
    
    # Umbrales para considerar el sistema listo
    MIN_TRADES_FOR_BASIC_ML = 500      # Mínimo para entrenar modelo básico
    MIN_TRADES_FOR_READY = 2000        # Recomendado para considerar "listo"
    MIN_TRADES_FOR_PRODUCTION = 5000   # Óptimo para producción
    
    def __init__(self, data_file: str = "src/ml/training_data.csv"):
        self.data_file = data_file
        self.progress_file = "ml_progress.json"
        self.logger = setup_logging(__name__)
        
    def get_training_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del dataset de entrenamiento"""
        try:
            if not os.path.exists(self.data_file):
                return {
                    "total_rows": 0,
                    "executed_trades": 0,
                    "rejected_signals": 0,
                    "no_signal_contexts": 0,
                    "ready_for_training": False,
                    "ready_for_live": False,
                }
            
            df = pd.read_csv(self.data_file, on_bad_lines='skip', encoding='utf-8')
            
            executed = len(df[df.get("trade_type", "") == "executed"]) if "trade_type" in df.columns else 0
            rejected = len(df[df.get("trade_type", "") == "rejected"]) if "trade_type" in df.columns else 0
            no_signal = len(df[df.get("trade_type", "") == "no_signal"]) if "trade_type" in df.columns else 0
            
            return {
                "total_rows": len(df),
                "executed_trades": executed,
                "rejected_signals": rejected,
                "no_signal_contexts": no_signal,
                "ready_for_training": executed >= self.MIN_TRADES_FOR_BASIC_ML,
                "ready_for_live": executed >= self.MIN_TRADES_FOR_READY,
                "ready_for_production": executed >= self.MIN_TRADES_FOR_PRODUCTION,
            }
        except Exception as e:
            self.logger.warning(f"⚠️ Error calculando estadísticas: {e}")
            return {
                "total_rows": 0,
                "executed_trades": 0,
                "rejected_signals": 0,
                "no_signal_contexts": 0,
                "ready_for_training": False,
                "ready_for_live": False,
            }
    
    def get_progress_percentage(self) -> float:
        """Retorna porcentaje de progreso hacia estar listo para LIVE (0-100)"""
        stats = self.get_training_stats()
        executed = stats["executed_trades"]
        
        if executed >= self.MIN_TRADES_FOR_PRODUCTION:
            return 100.0
        elif executed >= self.MIN_TRADES_FOR_READY:
            return 75.0 + ((executed - self.MIN_TRADES_FOR_READY) / (self.MIN_TRADES_FOR_PRODUCTION - self.MIN_TRADES_FOR_READY)) * 25.0
        elif executed >= self.MIN_TRADES_FOR_BASIC_ML:
            return 50.0 + ((executed - self.MIN_TRADES_FOR_BASIC_ML) / (self.MIN_TRADES_FOR_READY - self.MIN_TRADES_FOR_BASIC_ML)) * 25.0
        else:
            return (executed / self.MIN_TRADES_FOR_BASIC_ML) * 50.0
    
    def save_progress(self, stats: Dict[str, Any]):
        """Guarda el progreso actual"""
        try:
            progress = {
                "last_updated": datetime.now().isoformat(),
                "stats": stats,
                "progress_percentage": self.get_progress_percentage(),
            }
            
            os.makedirs(os.path.dirname(self.progress_file) if os.path.dirname(self.progress_file) else ".", exist_ok=True)
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            self.logger.warning(f"⚠️ Error guardando progreso: {e}")
    
    def get_status_message(self) -> str:
        """Retorna mensaje de estado legible"""
        stats = self.get_training_stats()
        progress = self.get_progress_percentage()
        
        executed = stats["executed_trades"]
        
        if executed >= self.MIN_TRADES_FOR_PRODUCTION:
            return f"✅ LISTO PARA PRODUCCIÓN - {executed} trades ejecutados ({progress:.1f}%)"
        elif executed >= self.MIN_TRADES_FOR_READY:
            return f"✅ LISTO PARA LIVE TRADING - {executed} trades ejecutados ({progress:.1f}%)"
        elif executed >= self.MIN_TRADES_FOR_BASIC_ML:
            return f"🟡 ENTRENANDO MODELO - {executed}/{self.MIN_TRADES_FOR_PRODUCTION} trades ({progress:.1f}%)"
        else:
            return f"🔄 RECOPILANDO DATOS - {executed}/{self.MIN_TRADES_FOR_BASIC_ML} trades ({progress:.1f}%)"
    
    def log_progress(self):
        """Log del progreso actual"""
        stats = self.get_training_stats()
        progress = self.get_progress_percentage()
        
        self.logger.info("=" * 60)
        self.logger.info("📊 PROGRESO DE MACHINE LEARNING")
        self.logger.info("=" * 60)
        self.logger.info(f"   Total de registros: {stats['total_rows']}")
        self.logger.info(f"   Trades ejecutados: {stats['executed_trades']}")
        self.logger.info(f"   Señales rechazadas: {stats['rejected_signals']}")
        self.logger.info(f"   Contextos sin señal: {stats['no_signal_contexts']}")
        self.logger.info(f"   Progreso: {progress:.1f}%")
        self.logger.info(f"   Estado: {self.get_status_message()}")
        
        if stats['ready_for_training']:
            self.logger.info("   ✅ Listo para entrenar modelo básico")
        if stats['ready_for_live']:
            self.logger.info("   ✅ Listo para LIVE trading")
        if stats['ready_for_production']:
            self.logger.info("   ✅ Listo para producción")
        
        self.logger.info("=" * 60)
        
        # Guardar progreso
        self.save_progress(stats)
