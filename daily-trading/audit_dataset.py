"""
Auditoría completa del dataset ML

Verifica:
- Más DecisionSamples que trades ejecutados
- HOLD explícitos con diferentes outcomes
- Ninguna feature depende de precio absoluto, equity, pnl
- executed_action SOLO es BUY/SELL cuando hubo ejecución real
- Conteo por decision_outcome
- Ratio HOLD vs BUY/SELL
- Balance del dataset
"""

import pandas as pd
import os
from pathlib import Path


def audit_decisions_csv(filepath: str = "src/ml/decisions.csv"):
    """Audita decisions.csv con verificaciones completas"""
    print("=" * 80)
    print("AUDITORÍA DE decisions.csv")
    print("=" * 80)
    
    if not os.path.exists(filepath):
        print(f"❌ Archivo no encontrado: {filepath}")
        return None
    
    try:
        df = pd.read_csv(filepath)
        print(f"✅ Archivo encontrado: {len(df)} DecisionSamples")
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")
        return None
    
    # 1. Verificar columnas esperadas
    print("\n📋 1. VERIFICACIÓN DE ESQUEMA")
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
        print(f"   ❌ Columnas faltantes: {missing}")
    else:
        print(f"   ✅ Todas las columnas esperadas presentes ({len(expected_columns)} columnas)")
    
    # 2. Verificar que NO hay features absolutas
    print("\n🔍 2. VERIFICACIÓN DE DATA LEAKAGE")
    forbidden_patterns = ["price", "capital", "balance", "equity", "pnl"]
    forbidden_cols = []
    for col in df.columns:
        col_lower = col.lower()
        if any(pattern in col_lower for pattern in forbidden_patterns):
            # Permitir columnas que son parte del nombre pero no son features absolutas
            if col_lower not in ["price_to_fast_pct", "price_to_slow_pct"]:
                forbidden_cols.append(col)
    
    if forbidden_cols:
        print(f"   ❌ Columnas con información absoluta detectadas: {forbidden_cols}")
        print("      (Estas NO deberían estar en features de entrada)")
    else:
        print("   ✅ No hay columnas con información absoluta en features")
    
    # 3. Verificar executed_action vs was_executed
    print("\n✅ 3. VERIFICACIÓN DE executed_action vs was_executed")
    if "executed_action" in df.columns and "was_executed" in df.columns:
        # executed_action debe ser BUY/SELL solo cuando was_executed=True
        buy_sell_without_execution = df[
            (df["executed_action"].isin(["BUY", "SELL"])) & 
            (df["was_executed"] == False)
        ]
        if len(buy_sell_without_execution) > 0:
            print(f"   ❌ {len(buy_sell_without_execution)} registros con executed_action=BUY/SELL pero was_executed=False")
            print("      (Esto es inconsistente)")
        else:
            print("   ✅ executed_action=BUY/SELL solo cuando was_executed=True")
        
        # was_executed=True debe corresponder a BUY/SELL
        executed_without_buy_sell = df[
            (df["was_executed"] == True) & 
            (~df["executed_action"].isin(["BUY", "SELL"]))
        ]
        if len(executed_without_buy_sell) > 0:
            print(f"   ❌ {len(executed_without_buy_sell)} registros con was_executed=True pero executed_action no es BUY/SELL")
            print("      (Esto es inconsistente)")
        else:
            print("   ✅ was_executed=True solo cuando executed_action=BUY/SELL")
    else:
        print("   ⚠️ Columnas executed_action o was_executed no encontradas")
    
    # 4. Conteo por decision_outcome
    print("\n📊 4. CONTEO POR decision_outcome")
    if "decision_outcome" in df.columns:
        outcome_counts = df["decision_outcome"].value_counts()
        print("   Distribución:")
        for outcome, count in outcome_counts.items():
            pct = (count / len(df)) * 100
            print(f"   - {outcome}: {count} ({pct:.1f}%)")
    else:
        print("   ⚠️ Columna decision_outcome no encontrada")
    
    # 5. HOLD explícitos con diferentes outcomes
    print("\n🛑 5. HOLD EXPLÍCITOS POR OUTCOME")
    if "executed_action" in df.columns and "decision_outcome" in df.columns:
        hold_samples = df[df["executed_action"] == "HOLD"]
        print(f"   Total HOLD: {len(hold_samples)}")
        
        if len(hold_samples) > 0:
            hold_outcomes = hold_samples["decision_outcome"].value_counts()
            print("   HOLD por outcome:")
            for outcome, count in hold_outcomes.items():
                pct = (count / len(hold_samples)) * 100
                status = "✅" if count > 0 else "❌"
                print(f"   {status} {outcome}: {count} ({pct:.1f}%)")
            
            # Verificar outcomes esperados
            required_outcomes = ["no_signal", "rejected_by_risk", "rejected_by_limits", "rejected_by_filters"]
            missing_outcomes = [outcome for outcome in required_outcomes if outcome not in hold_outcomes.index]
            if missing_outcomes:
                print(f"   ⚠️ Outcomes faltantes en HOLD: {missing_outcomes}")
            else:
                print("   ✅ Todos los outcomes esperados presentes en HOLD")
        else:
            print("   ❌ No hay muestras HOLD")
    else:
        print("   ⚠️ Columnas executed_action o decision_outcome no encontradas")
    
    # 6. Ratio HOLD vs BUY/SELL
    print("\n📈 6. RATIO HOLD vs BUY/SELL")
    if "executed_action" in df.columns:
        action_counts = df["executed_action"].value_counts()
        print("   Distribución por executed_action:")
        for action, count in action_counts.items():
            pct = (count / len(df)) * 100
            print(f"   - {action}: {count} ({pct:.1f}%)")
        
        hold_count = len(df[df["executed_action"] == "HOLD"])
        buy_sell_count = len(df[df["executed_action"].isin(["BUY", "SELL"])])
        
        if buy_sell_count > 0:
            ratio = hold_count / buy_sell_count
            print(f"\n   Ratio HOLD / (BUY+SELL): {ratio:.2f}")
            if ratio > 1:
                print("   ✅ Más HOLD que BUY/SELL (esperado para dataset balanceado)")
            else:
                print("   ⚠️ Menos HOLD que BUY/SELL (revisar downsampling)")
        else:
            print("   ⚠️ No hay muestras BUY/SELL para calcular ratio")
    else:
        print("   ⚠️ Columna executed_action no encontrada")
    
    # 7. Combinaciones executed_action + decision_outcome
    print("\n🔗 7. COMBINACIONES executed_action + decision_outcome")
    if "executed_action" in df.columns and "decision_outcome" in df.columns:
        action_outcome = df.groupby(["executed_action", "decision_outcome"]).size().reset_index(name="count")
        action_outcome = action_outcome.sort_values("count", ascending=False)
        
        print("   Top combinaciones:")
        for _, row in action_outcome.head(10).iterrows():
            print(f"   - {row['executed_action']} + {row['decision_outcome']}: {row['count']}")
        
        # Verificar combinaciones válidas
        print("\n   Validación de combinaciones:")
        
        # HOLD + no_signal
        hold_no_signal = len(df[(df["executed_action"] == "HOLD") & (df["decision_outcome"] == "no_signal")])
        print(f"   {'✅' if hold_no_signal > 0 else '❌'} HOLD + no_signal: {hold_no_signal}")
        
        # HOLD + rejected_by_risk
        hold_rejected_risk = len(df[(df["executed_action"] == "HOLD") & (df["decision_outcome"] == "rejected_by_risk")])
        print(f"   {'✅' if hold_rejected_risk > 0 else '⚠️'} HOLD + rejected_by_risk: {hold_rejected_risk}")
        
        # HOLD + rejected_by_limits
        hold_rejected_limits = len(df[(df["executed_action"] == "HOLD") & (df["decision_outcome"] == "rejected_by_limits")])
        print(f"   {'✅' if hold_rejected_limits > 0 else '⚠️'} HOLD + rejected_by_limits: {hold_rejected_limits}")
        
        # HOLD + rejected_by_filters
        hold_rejected_filters = len(df[(df["executed_action"] == "HOLD") & (df["decision_outcome"] == "rejected_by_filters")])
        print(f"   {'✅' if hold_rejected_filters > 0 else '⚠️'} HOLD + rejected_by_filters: {hold_rejected_filters}")
        
        # BUY/SELL + accepted
        buy_accepted = len(df[(df["executed_action"] == "BUY") & (df["decision_outcome"] == "accepted")])
        sell_accepted = len(df[(df["executed_action"] == "SELL") & (df["decision_outcome"] == "accepted")])
        print(f"   {'✅' if buy_accepted > 0 else '⚠️'} BUY + accepted: {buy_accepted}")
        print(f"   {'✅' if sell_accepted > 0 else '⚠️'} SELL + accepted: {sell_accepted}")
        
        # BUY/SELL + rejected (no debería existir, pero verificar)
        buy_rejected = len(df[(df["executed_action"] == "BUY") & (df["decision_outcome"].str.startswith("rejected", na=False))])
        sell_rejected = len(df[(df["executed_action"] == "SELL") & (df["decision_outcome"].str.startswith("rejected", na=False))])
        if buy_rejected > 0 or sell_rejected > 0:
            print(f"   ⚠️ BUY/SELL + rejected: BUY={buy_rejected}, SELL={sell_rejected} (revisar lógica)")
        else:
            print(f"   ✅ BUY/SELL nunca tiene outcome rejected (correcto)")
    else:
        print("   ⚠️ Columnas executed_action o decision_outcome no encontradas")
    
    return df


