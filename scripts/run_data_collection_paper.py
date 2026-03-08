import argparse
import asyncio
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def _resolve_repo_root() -> Path:
    base = Path(__file__).resolve()
    candidates = [base.parents[1], base.parents[2], base.parent]
    for candidate in candidates:
        if (candidate / "daily-trading" / "main.py").exists():
            return candidate
        if (candidate / "main.py").exists():
            return candidate
    return base.parents[1]


def _resolve_path(repo_root: Path, path: str) -> str:
    if os.path.isabs(path):
        return path
    return str(repo_root / path)


async def _run_bot_for_minutes(minutes: int) -> None:
    import importlib
    main_module = importlib.import_module("main")
    TradingBot = getattr(main_module, "TradingBot")

    bot = TradingBot()
    task = asyncio.create_task(bot.start())
    try:
        await asyncio.sleep(minutes * 60)
        await bot.stop()
        if getattr(bot, "order_executor", None):
            try:
                await bot.order_executor.close()
            except (AttributeError, RuntimeError):
                pass
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def _run_export(repo_root: Path, db_path: str, args) -> bool:
    out_path = _resolve_path(repo_root, args.out)
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "export_ml_decisions.py"),
        "--since-hours",
        str(args.since_hours),
        "--limit",
        str(args.export_limit),
        "--out",
        out_path,
        "--db",
        db_path,
    ]
    result = subprocess.run(
        cmd, cwd=str(repo_root), capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        print(f"ERROR: Export falló: {result.stderr.strip()}")
        return False
    if not os.path.exists(out_path):
        print(f"ERROR: Export no generó archivo: {out_path}")
        return False
    try:
        with open(out_path, "r", encoding="utf-8") as f:
            header = f.readline().strip()
        if not header.startswith("id,created_at"):
            print(f"ERROR: Export sin header esperado: {header}")
            return False
    except OSError as e:
        print(f"ERROR: Error leyendo export: {e}")
        return False
    print(f"OK: Export OK: {out_path}")
    return True


def _query_counts(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ml_decisions")
    total = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM ml_decisions WHERE side IN ('BUY','SELL')")
    buy_sell = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM ml_decisions WHERE executed = 1")
    executed = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM ml_decisions WHERE pnl IS NOT NULL")
    pnl_not_null = cursor.fetchone()[0] or 0
    conn.close()
    return total, buy_sell, executed, pnl_not_null


def parse_args():
    parser = argparse.ArgumentParser(
        description="PAPER Data Collection Run (tiempo acotado)."
    )
    parser.add_argument("--minutes", type=int, default=20)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--export-limit", type=int, default=5000)
    parser.add_argument("--since-hours", type=float, default=2)
    parser.add_argument(
        "--out",
        default="data/ml_decisions_export_last.csv",
        help="Ruta de salida CSV",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Habilitar dashboard en localhost durante la corrida",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = _resolve_repo_root()
    app_root = repo_root / "daily-trading"
    if app_root.exists():
        sys.path.insert(0, str(app_root))
        os.chdir(str(repo_root))
    else:
        sys.path.insert(0, str(repo_root))

    os.environ["TRADING_MODE"] = "PAPER"
    os.environ["DATA_COLLECTION_MODE"] = "true"
    os.environ["ML_ENABLED"] = "true"
    os.environ["ML_MODE"] = "shadow"
    os.environ["ML_GATING_LIVE_ENABLED"] = "false"
    os.environ["ENABLE_LEGACY_ML_FILTER"] = "false"
    if args.symbol:
        os.environ["SYMBOL"] = args.symbol
    os.environ["ENABLE_DASHBOARD"] = "true" if args.dashboard else "false"

    try:
        asyncio.run(_run_bot_for_minutes(args.minutes))
    except (RuntimeError, OSError) as e:
        print(f"ERROR: Error ejecutando bot: {e}")
        return 1

    db_path = _resolve_path(
        repo_root, os.getenv("ML_DECISIONS_DB_PATH", "data/ml_decisions.db")
    )
    if not os.path.exists(db_path):
        print(f"ERROR: DB no encontrada: {db_path}")
        return 1

    try:
        total, buy_sell, executed, pnl_not_null = _query_counts(db_path)
    except sqlite3.Error as e:
        print(f"ERROR: Error leyendo DB: {e}")
        return 1

    print(f"OK: rows_total={total}")
    print(f"OK: buy_sell={buy_sell}")
    print(f"OK: executed_1={executed}")
    print(f"OK: pnl_not_null={pnl_not_null}")

    export_ok = _run_export(repo_root, db_path, args)
    if not export_ok:
        return 1

    if executed > 0 and pnl_not_null > 0:
        print("OK: podés dejarlo corriendo más tiempo (PAPER) para recolectar datos.")
    else:
        print(
            "NO: no conviene dejarlo horas. Falta generar trades reales/cierres. "
            "Revisar strategy/umbrales."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
