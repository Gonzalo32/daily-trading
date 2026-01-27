#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valida integridad de training_data.csv:
- Header consistente
- Todas las filas con el mismo numero de columnas
- Pandas puede leerlo sin on_bad_lines
"""

import csv
import sys
from pathlib import Path

import pandas as pd


EXPECTED_COLUMNS = [
    "timestamp", "symbol", "side", "decision_id",
    "entry_price", "exit_price", "pnl",
    "size", "stop_loss", "take_profit",
    "duration_seconds",
    "risk_amount", "atr_value", "r_value", "risk_multiplier",
    "ema_cross_diff_pct", "atr_pct", "rsi_normalized",
    "price_to_fast_pct", "price_to_slow_pct",
    "trend_direction", "trend_strength",
    "regime", "volatility_level",
    "target", "trade_type",
    "exit_type", "r_multiple", "time_in_trade"
]


def validate_csv_integrity(csv_path: str = "src/ml/training_data.csv") -> bool:
    path = Path(csv_path)
    if not path.exists():
        print(f"ERROR: archivo no encontrado: {csv_path}")
        return False

    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, [])

        if not header:
            print("ERROR: header vacio o inexistente.")
            return False

        header = [col.strip() for col in header]
        expected_without_decision_id = [
            col for col in EXPECTED_COLUMNS if col != "decision_id"
        ]

        if header == EXPECTED_COLUMNS:
            print("OK: header coincide con el esquema esperado.")
        elif header == expected_without_decision_id:
            print(
                "WARNING: header sin decision_id (compatibilidad hacia atras)."
            )
        else:
            print("ERROR: header inesperado.")
            print(f"Header encontrado: {header}")
            print(f"Header esperado:  {EXPECTED_COLUMNS}")
            return False

        expected_len = len(header)
        invalid_rows = 0
        for idx, row in enumerate(reader, start=2):
            if len(row) != expected_len:
                invalid_rows += 1
                print(
                    f"ERROR: fila {idx} con {len(row)} columnas (esperadas {expected_len})."
                )
                if invalid_rows >= 5:
                    break

        if invalid_rows > 0:
            print("ERROR: filas con cantidad de columnas inconsistente.")
            return False

    try:
        pd.read_csv(csv_path)
        print("OK: pandas pudo leer el CSV sin on_bad_lines.")
    except Exception as e:
        print(f"ERROR: pandas no pudo leer el CSV: {e}")
        return False

    return True


if __name__ == "__main__":
    target_path = sys.argv[1] if len(sys.argv) > 1 else "src/ml/training_data.csv"
    success = validate_csv_integrity(target_path)
    sys.exit(0 if success else 1)
