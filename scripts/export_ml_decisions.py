import argparse
import csv
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path


def _resolve_repo_root() -> Path:
    base = Path(__file__).resolve()
    candidates = [base.parents[1], base.parents[2], base.parent]
    for candidate in candidates:
        if (candidate / "config.py").exists() or (candidate / "src").exists():
            return candidate
    return base.parents[1]


REPO_ROOT = _resolve_repo_root()
sys.path.insert(0, str(REPO_ROOT))

BASE_COLUMNS = [
    "id",
    "created_at",
    "decision_id",
    "trade_id",
    "symbol",
    "side",
    "mode",
    "model_version",
    "feature_version",
    "threshold",
    "ml_score",
    "ml_prediction",
    "ml_action",
    "reason",
    "would_execute",
    "executed",
    "trade_type",
    "target",
    "pnl",
    "r_multiple",
    "exit_type",
]

EXPORT_COLUMNS = BASE_COLUMNS + ["created_at_epoch"]


def _build_query(args, selected_columns):
    where = []
    params = []

    if args.since_hours is not None:
        since_dt = datetime.utcnow() - timedelta(hours=args.since_hours)
        where.append("created_at >= ?")
        params.append(since_dt.isoformat())

    if args.symbol:
        where.append("symbol = ?")
        params.append(args.symbol)

    sql = f"SELECT {', '.join(selected_columns)} FROM ml_decisions"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC"

    if args.limit is not None:
        sql += " LIMIT ?"
        params.append(args.limit)

    return sql, params


def _get_table_columns(cursor):
    cursor.execute("PRAGMA table_info(ml_decisions)")
    rows = cursor.fetchall()
    return {row[1] for row in rows}


def _validate_schema(available_columns) -> bool:
    required = {"created_at", "decision_id", "ml_action", "executed", "trade_type"}
    missing = sorted(required - available_columns)
    if missing:
        print(f"ERROR: ml_decisions schema invalido, faltan: {missing}", file=sys.stderr)
        return False
    return True


def _created_at_epoch(value):
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(value).timestamp())
    except ValueError:
        return None


def export_ml_decisions(args):
    if not os.path.exists(args.db):
        print(f"ERROR: DB no encontrada: {args.db}", file=sys.stderr)
        return 1

    out_dir = os.path.dirname(args.out) or "."
    os.makedirs(out_dir, exist_ok=True)

    mode = "a" if args.append else "w"
    write_header = True
    if args.append and os.path.exists(args.out) and os.path.getsize(args.out) > 0:
        write_header = False

    try:
        conn = sqlite3.connect(args.db)
        cursor = conn.cursor()
        available_columns = _get_table_columns(cursor)
        if not _validate_schema(available_columns):
            conn.close()
            return 1

        selected_columns = [c for c in BASE_COLUMNS if c in available_columns]
        if "id" not in available_columns:
            print("WARN: ml_decisions sin columna id, exportando sin id.")

        sql, params = _build_query(args, selected_columns)
        cursor.execute(sql, params)

        with open(args.out, mode, newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow([*selected_columns, "created_at_epoch"])
            rows = 0
            counts_action = {}
            counts_executed = {}
            counts_trade_type = {}
            for row in cursor.fetchall():
                row_dict = dict(zip(selected_columns, row))
                created_at_epoch = _created_at_epoch(row_dict.get("created_at"))
                writer.writerow([*row, created_at_epoch])
                rows += 1
                action = row_dict.get("ml_action") or "UNKNOWN"
                counts_action[action] = counts_action.get(action, 0) + 1
                executed = row_dict.get("executed")
                counts_executed[executed] = counts_executed.get(executed, 0) + 1
                trade_type = row_dict.get("trade_type") or "UNKNOWN"
                counts_trade_type[trade_type] = counts_trade_type.get(trade_type, 0) + 1
        conn.close()
        executed_1 = counts_executed.get(1, 0)
        executed_0 = counts_executed.get(0, 0)
        print(f"OK: Export completado: {rows} filas -> {args.out}")
        print(
            "Resumen: rows=%d | executed=1:%d | executed=0:%d | actions=%s | trade_type=%s"
            % (rows, executed_1, executed_0, counts_action, counts_trade_type)
        )
        return 0
    except (sqlite3.Error, OSError, ValueError) as e:
        print(f"ERROR: Error exportando decisiones ML: {e}", file=sys.stderr)
        return 1


def _default_db_path() -> str:
    return os.getenv("ML_DECISIONS_DB_PATH", "data/ml_decisions.db")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Exportar ml_decisions.db a CSV."
    )
    parser.add_argument(
        "--db",
        default=_default_db_path(),
        help="Ruta a ml_decisions.db",
    )
    parser.add_argument(
        "--out",
        default="data/ml_decisions_export.csv",
        help="Ruta de salida CSV",
    )
    parser.add_argument(
        "--since-hours",
        type=float,
        default=None,
        help="Exportar solo decisiones de las últimas N horas",
    )
    parser.add_argument(
        "--symbol",
        default=None,
        help="Filtrar por símbolo",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limitar cantidad de filas",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append al CSV de salida si existe",
    )
    return parser.parse_args()


if __name__ == "__main__":
    exit_code = export_ml_decisions(parse_args())
    sys.exit(exit_code)
