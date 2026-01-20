#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_dataset.py
Validador de sanidad para DecisionSamples guardados en CSV.

Qué valida (en orden):
1) Corrupción estructural:
   - filas con distinta cantidad de columnas
   - headers duplicados / vacíos
2) Enums / valores:
   - executed_action en {HOLD, BUY, SELL}
   - decision_outcome en set permitido (configurable)
3) Invariantes semánticos:
   - EXECUTED => executed_action ∈ {BUY, SELL}
   - executed_action BUY/SELL => decision_outcome == EXECUTED (si hay "EXECUTED" en outcomes)
   - HOLD no puede tener EXECUTED
   - NO_SIGNAL normalmente NO tiene reject_reason
     EXCEPCIÓN: PAPER con texto que contenga "paper limits" / "limits (paper only)"
4) Resumen y estadísticas para auditar densidad / distribución.

Uso:
  python validate_dataset.py path/al/decisions.csv

Opcional:
  python validate_dataset.py path/al/decisions.csv --strict
  python validate_dataset.py path/al/decisions.csv --outcomes EXECUTED,NO_SIGNAL,REJECTED_BY_RISK,REJECTED_BY_LIMITS,REJECTED_BY_EXECUTION
"""

import argparse
import csv
import sys
from collections import Counter, defaultdict

DEFAULT_VALID_ACTIONS = {"HOLD", "BUY", "SELL"}

# Si tu proyecto tiene otros outcomes, pasalos por --outcomes
DEFAULT_VALID_OUTCOMES = {
    "EXECUTED",
    "NO_SIGNAL",
    "REJECTED_BY_RISK",
    "REJECTED_BY_LIMITS",
    "REJECTED_BY_EXECUTION",
}

PAPER_LIMITS_TOKENS = ("paper limits", "limits (paper only)")

# Aliases comunes (por si cambian nombres de columnas)
COLUMN_ALIASES = {
    "executed_action": ["executed_action", "executedAction", "action_executed", "final_action", "final_executed_action"],
    "decision_outcome": ["decision_outcome", "decisionOutcome", "outcome", "final_outcome", "final_decision_outcome"],
    "reject_reason": ["reject_reason", "rejectReason", "rejection_reason", "reason_reject", "reject"],
    "strategy_signal": ["strategy_signal", "strategySignal", "signal", "strategy_action"],
    "timestamp": ["timestamp", "time", "datetime", "ts"],
    "symbol": ["symbol", "ticker"],
}

def _normalize(s: str) -> str:
    return (s or "").strip()

def _upper(s: str) -> str:
    return _normalize(s).upper()

def find_col(headers, logical_name: str):
    """Devuelve el nombre real de la columna si existe, o None."""
    hdr_set = {h: h for h in headers}
    for alias in COLUMN_ALIASES.get(logical_name, []):
        for h in headers:
            if h == alias:
                return h
    # fallback case-insensitive
    lower_map = {h.lower(): h for h in headers}
    for alias in COLUMN_ALIASES.get(logical_name, []):
        if alias.lower() in lower_map:
            return lower_map[alias.lower()]
    return None

def read_csv_rows(path: str):
    """
    Lee CSV con csv.reader para detectar filas corruptas por longitud.
    Devuelve: headers(list), rows(list of dict), bad_lines(list of (line_no, n_fields, expected, preview))
    """
    bad_lines = []
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            raise ValueError("CSV vacío: no tiene header.")

        headers = [h.strip() for h in headers]
        expected_len = len(headers)

        # headers inválidos
        if expected_len == 0:
            raise ValueError("Header vacío (0 columnas).")

        # duplicados / vacíos
        empties = [i for i, h in enumerate(headers) if not h]
        if empties:
            raise ValueError(f"Header tiene columnas vacías en índices: {empties}")

        dup = [h for h, c in Counter(headers).items() if c > 1]
        if dup:
            raise ValueError(f"Header tiene columnas duplicadas: {dup}")

        # leer filas
        for idx, fields in enumerate(reader, start=2):  # 1=header, entonces datos arrancan en 2
            if len(fields) != expected_len:
                preview = ",".join(fields[:10])
                bad_lines.append((idx, len(fields), expected_len, preview))
                continue

            row = {headers[i]: fields[i] for i in range(expected_len)}
            rows.append(row)

    return headers, rows, bad_lines

def validate_rows(rows, cols, valid_actions, valid_outcomes, strict: bool):
    """
    Valida invariantes y retorna (errors, warnings, stats)
    """
    errors = []
    warnings = []
    stats = {
        "total_rows": len(rows),
        "by_outcome": Counter(),
        "by_action": Counter(),
        "paper_limits_no_signal": 0,
        "no_signal_with_reason": 0,
        "executed_total": 0,
        "executed_with_hold": 0,
        "buy_sell_not_executed": 0,
    }

    col_action = cols["executed_action"]
    col_outcome = cols["decision_outcome"]
    col_reject = cols.get("reject_reason")

    for i, r in enumerate(rows, start=2):  # mantener referencia humana similar a CSV (aprox)
        action = _upper(r.get(col_action, ""))
        outcome = _upper(r.get(col_outcome, ""))
        reject_reason = _normalize(r.get(col_reject, "")) if col_reject else ""

        stats["by_action"][action or "<EMPTY>"] += 1
        stats["by_outcome"][outcome or "<EMPTY>"] += 1

        # enums básicos
        if action not in valid_actions:
            errors.append(f"L{i}: executed_action inválido: '{action}'")
        if outcome not in valid_outcomes:
            errors.append(f"L{i}: decision_outcome inválido: '{outcome}'")

        # invariantes
        if outcome == "EXECUTED":
            stats["executed_total"] += 1
            if action == "HOLD":
                stats["executed_with_hold"] += 1
                errors.append(f"L{i}: Invariante rota: outcome=EXECUTED pero executed_action=HOLD")
            if action not in {"BUY", "SELL"}:
                errors.append(f"L{i}: Invariante rota: outcome=EXECUTED pero action no es BUY/SELL (es '{action}')")

        # Si existe EXECUTED en outcomes, entonces BUY/SELL debería implicar EXECUTED
        if action in {"BUY", "SELL"} and "EXECUTED" in valid_outcomes and outcome != "EXECUTED":
            stats["buy_sell_not_executed"] += 1
            msg = f"L{i}: Invariante rota: action={action} pero outcome={outcome} (esperado EXECUTED)"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)

        # NO_SIGNAL reject_reason regla
        if outcome == "NO_SIGNAL":
            if reject_reason:
                stats["no_signal_with_reason"] += 1
                rr_low = reject_reason.lower()
                if any(tok in rr_low for tok in PAPER_LIMITS_TOKENS):
                    stats["paper_limits_no_signal"] += 1
                else:
                    msg = f"L{i}: NO_SIGNAL con reject_reason no permitido: '{reject_reason[:120]}'"
                    if strict:
                        errors.append(msg)
                    else:
                        warnings.append(msg)

    return errors, warnings, stats

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", help="Ruta al CSV de DecisionSamples")
    ap.add_argument("--strict", action="store_true", help="Convierte warnings semánticos en errores")
    ap.add_argument(
        "--outcomes",
        default=",".join(sorted(DEFAULT_VALID_OUTCOMES)),
        help="Lista de outcomes válidos separados por coma"
    )
    args = ap.parse_args()

    valid_outcomes = {o.strip().upper() for o in args.outcomes.split(",") if o.strip()}
    valid_actions = set(DEFAULT_VALID_ACTIONS)

    try:
        headers, rows, bad_lines = read_csv_rows(args.csv_path)
    except Exception as e:
        print(f"❌ ERROR leyendo CSV: {e}")
        sys.exit(2)

    if bad_lines:
        print("❌ CSV corrupto: filas con longitud distinta al header.")
        print(f"   Header columns: {len(headers)}")
        print("   Primeras 10 filas corruptas (linea, fields, expected, preview):")
        for item in bad_lines[:10]:
            print("   -", item)
        print(f"   Total filas corruptas: {len(bad_lines)}")
        sys.exit(3)

    # localizar columnas clave
    col_action = find_col(headers, "executed_action")
    col_outcome = find_col(headers, "decision_outcome")
    col_reject = find_col(headers, "reject_reason")
    col_signal = find_col(headers, "strategy_signal")

    missing = []
    if not col_action: missing.append("executed_action")
    if not col_outcome: missing.append("decision_outcome")

    if missing:
        print("❌ No puedo validar: faltan columnas obligatorias.")
        print("   Faltan:", missing)
        print("   Headers detectados:", headers[:40], ("..." if len(headers) > 40 else ""))
        sys.exit(4)

    cols = {
        "executed_action": col_action,
        "decision_outcome": col_outcome,
    }
    if col_reject:
        cols["reject_reason"] = col_reject
    if col_signal:
        cols["strategy_signal"] = col_signal

    errors, warnings, stats = validate_rows(
        rows=rows,
        cols=cols,
        valid_actions=valid_actions,
        valid_outcomes=valid_outcomes,
        strict=args.strict,
    )

    # output
    print("✅ CSV leíble y con header consistente.")
    print(f"   Rows: {stats['total_rows']}")

    print("\n📊 Distribución executed_action:")
    for k, v in stats["by_action"].most_common():
        print(f"   - {k}: {v}")

    print("\n📊 Distribución decision_outcome:")
    for k, v in stats["by_outcome"].most_common():
        print(f"   - {k}: {v}")

    if "NO_SIGNAL" in stats["by_outcome"]:
        print("\n🧾 NO_SIGNAL con reject_reason:")
        print(f"   - Total NO_SIGNAL con reject_reason: {stats['no_signal_with_reason']}")
        print(f"   - De esos, 'paper limits': {stats['paper_limits_no_signal']}")

    print("\n🧪 Invariantes:")
    print(f"   - EXECUTED total: {stats['executed_total']}")
    print(f"   - EXECUTED con HOLD (debe ser 0): {stats['executed_with_hold']}")
    print(f"   - BUY/SELL con outcome != EXECUTED: {stats['buy_sell_not_executed']}")

    if warnings:
        print("\n⚠️ WARNINGS (no fatales):")
        for w in warnings[:30]:
            print("   -", w)
        if len(warnings) > 30:
            print(f"   ... ({len(warnings)-30} más)")
    if errors:
        print("\n❌ ERRORES (fatales):")
        for e in errors[:50]:
            print("   -", e)
        if len(errors) > 50:
            print(f"   ... ({len(errors)-50} más)")
        sys.exit(5)

    print("\n✅ VALIDACIÓN OK. Dataset sano para entrenar / auditar.")
    sys.exit(0)

if __name__ == "__main__":
    main()
