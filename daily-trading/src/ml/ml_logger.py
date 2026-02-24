import os
import sqlite3
from typing import Any, Dict, Optional

from src.utils.logging_setup import setup_logging


class MLDecisionLogger:
    def __init__(self, db_path: str = "data/ml_decisions.db"):
        self.db_path = db_path
        self.logger = setup_logging(__name__)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._initialize_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize_db(self) -> None:
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ml_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    trade_id TEXT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    feature_version TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    ml_score REAL NULL,
                    ml_prediction INTEGER NULL,
                    ml_action TEXT NOT NULL,
                    reason TEXT NULL,
                    features_json TEXT NULL,
                    would_execute INTEGER NOT NULL,
                    executed INTEGER NOT NULL,
                    trade_type TEXT NULL,
                    target INTEGER NULL,
                    pnl REAL NULL,
                    r_multiple REAL NULL,
                    exit_type TEXT NULL
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ml_decisions_decision_id ON ml_decisions(decision_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ml_decisions_created_at ON ml_decisions(created_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ml_decisions_symbol_created_at ON ml_decisions(symbol, created_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ml_decisions_model_version ON ml_decisions(model_version)"
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.exception(f"❌ Error inicializando ml_decisions: {e}")

    def insert_decision(self, record: Dict[str, Any]) -> None:
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ml_decisions (
                    created_at, decision_id, trade_id, symbol, side, mode,
                    model_version, feature_version, threshold, ml_score, ml_prediction,
                    ml_action, reason, features_json, would_execute, executed,
                    trade_type, target, pnl, r_multiple, exit_type
                ) VALUES (
                    :created_at, :decision_id, :trade_id, :symbol, :side, :mode,
                    :model_version, :feature_version, :threshold, :ml_score, :ml_prediction,
                    :ml_action, :reason, :features_json, :would_execute, :executed,
                    :trade_type, :target, :pnl, :r_multiple, :exit_type
                )
                """,
                record,
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.exception(f"❌ Error insertando ml_decision: {e}")

    def update_execution_outcome(
        self,
        decision_id: str,
        executed: int,
        trade_type: Optional[str],
        trade_id: Optional[str] = None,
    ) -> None:
        if not decision_id:
            self.logger.warning(
                "⚠️ update_execution_outcome sin decision_id, se omite."
            )
            return

        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE ml_decisions
                SET executed = ?, trade_type = ?, trade_id = COALESCE(?, trade_id)
                WHERE id = (
                    SELECT id FROM ml_decisions
                    WHERE decision_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                )
                """,
                (executed, trade_type, trade_id, decision_id),
            )
            conn.commit()
            updated = cursor.rowcount
            conn.close()
            if updated == 0:
                self.logger.warning(
                    f"⚠️ No se encontró ml_decision para actualizar (decision_id={decision_id})"
                )
        except Exception as e:
            self.logger.exception(
                f"❌ Error actualizando outcome ml_decision: {e}"
            )

    def update_trade_outcome(
        self,
        decision_id: str,
        pnl: Optional[float],
        target: Optional[int],
        r_multiple: Optional[float],
        exit_type: Optional[str],
    ) -> None:
        if not decision_id:
            self.logger.warning(
                "⚠️ update_trade_outcome sin decision_id, se omite."
            )
            return

        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE ml_decisions
                SET pnl = ?, target = ?, r_multiple = ?, exit_type = ?
                WHERE id = (
                    SELECT id FROM ml_decisions
                    WHERE decision_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                )
                """,
                (pnl, target, r_multiple, exit_type, decision_id),
            )
            conn.commit()
            updated = cursor.rowcount
            conn.close()
            if updated == 0:
                self.logger.warning(
                    f"⚠️ No se encontró ml_decision para cierre (decision_id={decision_id})"
                )
        except Exception as e:
            self.logger.exception(
                f"❌ Error actualizando cierre ml_decision: {e}"
            )
