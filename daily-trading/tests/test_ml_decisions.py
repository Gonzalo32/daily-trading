import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ml.ml_logger import MLDecisionLogger


class TestMLDecisionsDB(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "ml_decisions.db")
        self.logger = MLDecisionLogger(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _sample_record(self, decision_id: str) -> dict:
        return {
            "created_at": datetime.utcnow().isoformat(),
            "decision_id": decision_id,
            "trade_id": None,
            "symbol": "BTC/USDT",
            "side": "BUY",
            "mode": "shadow",
            "model_version": "shadow_stub_v1",
            "feature_version": "v1",
            "threshold": 0.55,
            "ml_score": 0.6,
            "ml_prediction": 1,
            "ml_action": "ALLOW",
            "reason": "Score >= threshold",
            "features_json": '{"atr_value":1.0}',
            "would_execute": 1,
            "executed": 0,
            "trade_type": None,
            "target": None,
            "pnl": None,
            "r_multiple": None,
            "exit_type": None,
        }

    def test_table_created(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ml_decisions'"
        )
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_insert_decision(self):
        record = self._sample_record("dec-1")
        self.logger.insert_decision(record)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ml_decisions")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_update_trade_outcome(self):
        record = self._sample_record("dec-2")
        self.logger.insert_decision(record)
        self.logger.update_trade_outcome(
            decision_id="dec-2",
            pnl=10.0,
            target=1,
            r_multiple=2.0,
            exit_type="take_profit",
        )
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT pnl, target, r_multiple, exit_type FROM ml_decisions WHERE decision_id = ?",
            ("dec-2",),
        )
        row = cursor.fetchone()
        conn.close()
        self.assertEqual(row, (10.0, 1, 2.0, "take_profit"))

    def test_execution_and_trade_outcome(self):
        record = self._sample_record("dec-3")
        self.logger.insert_decision(record)
        self.logger.update_execution_outcome(
            decision_id="dec-3",
            executed=1,
            trade_type="EXECUTED",
            trade_id="trade-999",
        )
        self.logger.update_trade_outcome(
            decision_id="dec-3",
            pnl=5.5,
            target=0,
            r_multiple=0.5,
            exit_type="stop_loss",
        )
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT executed, trade_type, trade_id, pnl, target, r_multiple, exit_type
            FROM ml_decisions
            WHERE decision_id = ?
            """,
            ("dec-3",),
        )
        row = cursor.fetchone()
        conn.close()
        self.assertEqual(row, (1, "EXECUTED", "trade-999", 5.5, 0, 0.5, "stop_loss"))

    def test_duplicate_decision_id_updates_latest(self):
        record_a = self._sample_record("dup-1")
        record_b = self._sample_record("dup-1")
        self.logger.insert_decision(record_a)
        self.logger.insert_decision(record_b)

        self.logger.update_execution_outcome(
            decision_id="dup-1",
            executed=1,
            trade_type="executed",
            trade_id="trade-123",
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT executed, trade_type, trade_id
            FROM ml_decisions
            WHERE decision_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            ("dup-1",),
        )
        row = cursor.fetchone()
        conn.close()
        self.assertEqual(row, (1, "executed", "trade-123"))


if __name__ == "__main__":
    unittest.main()
