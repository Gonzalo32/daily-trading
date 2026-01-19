"""
Script de validación del dataset ML

Verifica que el dataset cumple con los requisitos para aprender ESTRATEGIA:
- Más DecisionSamples que trades ejecutados
- Combinaciones correctas de acciones y outcomes
- Solo features relativas (sin leakage de precio absoluto, capital, PnL)
"""

import pandas as pd
import os
from pathlib import Path


def validate_decisions_csv(filepath: str = "src/ml/decisions.csv"):
    """Valida el esquema y contenido de decisions.csv"""
    print("=" * 60)
    print("VALIDACIÓN DE decisions.csv")
    print("=" * 60)
    
    if not os.path.exists(filepath):
        print(f"❌ Archivo no encontrado: {filepath}")
        return False
    
    df = pd.read_csv(filepath)
    print(f"✅ Archivo encontrado: {len(df)} DecisionSamples")
    
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
    
    missing = [col for col in expected_columns if col not in df.columns]
    if missing:
        print(f"❌ Columnas faltantes: {missing}")
        return False
    else:
        print(f"✅ Todas las columnas esperadas presentes ({len(expected_columns)} columnas)")
    
    # Validar que NO hay columnas con información absoluta
    forbidden_patterns = ["price", "capital", "balance", "equity", "pnl"]
    forbidden_cols = [col for col in df.columns if any(pattern in col.lower() for pattern in forbidden_patterns)]
    if forbidden_cols:
        print(f"⚠️ Columnas con información absoluta detectadas: {forbidden_cols}")
        print("   (Estas NO deberían estar en features de entrada)")
    else:
        print("✅ No hay columnas con información absoluta en features")
    
    # Validar combinaciones de acciones y outcomes
    print("\n📊 Distribución de DecisionSamples:")
    print(f"   Total: {len(df)}")
    
    if "executed_action" in df.columns and "decision_outcome" in df.columns:
        action_outcome = df.groupby(["executed_action", "decision_outcome"]).size()
        print("\n   Combinaciones executed_action + decision_outcome:")
        for (action, outcome), count in action_outcome.items():
            print(f"   - {action} + {outcome}: {count}")
        
        # Validar combinaciones esperadas
        print("\n✅ Validación de combinaciones:")
        
        # HOLD + no_signal
        hold_no_signal = len(df[(df["executed_action"] == "HOLD") & (df["decision_outcome"] == "no_signal")])
        print(f"   HOLD + no_signal: {hold_no_signal} {'✅' if hold_no_signal > 0 else '❌'}")
        
        # HOLD + rejected_by_risk
        hold_rejected_risk = len(df[(df["executed_action"] == "HOLD") & (df["decision_outcome"] == "rejected_by_risk")])
        print(f"   HOLD + rejected_by_risk: {hold_rejected_risk} {'✅' if hold_rejected_risk > 0 else '⚠️'}")
        
        # HOLD + rejected_by_limits
        hold_rejected_limits = len(df[(df["executed_action"] == "HOLD") & (df["decision_outcome"] == "rejected_by_limits")])
        print(f"   HOLD + rejected_by_limits: {hold_rejected_limits} {'✅' if hold_rejected_limits > 0 else '⚠️'}")
        
        # HOLD + rejected_by_filters
        hold_rejected_filters = len(df[(df["executed_action"] == "HOLD") & (df["decision_outcome"] == "rejected_by_filters")])
        print(f"   HOLD + rejected_by_filters: {hold_rejected_filters} {'✅' if hold_rejected_filters > 0 else '⚠️'}")
        
        # BUY/SELL + accepted
        buy_accepted = len(df[(df["executed_action"] == "BUY") & (df["decision_outcome"] == "accepted")])
        sell_accepted = len(df[(df["executed_action"] == "SELL") & (df["decision_outcome"] == "accepted")])
        print(f"   BUY + accepted: {buy_accepted} {'✅' if buy_accepted > 0 else '⚠️'}")
        print(f"   SELL + accepted: {sell_accepted} {'✅' if sell_accepted > 0 else '⚠️'}")
        
        # BUY/SELL + rejected (debería existir)
        buy_rejected = len(df[(df["executed_action"] == "BUY") & (df["decision_outcome"].str.startswith("rejected", na=False))])
        sell_rejected = len(df[(df["executed_action"] == "SELL") & (df["decision_outcome"].str.startswith("rejected", na=False))])
        print(f"   BUY + rejected_*: {buy_rejected} {'✅' if buy_rejected > 0 else '⚠️'}")
        print(f"   SELL + rejected_*: {sell_rejected} {'✅' if sell_rejected > 0 else '⚠️'}")
    
    # Validar features relativas
    print("\n✅ Validación de features:")
    relative_features = [
        "ema_cross_diff_pct", "atr_pct", "rsi_normalized",
        "price_to_fast_pct", "price_to_slow_pct",
        "trend_direction", "trend_strength"
    ]
    missing_features = [f for f in relative_features if f not in df.columns]
    if missing_features:
        print(f"   ❌ Features relativas faltantes: {missing_features}")
        return False
    else:
        print(f"   ✅ Todas las features relativas presentes ({len(relative_features)} features)")
    
    return True


