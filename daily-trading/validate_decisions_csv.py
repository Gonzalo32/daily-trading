"""
Validador de decisions.csv
Valida enums, consistencia DecisionOutcome/ExecutedAction, y estructura del CSV.
"""

import pandas as pd
import sys
from pathlib import Path

from src.utils.decision_constants import (
    DecisionOutcome,
    ExecutedAction,
    VALID_DECISION_OUTCOMES,
    VALID_EXECUTED_ACTIONS,
    validate_decision_consistency
)


def validate_decisions_csv(csv_path: str = "src/ml/decisions.csv") -> bool:
    """
    Valida decisions.csv:
    - Enums válidos (DecisionOutcome, ExecutedAction)
    - Consistencia (HOLD+EXECUTED, BUY/SELL sin EXECUTED, etc.)
    - Columnas correctas
    - strategy_signal ∈ {"BUY","SELL","NONE"}

    Returns:
        True si pasa todas las validaciones, False si hay errores
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"❌ Archivo no encontrado: {csv_path}")
        return False

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        return False

    print(f"📊 Validando {len(df)} DecisionSamples en {csv_path}...")

    errors = []
    warnings = []

    # Validar columnas esperadas
    expected_columns = [
        "timestamp", "symbol",
        "ema_cross_diff_pct", "atr_pct", "rsi_normalized",
        "price_to_fast_pct", "price_to_slow_pct",
        "trend_direction", "trend_strength",
        "decision_buy_possible", "decision_sell_possible", "decision_hold_possible",
        "strategy_signal", "executed_action", "was_executed",
        "regime", "volatility_level",
        "decision_outcome", "reject_reason", "reason"
    ]

    missing_columns = set(expected_columns) - set(df.columns)
    if missing_columns:
        errors.append(f"❌ Columnas faltantes: {missing_columns}")

    extra_columns = set(df.columns) - set(expected_columns)
    if extra_columns:
        warnings.append(f"⚠️ Columnas extra (no esperadas): {extra_columns}")

    # Validar enums
    invalid_outcomes = df[~df["decision_outcome"].isin(
        VALID_DECISION_OUTCOMES)]
    if len(invalid_outcomes) > 0:
        errors.append(
            f"❌ {len(invalid_outcomes)} DecisionSamples con decision_outcome inválido:")
        for idx, row in invalid_outcomes.iterrows():
            errors.append(
                f"   Línea {idx+2}: decision_outcome='{row['decision_outcome']}'")

    invalid_actions = df[~df["executed_action"].isin(VALID_EXECUTED_ACTIONS)]
    if len(invalid_actions) > 0:
        errors.append(
            f"❌ {len(invalid_actions)} DecisionSamples con executed_action inválido:")
        for idx, row in invalid_actions.iterrows():
            errors.append(
                f"   Línea {idx+2}: executed_action='{row['executed_action']}'")

    # Validar strategy_signal ∈ {"BUY","SELL","NONE"}
    invalid_signals = df[~df["strategy_signal"].isin(["BUY", "SELL", "NONE"])]
    if len(invalid_signals) > 0:
        errors.append(
            f"❌ {len(invalid_signals)} DecisionSamples con strategy_signal inválido:")
        for idx, row in invalid_signals.iterrows():
            errors.append(
                f"   Línea {idx+2}: strategy_signal='{row['strategy_signal']}'")

    # Validar consistencia DecisionOutcome/ExecutedAction
    consistency_errors = []
    for idx, row in df.iterrows():
        is_valid, error = validate_decision_consistency(
            row["executed_action"],
            row["decision_outcome"],
            row["strategy_signal"]
        )
        if not is_valid:
            consistency_errors.append((idx+2, error, row))

    if consistency_errors:
        errors.append(
            f"❌ {len(consistency_errors)} DecisionSamples con inconsistencias:")
        # Mostrar primeros 10
        for line_num, error_msg, row in consistency_errors[:10]:
            errors.append(f"   Línea {line_num}: {error_msg}")
            errors.append(
                f"      executed_action={row['executed_action']}, decision_outcome={row['decision_outcome']}, strategy_signal={row['strategy_signal']}")
        if len(consistency_errors) > 10:
            errors.append(f"   ... y {len(consistency_errors) - 10} más")

    # Validar NO_SIGNAL + reject_reason (debe ser None o "limits (paper only)")
    no_signal_with_reject = df[
        (df["decision_outcome"] == DecisionOutcome.NO_SIGNAL.value) &
        (df["reject_reason"].notna()) &
        (df["reject_reason"] != "") &
        (~df["reject_reason"].str.contains(r"limits \(paper only\)", na=False))
    ]
    if len(no_signal_with_reject) > 0:
        warnings.append(
            f"⚠️ {len(no_signal_with_reject)} DecisionSamples con NO_SIGNAL pero reject_reason no vacío (debe ser None o 'limits (paper only)')")

    # Validar EXECUTED sin BUY/SELL
    executed_with_hold = df[
        (df["decision_outcome"] == DecisionOutcome.EXECUTED.value) &
        (df["executed_action"] == ExecutedAction.HOLD.value)
    ]
    if len(executed_with_hold) > 0:
        errors.append(
            f"❌ {len(executed_with_hold)} DecisionSamples con EXECUTED pero executed_action=HOLD (prohibido)")

    # Reportar conteos por outcome
    print("\n📈 Conteos por decision_outcome:")
    outcome_counts = df["decision_outcome"].value_counts()
    for outcome, count in outcome_counts.items():
        print(f"   {outcome}: {count}")

    print("\n📈 Conteos por executed_action:")
    action_counts = df["executed_action"].value_counts()
    for action, count in action_counts.items():
        print(f"   {action}: {count}")

    # Mostrar errores y warnings
    if warnings:
        print("\n⚠️ WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")

    if errors:
        print("\n❌ ERRORES ENCONTRADOS:")
        for error in errors:
            print(f"   {error}")
        return False

    print("\n✅ Validación exitosa: todos los DecisionSamples son consistentes")
    return True


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "src/ml/decisions.csv"
    success = validate_decisions_csv(csv_path)
    sys.exit(0 if success else 1)