def audit_trades_csv(filepath: str = "src/ml/training_data.csv"):
    """Audita trades.csv (o training_data.csv) con verificaciones completas"""
    print("\n" + "=" * 80)
    print("AUDITORÍA DE trades.csv / training_data.csv")
    print("=" * 80)
    
    if not os.path.exists(filepath):
        print(f"⚠️ Archivo no encontrado: {filepath}")
        print("   (Esto es normal si aún no hay trades ejecutados)")
        return None
    
    try:
        df = pd.read_csv(filepath)
        print(f"✅ Archivo encontrado: {len(df)} trades ejecutados")
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")
        return None
    
    # 1. Verificar que las features de entrada son relativas
    print("\n🔍 1. VERIFICACIÓN DE FEATURES RELATIVAS")
    relative_features = [
        "ema_cross_diff_pct", "atr_pct", "rsi_normalized",
        "price_to_fast_pct", "price_to_slow_pct",
        "trend_direction", "trend_strength"
    ]
    
    missing_features = [f for f in relative_features if f not in df.columns]
    if missing_features:
        print(f"   ⚠️ Features relativas faltantes: {missing_features}")
    else:
        print(f"   ✅ Todas las features relativas presentes ({len(relative_features)} features)")
    
    # 2. Verificar que NO hay features absolutas
    print("\n🔍 2. VERIFICACIÓN DE DATA LEAKAGE")
    forbidden_patterns = ["price", "capital", "balance", "equity"]
    forbidden_cols = []
    for col in df.columns:
        col_lower = col.lower()
        if any(pattern in col_lower for pattern in forbidden_patterns):
            # Permitir entry_price, exit_price, pnl (son outcomes, no features)
            if col_lower not in ["entry_price", "exit_price", "price_to_fast_pct", "price_to_slow_pct"]:
                forbidden_cols.append(col)
    
    if forbidden_cols:
        print(f"   ⚠️ Columnas con información absoluta detectadas: {forbidden_cols}")
        print("      (Verificar que no se usen como features de entrada)")
    else:
        print("   ✅ No hay columnas con información absoluta en features")
    
    # 3. Verificar que entry_price, exit_price, pnl están (son outcomes)
    print("\n📊 3. VERIFICACIÓN DE OUTCOMES")
    outcome_cols = ["entry_price", "exit_price", "pnl", "target", "r_multiple"]
    missing_outcomes = [col for col in outcome_cols if col not in df.columns]
    if missing_outcomes:
        print(f"   ⚠️ Columnas de outcome faltantes: {missing_outcomes}")
    else:
        print(f"   ✅ Columnas de outcome presentes ({len(outcome_cols)} columnas)")
    
    # 4. Resumen de trades
    print("\n📈 4. RESUMEN DE TRADES")
    if "side" in df.columns:
        buy_count = len(df[df['side'] == 'BUY'])
        sell_count = len(df[df['side'] == 'SELL'])
        print(f"   BUY: {buy_count}")
        print(f"   SELL: {sell_count}")
        print(f"   Total: {len(df)}")
    
    if "pnl" in df.columns:
        total_pnl = df["pnl"].sum()
        avg_pnl = df["pnl"].mean()
        win_rate = len(df[df["pnl"] > 0]) / len(df) * 100 if len(df) > 0 else 0
        print(f"\n   PnL total: {total_pnl:.2f}")
        print(f"   PnL promedio: {avg_pnl:.2f}")
        print(f"   Win rate: {win_rate:.1f}%")
    
    return df