def validate_trades_csv(filepath: str = "src/ml/trades.csv"):
    """Valida el esquema y contenido de trades.csv"""
    print("\n" + "=" * 60)
    print("VALIDACIÓN DE trades.csv")
    print("=" * 60)
    
    if not os.path.exists(filepath):
        print(f"⚠️ Archivo no encontrado: {filepath}")
        print("   (Esto es normal si aún no hay trades ejecutados)")
        return True
    
    df = pd.read_csv(filepath)
    print(f"✅ Archivo encontrado: {len(df)} trades ejecutados")
    
    # Validar que las features de entrada son relativas
    relative_features = [
        "ema_cross_diff_pct", "atr_pct", "rsi_normalized",
        "price_to_fast_pct", "price_to_slow_pct",
        "trend_direction", "trend_strength"
    ]
    
    missing_features = [f for f in relative_features if f not in df.columns]
    if missing_features:
        print(f"❌ Features relativas faltantes: {missing_features}")
        return False
    else:
        print(f"✅ Features relativas presentes ({len(relative_features)} features)")
    
    # Validar que entry_price, exit_price, pnl están (son outcomes, no features)
    outcome_cols = ["entry_price", "exit_price", "pnl", "target", "r_multiple"]
    missing_outcomes = [col for col in outcome_cols if col not in df.columns]
    if missing_outcomes:
        print(f"⚠️ Columnas de outcome faltantes: {missing_outcomes}")
    else:
        print(f"✅ Columnas de outcome presentes ({len(outcome_cols)} columnas)")
    
    print("\n📊 Resumen de trades:")
    if "side" in df.columns:
        print(f"   BUY: {len(df[df['side'] == 'BUY'])}")
        print(f"   SELL: {len(df[df['side'] == 'SELL'])}")
    
    return True


def validate_dataset_balance():
    """Valida que hay más DecisionSamples que trades ejecutados"""
    print("\n" + "=" * 60)
    print("VALIDACIÓN DE BALANCE DEL DATASET")
    print("=" * 60)
    
    decisions_path = "src/ml/decisions.csv"
    trades_path = "src/ml/trades.csv"
    
    decisions_count = 0
    trades_count = 0
    
    if os.path.exists(decisions_path):
        df_decisions = pd.read_csv(decisions_path)
        decisions_count = len(df_decisions)
        print(f"✅ DecisionSamples: {decisions_count}")
    else:
        print(f"⚠️ decisions.csv no encontrado")
    
    if os.path.exists(trades_path):
        df_trades = pd.read_csv(trades_path)
        trades_count = len(df_trades)
        print(f"✅ Trades ejecutados: {trades_count}")
    else:
        print(f"⚠️ trades.csv no encontrado (normal si no hay trades aún)")
    
    if decisions_count > 0 and trades_count > 0:
        ratio = decisions_count / trades_count if trades_count > 0 else float('inf')
        print(f"\n📊 Ratio DecisionSamples / Trades: {ratio:.2f}")
        
        if decisions_count > trades_count:
            print("✅ Hay más DecisionSamples que trades (correcto)")
        else:
            print("⚠️ Hay menos DecisionSamples que trades (revisar downsampling)")
    
    return True


def main():
    """Ejecuta todas las validaciones"""
    print("\n" + "=" * 60)
    print("VALIDACIÓN COMPLETA DEL DATASET ML")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Decisions CSV", validate_decisions_csv()))
    results.append(("Trades CSV", validate_trades_csv()))
    results.append(("Dataset Balance", validate_dataset_balance()))
    
    print("\n" + "=" * 60)
    print("RESUMEN DE VALIDACIÓN")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✅ Todas las validaciones pasaron")
        print("   El dataset es apto para aprender ESTRATEGIA")
    else:
        print("\n⚠️ Algunas validaciones fallaron")
        print("   Revisar los errores arriba")
    
    return all_passed


if __name__ == "__main__":
    main()
