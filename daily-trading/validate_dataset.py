import sys
import csv
from collections import Counter
from typing import List, Dict, Any

# === CONFIGURACIÓN ===

# ⚠️ NOTA: Este validador está diseñado para training_data.csv (formato de trades ejecutados)
# Para validar decisions.csv, usar validate_decisions_csv.py
EXPECTED_COLUMNS = [
    # --- core decision ---
    "timestamp",
    "symbol",
    "executed_action",
    "decision_outcome",
    "reject_reason",

    # --- strategy / signal ---
    "strategy_signal",
    "signal_strength",

    # --- market features ---
    "price",
    "rsi",
    "ema_fast",
    "ema_slow",
    "atr",

    # --- regime ---
    "market_regime",

    # --- bot state snapshot ---
    "daily_pnl",
    "daily_trades",

    # --- target (si existe, no obligatorio en PAPER) ---
    "target",
]

VALID_EXECUTED_ACTIONS = {"BUY", "SELL", "HOLD"}
VALID_DECISION_OUTCOMES = {
    "no_signal",
    "executed",
    "rejected_by_risk",
    "rejected_by_limits",
    "rejected_by_filters",
    "rejected_by_execution",
}

# === HELPERS ===

def fail(msg: str):
    print(f"❌ ERROR: {msg}")
    sys.exit(1)

def warn(msg: str):
    print(f"⚠️ WARNING: {msg}")

def ok(msg: str):
    print(f"✅ {msg}")

# === VALIDACIONES ===

def validate_columns(header: List[str]):
    missing = [c for c in EXPECTED_COLUMNS if c not in header]
    extra = [c for c in header if c not in EXPECTED_COLUMNS]

    if missing:
        fail(f"Faltan columnas esperadas: {missing}")
    if extra:
        warn(f"Columnas extra detectadas (no bloquea): {extra}")

    ok("Columnas del CSV válidas")

def validate_row_semantics(row: Dict[str, Any], line_num: int):
    ea = row.get("executed_action")
    outcome = row.get("decision_outcome")
    reject = row.get("reject_reason")

    # --- enums válidos ---
    if ea not in VALID_EXECUTED_ACTIONS:
        fail(f"Línea {line_num}: executed_action inválido: {ea}")

    if outcome not in VALID_DECISION_OUTCOMES:
        fail(f"Línea {line_num}: decision_outcome inválido: {outcome}")

    # --- reglas semánticas ---
    if ea == "HOLD" and outcome == "executed":
        fail(f"Línea {line_num}: HOLD no puede tener outcome=executed")

    if ea in {"BUY", "SELL"} and outcome != "executed":
        fail(
            f"Línea {line_num}: {ea} debe tener outcome=executed "
            f"(tiene {outcome})"
        )

    if outcome == "no_signal" and reject not in ("", None):
        # excepción: PAPER limits informativos
        if "limits (paper only)" not in str(reject):
            warn(
                f"Línea {line_num}: no_signal con reject_reason='{reject}' "
                "(¿ruido semántico?)"
            )

def validate_row_length(row: Dict[str, Any], expected_len: int, line_num: int):
    if len(row) != expected_len:
        fail(
            f"Línea {line_num}: cantidad de columnas incorrecta "
            f"(esperado={expected_len}, actual={len(row)})"
        )

# === MAIN ===

def main(csv_path: str):
    print("🔍 Validando dataset ML:", csv_path)
    print("-" * 60)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames

        if not header:
            fail("CSV sin header")

        validate_columns(header)

        total_rows = 0
        executed = 0
        holds = 0
        buy_sell = 0

        for i, row in enumerate(reader, start=2):
            validate_row_length(row, len(header), i)
            validate_row_semantics(row, i)

            total_rows += 1
            ea = row.get("executed_action")
            if ea == "HOLD":
                holds += 1
            else:
                buy_sell += 1
                executed += 1

        print("-" * 60)
        ok(f"Filas totales: {total_rows}")
        ok(f"HOLD samples: {holds}")
        ok(f"BUY/SELL samples: {buy_sell}")
        ok(f"Trades ejecutados: {executed}")

        if total_rows == 0:
            warn("Dataset vacío")

        print("🎯 Dataset válido. No se detectó corrupción.")
        print("🔒 Listo para entrenamiento ML.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python validate_dataset.py path/al/training_data.csv")
        sys.exit(1)

    main(sys.argv[1])