def audit_dataset_balance(decisions_df=None, trades_df=None):
    """Audita el balance del dataset"""
    print("\n" + "=" * 80)
    print("AUDITORÍA DE BALANCE DEL DATASET")
    print("=" * 80)
    
    decisions_path = "src/ml/decisions.csv"
    trades_path = "src/ml/training_data.csv"
    
    if decisions_df is None:
        if os.path.exists(decisions_path):
            try:
                decisions_df = pd.read_csv(decisions_path)
            except:
                decisions_df = None
    
    if trades_df is None:
        if os.path.exists(trades_path):
            try:
                trades_df = pd.read_csv(trades_path)
            except:
                trades_df = None
    
    decisions_count = len(decisions_df) if decisions_df is not None else 0
    trades_count = len(trades_df) if trades_df is not None else 0
    
    print(f"\n📊 CONTEOS:")
    print(f"   DecisionSamples: {decisions_count}")
    print(f"   Trades ejecutados: {trades_count}")
    
    if decisions_count > 0 and trades_count > 0:
        ratio = decisions_count / trades_count if trades_count > 0 else float('inf')
        print(f"\n   Ratio DecisionSamples / Trades: {ratio:.2f}")
        
        if decisions_count > trades_count:
            print("   ✅ Hay más DecisionSamples que trades (correcto)")
            if ratio >= 2:
                print("   ✅ Ratio >= 2 (dataset bien balanceado)")
            else:
                print("   ⚠️ Ratio < 2 (considerar aumentar downsampling de HOLD)")
        else:
            print("   ❌ Hay menos DecisionSamples que trades (revisar lógica)")
    elif decisions_count > 0 and trades_count == 0:
        print("\n   ⚠️ Hay DecisionSamples pero no hay trades ejecutados aún")
        print("   (Esto es normal al inicio de la recolección de datos)")
    elif decisions_count == 0:
        print("\n   ❌ No hay DecisionSamples (revisar que el bot esté generando datos)")
    
    # Verificar que executed_action=BUY/SELL corresponde a trades ejecutados
    if decisions_df is not None and trades_df is not None:
        if "executed_action" in decisions_df.columns:
            executed_count = len(decisions_df[decisions_df["executed_action"].isin(["BUY", "SELL"])])
            print(f"\n   DecisionSamples con executed_action=BUY/SELL: {executed_count}")
            print(f"   Trades ejecutados: {trades_count}")
            
            if executed_count == trades_count:
                print("   ✅ Coincidencia perfecta (correcto)")
            elif abs(executed_count - trades_count) <= 5:
                print(f"   ⚠️ Diferencia pequeña: {abs(executed_count - trades_count)} (puede ser por timing)")
            else:
                print(f"   ❌ Diferencia significativa: {abs(executed_count - trades_count)} (revisar lógica)")


def main():
    """Ejecuta auditoría completa"""
    print("\n" + "=" * 80)
    print("AUDITORÍA COMPLETA DEL DATASET ML")
    print("=" * 80)
    print()
    
    # Auditar decisions.csv
    decisions_df = audit_decisions_csv()
    
    # Auditar trades.csv / training_data.csv
    trades_df = audit_trades_csv()
    
    # Auditar balance
    audit_dataset_balance(decisions_df, trades_df)
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN DE AUDITORÍA")
    print("=" * 80)
    
    issues = []
    if decisions_df is None:
        issues.append("❌ decisions.csv no encontrado o con errores")
    if decisions_df is not None and len(decisions_df) == 0:
        issues.append("⚠️ decisions.csv está vacío")
    if trades_df is not None and len(trades_df) == 0:
        issues.append("⚠️ training_data.csv está vacío (normal si no hay trades aún)")
    
    if issues:
        print("\n⚠️ ISSUES ENCONTRADOS:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ Auditoría completada")
        print("   Revisar los detalles arriba para validar el dataset")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
