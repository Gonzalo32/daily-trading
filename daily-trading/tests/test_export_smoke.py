import csv
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def _create_db(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE ml_decisions (
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
        """
        INSERT INTO ml_decisions (
            created_at, decision_id, trade_id, symbol, side, mode,
            model_version, feature_version, threshold, ml_score, ml_prediction,
            ml_action, reason, features_json, would_execute, executed,
            trade_type, target, pnl, r_multiple, exit_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "2024-01-01T00:00:00",
            "dec-1",
            None,
            "BTC/USDT",
            "BUY",
            "shadow",
            "v1",
            "f1",
            0.55,
            0.6,
            1,
            "ALLOW",
            "test",
            None,
            1,
            1,
            "executed",
            1,
            10.0,
            2.0,
            "tp",
        ),
    )
    conn.commit()
    conn.close()


def test_export_ml_decisions_smoke():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "export_ml_decisions.py"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        db_path = tmpdir_path / "ml_decisions.db"
        out_path = tmpdir_path / "export.csv"
        _create_db(db_path)

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--db",
                str(db_path),
                "--out",
                str(out_path),
                "--limit",
                "10",
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert out_path.exists()

        with out_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, [])
        assert header[:3] == ["created_at", "decision_id", "trade_id"]
