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


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except ImportError:
        pass


async def _run_bot_for_seconds(seconds: int) -> None:
    import importlib
    main_module = importlib.import_module("main")
    TradingBot = getattr(main_module, "TradingBot")

    bot = TradingBot()
    task = asyncio.create_task(bot.start())
    try:
        await asyncio.sleep(seconds)
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


def _resolve_path(repo_root: Path, path: str) -> str:
    if os.path.isabs(path):
        return path
    return str(repo_root / path)


def _check_db(db_path: str) -> bool:
    if not os.path.exists(db_path):
        print(f"ERROR: DB no encontrada: {db_path}")
        return False
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ml_decisions")
        total = cursor.fetchone()[0] or 0
        conn.close()
        if total <= 0:
            print("ERROR: DB existe pero sin filas en ml_decisions")
            return False
        print(f"OK: DB OK: {db_path} | filas={total}")
        return True
    except sqlite3.Error as e:
        print(f"ERROR: Error leyendo DB: {e}")
        return False


def _check_training_data(repo_root: Path) -> None:
    candidates = [
        repo_root / "src" / "ml" / "training_data.csv",
        repo_root / "daily-trading" / "src" / "ml" / "training_data.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            print(f"OK: training_data.csv encontrado: {candidate}")
            return
    print("WARN: training_data.csv no encontrado (puede ser normal si no hubo trades)")


def _run_export(repo_root: Path, db_path: str) -> bool:
    out_path = str(repo_root / "data" / "ml_decisions_export_smoke.csv")
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "export_ml_decisions.py"),
        "--limit",
        "100",
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
        if not header.startswith("created_at,decision_id,trade_id"):
            print(f"ERROR: Export sin header esperado: {header}")
            return False
    except OSError as e:
        print(f"ERROR: Error leyendo export: {e}")
        return False
    print(f"OK: Export OK: {out_path}")
    return True


def main() -> int:
    repo_root = _resolve_repo_root()
    app_root = repo_root / "daily-trading"
    if app_root.exists():
        sys.path.insert(0, str(app_root))
        os.chdir(str(repo_root))
    else:
        sys.path.insert(0, str(repo_root))

    _load_dotenv_if_available()

    os.environ["TRADING_MODE"] = "PAPER"
    os.environ["ML_ENABLED"] = "true"
    os.environ["ML_MODE"] = "shadow"
    os.environ["ENABLE_LEGACY_ML_FILTER"] = "false"
    os.environ["ML_GATING_LIVE_ENABLED"] = "false"
    os.environ["ENABLE_DASHBOARD"] = "false"

    try:
        asyncio.run(_run_bot_for_seconds(15))
    except (RuntimeError, OSError) as e:
        print(f"ERROR: Error ejecutando bot: {e}")
        return 1

    db_path = _resolve_path(
        repo_root, os.getenv("ML_DECISIONS_DB_PATH", "data/ml_decisions.db")
    )
    ok_db = _check_db(db_path)
    _check_training_data(repo_root)
    ok_export = _run_export(repo_root, db_path)

    if ok_db and ok_export:
        print("OK: Smoke test PAPER OK")
        return 0

    print("ERROR: Smoke test PAPER falló")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
