"""
Reporte de auditoría del dataset ML

Analiza decisions.csv y training_data.csv para verificar:
- Más DecisionSamples que trades ejecutados
- HOLD explícitos con diferentes outcomes
- Ninguna feature depende de precio absoluto, equity, pnl
- executed_action SOLO es BUY/SELL cuando hubo ejecución real
"""

import pandas as pd
import os
from pathlib import Path

def analyze_dataset():
    """Analiza el dataset y genera reporte completo"""
    
    print("=" * 80)
    print("AUDITORÍA COMPLETA DEL DATASET ML")
    print("=" * 80)
    print()
    
    # 1. Analizar decisions.csv
    decisions_path = "src/ml/decisions.csv"
    decisions_df = None
    
    if os.path.exists(decisions_path):
        try:
            decisions_df = pd.read_csv(decisions_path)
            print(f"✅ decisions.csv encontrado: {len(decisions_df)} DecisionSamples")
        except Exception as e:
            print(f"❌ Error leyendo decisions.csv: {e}")
    else:
        print(f"⚠️ decisions.csv no encontrado en {decisions_path}")
        print("   (El bot debe estar en modo PAPER para generar DecisionSamples)")
    
    # 2. Analizar training_data.csv
    training_data_path = "src/ml/training_data.csv"
    training_df = None
    
    if os.path.exists(training_data_path):
        try:
            training_df = pd.read_csv(training_data_path)
            print(f"✅ training_data.csv encontrado: {len(training_df)} registros")
        except Exception as e:
            print(f"❌ Error leyendo training_data.csv: {e}")
    else:
        print(f"⚠️ training_data.csv no encontrado en {training_data_path}")
    
    print("\n" + "=" * 80)
    
    # 3. Auditoría de decisions.csv
    if decisions_df is not None and len(decisions_df) > 0:
        audit_decisions(decisions_df)
    else:
        print("\n⚠️ No hay datos en decisions.csv para auditar")
        print("   El bot debe ejecutarse en modo PAPER para generar DecisionSamples")
    
    # 4. Auditoría de training_data.csv
    if training_df is not None and len(training_df) > 0:
        audit_training_data(training_df)
    else:
        print("\n⚠️ No hay datos en training_data.csv para auditar")
    
    # 5. Balance del dataset
    print("\n" + "=" * 80)
    print("BALANCE DEL DATASET")
    print("=" * 80)
    
    if decisions_df is not None and training_df is not None:
        decisions_count = len(decisions_df)
        trades_count = len(training_df[training_df.get('trade_type', '') == 'executed']) if 'trade_type' in training_df.columns else len(training_df)
        
        print(f"\n📊 CONTEOS:")
        print(f"   DecisionSamples: {decisions_count}")
        print(f"   Trades ejecutados: {trades_count}")
        
        if trades_count > 0:
            ratio = decisions_count / trades_count
            print(f"\n   Ratio DecisionSamples / Trades: {ratio:.2f}")
            
            if decisions_count > trades_count:
                print("   ✅ Hay más DecisionSamples que trades (correcto)")
                if ratio >= 2:
                    print("   ✅ Ratio >= 2 (dataset bien balanceado)")
                else:
                    print("   ⚠️ Ratio < 2 (considerar aumentar downsampling de HOLD)")
            else:
                print("   ❌ Hay menos DecisionSamples que trades (revisar lógica)")
        else:
            print("   ⚠️ No hay trades ejecutados para comparar")
    elif decisions_df is not None:
        print(f"\n📊 DecisionSamples: {len(decisions_df)}")
        print("   ⚠️ No hay training_data.csv para comparar")
    elif training_df is not None:
        trades_count = len(training_df[training_df.get('trade_type', '') == 'executed']) if 'trade_type' in training_df.columns else len(training_df)
        print(f"\n📊 Trades ejecutados: {trades_count}")
        print("   ⚠️ No hay decisions.csv para comparar")
    else:
        print("\n❌ No hay datos disponibles para auditar")
        print("   Ejecutar el bot en modo PAPER para generar datos")


