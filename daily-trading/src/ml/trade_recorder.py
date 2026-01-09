# pylint: disable=import-error,logging-fstring-interpolation,broad-except

import pandas as pd
import os
from src.utils.logging_setup import setup_logging


class TradeRecorder:
    """
    Registro compacto y útil para ML:
    Guarda risk_amount, atr_value, r_value y resultado real (pnl).
    """

    def __init__(self, data_file: str = "src/ml/training_data.csv"):
        self.data_file = data_file
        self.logger = setup_logging(__name__)

        if not os.path.exists(self.data_file):
            self._initialize_file()

    def _initialize_file(self):
        df = pd.DataFrame(columns=[
            "timestamp", "symbol", "side",
            "entry_price", "exit_price", "pnl",
            "size", "stop_loss", "take_profit",
            "duration_seconds",
            # ML features
            "risk_amount", "atr_value", "r_value",
            # TARGETS
            "target"
        ])
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        df.to_csv(self.data_file, index=False)
        self.logger.info(f"📁 Archivo ML creado: {self.data_file}")

    def record_trade(self, position: dict, exit_price: float, pnl: float):
        """Guarda el trade en el CSV con las features correctas."""
        try:
            duration = None
            if position.get("exit_time") and position.get("entry_time"):
                duration = (position["exit_time"] - position["entry_time"]).total_seconds()

            record = {
                "timestamp": position.get("entry_time"),
                "symbol": position.get("symbol"),
                "side": position.get("side"),
                "entry_price": position.get("entry_price"),
                "exit_price": exit_price,
                "pnl": pnl,
                "size": position.get("size"),
                "stop_loss": position.get("stop_loss"),
                "take_profit": position.get("take_profit"),
                "duration_seconds": duration,
                "risk_amount": position.get("risk_amount"),
                "atr_value": position.get("atr_value"),
                "r_value": position.get("r_value"),
                # TARGET 1 = ganó al menos 1R
                "target": 1 if pnl >= position.get("r_value", 1) else 0
            }

            df = pd.DataFrame([record])
            df.to_csv(self.data_file, mode="a", index=False, header=False)

            self.logger.info(
                f"💾 Trade guardado ML | {record['symbol']} | PnL={pnl:.2f} | Target={record['target']}"
            )

            # ENTRENAMIENTO AUTOMÁTICO (llamado correctamente)
            from src.ml.auto_trainer import auto_train_if_needed
            auto_train_if_needed()

        except Exception as e:
            self.logger.exception(f"❌ Error guardando trade: {e}")

    def get_training_data(self, limit: int = None):
        """
        Retorna el dataset completo de training o las últimas N filas.
        """
        try:
            if not os.path.exists(self.data_file):
                self.logger.warning("⚠️ No hay archivo de training_data todavía.")
                return pd.DataFrame()

            df = pd.read_csv(self.data_file)

            if limit is not None and limit > 0:
                df = df.tail(limit)

            self.logger.info(f"📚 Training data cargado ({len(df)} filas).")
            return df

        except Exception as e:
            self.logger.exception(f"❌ Error leyendo training_data: {e}")
            return pd.DataFrame()