def audit_decisions(df):
    """Audita decisions.csv"""
    print("\n" + "=" * 80)
    print("AUDITORÍA DE decisions.csv")
    print("=" * 80)
    
    # 1. Conteo por decision_outcome
    print("\n📊 1. CONTEO POR decision_outcome")
    if "decision_outcome" in df.columns:
        outcome_counts = df["decision_outcome"].value_counts()
        print("   Distribución:")
        for outcome, count in outcome_counts.items():
            pct = (count / len(df)) * 100
            print(f"   - {outcome}: {count} ({pct:.1f}%)")
    else:
        print("   ⚠️ Columna decision_outcome no encontrada")
    
    # 2. Ratio HOLD vs BUY/SELL
    print("\n📈 2. RATIO HOLD vs BUY/SELL")
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
    
    # 3. HOLD explícitos con diferentes outcomes
    print("\n🛑 3. HOLD EXPLÍCITOS POR OUTCOME")
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
    
    # 4. Verificar executed_action vs was_executed
    print("\n✅ 4. VERIFICACIÓN executed_action vs was_executed")
    if "executed_action" in df.columns and "was_executed" in df.columns:
        # executed_action debe ser BUY/SELL solo cuando was_executed=True
        buy_sell_without_execution = df[
            (df["executed_action"].isin(["BUY", "SELL"])) & 
            (df["was_executed"] == False)
        ]
        if len(buy_sell_without_execution) > 0:
            print(f"   ❌ {len(buy_sell_without_execution)} registros con executed_action=BUY/SELL pero was_executed=False")
        else:
            print("   ✅ executed_action=BUY/SELL solo cuando was_executed=True")
        
        # was_executed=True debe corresponder a BUY/SELL
        executed_without_buy_sell = df[
            (df["was_executed"] == True) & 
            (~df["executed_action"].isin(["BUY", "SELL"]))
        ]
        if len(executed_without_buy_sell) > 0:
            print(f"   ❌ {len(executed_without_buy_sell)} registros con was_executed=True pero executed_action no es BUY/SELL")
        else:
            print("   ✅ was_executed=True solo cuando executed_action=BUY/SELL")
    else:
        print("   ⚠️ Columnas executed_action o was_executed no encontradas")
    
    # 5. Verificar data leakage
    print("\n🔍 5. VERIFICACIÓN DE DATA LEAKAGE")
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
    else:
        print("   ✅ No hay columnas con información absoluta en features")
    
    # 6. Combinaciones executed_action + decision_outcome
    print("\n🔗 6. COMBINACIONES executed_action + decision_outcome")
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


def audit_training_data(df):
    """Audita training_data.csv"""
    print("\n" + "=" * 80)
    print("AUDITORÍA DE training_data.csv")
    print("=" * 80)
    
    # Verificar features relativas
    print("\n🔍 VERIFICACIÓN DE FEATURES RELATIVAS")
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
    
    # Verificar data leakage
    print("\n🔍 VERIFICACIÓN DE DATA LEAKAGE")
    forbidden_patterns = ["price", "capital", "balance", "equity"]
    forbidden_cols = []
    for col in df.columns:
        col_lower = col.lower()
        if any(pattern in col_lower for pattern in forbidden_patterns):
            # Permitir entry_price, exit_price (son outcomes, no features)
            if col_lower not in ["entry_price", "exit_price", "price_to_fast_pct", "price_to_slow_pct"]:
                forbidden_cols.append(col)
    
    if forbidden_cols:
        print(f"   ⚠️ Columnas con información absoluta detectadas: {forbidden_cols}")
        print("      (Verificar que no se usen como features de entrada)")
    else:
        print("   ✅ No hay columnas con información absoluta en features")
    
    # Resumen de trades
    print("\n📊 RESUMEN DE TRADES")
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


if __name__ == "__main__":
    analyze_dataset()
    print("\n" + "=" * 80)
    print("AUDITORÍA COMPLETADA")
    print("=" * 80)
