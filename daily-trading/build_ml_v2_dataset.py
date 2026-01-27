#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML v2 Dataset Builder
Joins decisions.csv (features) with training_data.csv (targets)
Creates dataset with target = (r_multiple > 0)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("ML v2 DATASET BUILDER")
print("=" * 80)

print("\n" + "=" * 80)
print("1. LOADING DATA")
print("=" * 80)

print("\nLoading decisions.csv...")
try:
    def _read_csv_with_optional_header(path, expected_columns):
        with open(path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        header_tokens = [h.strip() for h in first_line.split(",")] if first_line else []
        header_present = "timestamp" in header_tokens and "symbol" in header_tokens
        if header_present:
            df = pd.read_csv(path)
            return df, header_tokens
        df = pd.read_csv(path, names=expected_columns)
        return df, []

    decisions, decisions_header = _read_csv_with_optional_header(
        "src/ml/decisions.csv",
        [
            "timestamp", "symbol", "decision_id",
            "ema_cross_diff_pct", "atr_pct", "rsi_normalized",
            "price_to_fast_pct", "price_to_slow_pct",
            "trend_direction", "trend_strength",
            "decision_buy_possible", "decision_sell_possible", "decision_hold_possible",
            "strategy_signal", "executed_action", "was_executed",
            "regime", "volatility_level",
            "decision_outcome", "reject_reason", "reason"
        ]
    )
    print(f"  Loaded: {len(decisions):,} rows")
    if decisions_header and "decision_id" not in decisions_header:
        print("  WARNING: decisions.csv sin decision_id en header. Se intentara continuar.")
except Exception as e:
    print(f"  ERROR loading decisions.csv: {e}")
    exit(1)

print("\nLoading training_data.csv...")
try:
    trades_columns = [
        "timestamp", "symbol", "side", "decision_id",
        "entry_price", "exit_price", "pnl",
        "size", "stop_loss", "take_profit", "duration_seconds",
        "risk_amount", "atr_value", "r_value", "risk_multiplier",
        "ema_cross_diff_pct", "atr_pct", "rsi_normalized",
        "price_to_fast_pct", "price_to_slow_pct",
        "trend_direction", "trend_strength",
        "regime", "volatility_level",
        "target", "trade_type",
        "exit_type", "r_multiple", "time_in_trade"
    ]
    trades, trades_header = _read_csv_with_optional_header(
        "src/ml/training_data.csv",
        trades_columns
    )
    print(f"  Loaded: {len(trades):,} rows")
    if trades_header and "decision_id" not in trades_header:
        print("  WARNING: training_data.csv sin decision_id en header. Se usaran fallbacks.")
except Exception as e:
    print(f"  ERROR loading training_data.csv: {e}")
    exit(1)

print("\n" + "=" * 80)
print("2. DATA CLEANING")
print("=" * 80)

print("\nCleaning decisions.csv...")
decisions.columns = decisions.columns.str.strip()
decisions['timestamp'] = pd.to_datetime(decisions['timestamp'], errors='coerce')
decisions['executed_action'] = decisions['executed_action'].astype(str).str.strip().str.upper()
decisions['decision_outcome'] = decisions['decision_outcome'].astype(str).str.strip().str.lower()
decisions['symbol'] = decisions['symbol'].astype(str).str.strip()
decisions['strategy_signal'] = decisions['strategy_signal'].astype(str).str.strip().str.upper()

print(f"  After cleaning: {len(decisions):,} rows")
print(f"  Missing timestamps: {decisions['timestamp'].isna().sum()}")

print("\nCleaning training_data.csv...")
trades.columns = trades.columns.str.strip()
trades['timestamp'] = pd.to_datetime(trades['timestamp'], errors='coerce')
trades['side'] = trades['side'].astype(str).str.strip().str.upper()
trades['symbol'] = trades['symbol'].astype(str).str.strip()
trades['decision_id'] = trades['decision_id'].astype(str).str.strip() if 'decision_id' in trades.columns else ''

if 'r_multiple' not in trades.columns or trades['r_multiple'].isna().all():
    if 'r_value' in trades.columns and 'pnl' in trades.columns:
        trades['r_multiple'] = trades['pnl'] / trades['r_value'].replace(0, np.nan)
        trades['r_multiple'] = trades['r_multiple'].fillna(0)
        print("  Created r_multiple from pnl / r_value")
    else:
        print("  WARNING: r_multiple not found and cannot be computed")
        trades['r_multiple'] = 0

print(f"  After cleaning: {len(trades):,} rows")
print(f"  Missing timestamps: {trades['timestamp'].isna().sum()}")
print(f"  Trades with r_multiple: {(trades['r_multiple'].notna()).sum()}")

print("\n" + "=" * 80)
print("3. FILTERING DECISIONS")
print("=" * 80)

initial_decisions = len(decisions)

decisions = decisions[
    (decisions['executed_action'].isin(['BUY', 'SELL'])) &
    (decisions['decision_outcome'] == 'executed') &
    (decisions['timestamp'].notna())
].copy()

print(f"\nFiltered decisions:")
print(f"  Initial: {initial_decisions:,}")
print(f"  After filter (BUY/SELL + executed): {len(decisions):,}")
print(f"  Dropped: {initial_decisions - len(decisions):,}")

if len(decisions) == 0:
    print("\nERROR: No valid decisions after filtering")
    exit(1)

print("\n" + "=" * 80)
print("4. JOINING DECISIONS WITH TRADES")
print("=" * 80)

print("\nJoining strategy:")
print("  1. Primary: decision_id match (if available)")
print("  2. Fallback: symbol + side + timestamp (±5 seconds)")
print("  3. Last resort: symbol + side only")

merged_rows = []
tolerance_seconds = 5

trades_used = set()
join_method_counts = {"decision_id": 0, "timestamp": 0, "symbol_side": 0}
fallback_warnings = {"missing_decision_id": 0, "timestamp": 0, "symbol_side": 0}

for idx, decision in decisions.iterrows():
    decision_id = decision.get('decision_id', '')
    has_decision_id = bool(decision_id and str(decision_id).strip())
    decision_time = decision['timestamp']
    decision_symbol = decision['symbol']
    decision_action = decision['executed_action']
    
    if pd.isna(decision_symbol) or pd.isna(decision_action):
        continue
    
    matched = False
    
    if has_decision_id:
        matching_trades = trades[
            (trades['decision_id'] == decision_id) &
            (~trades.index.isin(trades_used))
        ].copy()
        
        if len(matching_trades) > 0:
            best_match = matching_trades.iloc[0]
            row = decision.copy()
            row['r_multiple'] = best_match.get('r_multiple', 0)
            row['pnl'] = best_match.get('pnl', 0)
            row['exit_type'] = best_match.get('exit_type', 'unknown')
            row['duration_seconds'] = best_match.get('duration_seconds', 0)
            row['join_method'] = 'decision_id'
            merged_rows.append(row)
            trades_used.add(best_match.name)
            join_method_counts['decision_id'] += 1
            matched = True
    
    if not matched and pd.notna(decision_time):
        if not has_decision_id:
            fallback_warnings["missing_decision_id"] += 1
        matching_trades = trades[
            (trades['symbol'] == decision_symbol) &
            (trades['side'] == decision_action) &
            (trades['timestamp'].notna()) &
            (~trades.index.isin(trades_used))
        ].copy()
        
        if len(matching_trades) > 0:
            matching_trades['time_diff'] = abs((matching_trades['timestamp'] - decision_time).dt.total_seconds())
            best_match = matching_trades.loc[matching_trades['time_diff'].idxmin()]
            
            if best_match['time_diff'] <= tolerance_seconds:
                row = decision.copy()
                row['r_multiple'] = best_match.get('r_multiple', 0)
                row['pnl'] = best_match.get('pnl', 0)
                row['exit_type'] = best_match.get('exit_type', 'unknown')
                row['duration_seconds'] = best_match.get('duration_seconds', 0)
                row['join_time_diff'] = best_match['time_diff']
                row['join_method'] = 'timestamp'
                merged_rows.append(row)
                trades_used.add(best_match.name)
                join_method_counts['timestamp'] += 1
                fallback_warnings["timestamp"] += 1
                matched = True
    
    if not matched:
        if not has_decision_id:
            fallback_warnings["missing_decision_id"] += 1
        matching_trades = trades[
            (trades['symbol'] == decision_symbol) &
            (trades['side'] == decision_action) &
            (~trades.index.isin(trades_used))
        ].copy()
        
        if len(matching_trades) > 0:
            best_match = matching_trades.iloc[0]
            row = decision.copy()
            row['r_multiple'] = best_match.get('r_multiple', 0)
            row['pnl'] = best_match.get('pnl', 0)
            row['exit_type'] = best_match.get('exit_type', 'unknown')
            row['duration_seconds'] = best_match.get('duration_seconds', 0)
            row['join_method'] = 'symbol_side'
            merged_rows.append(row)
            trades_used.add(best_match.name)
            join_method_counts['symbol_side'] += 1
            fallback_warnings["symbol_side"] += 1

if len(merged_rows) == 0:
    print("\nERROR: No matches found after joining")
    exit(1)

ml_v2_df = pd.DataFrame(merged_rows)

print(f"\nJoin results:")
print(f"  Decisions to match: {len(decisions):,}")
print(f"  Successful matches: {len(ml_v2_df):,}")
print(f"  Match rate: {len(ml_v2_df)/len(decisions)*100:.1f}%")
print(f"\nJoin method breakdown:")
print(f"  - decision_id: {join_method_counts['decision_id']:,} ({join_method_counts['decision_id']/len(ml_v2_df)*100:.1f}%)")
print(f"  - timestamp: {join_method_counts['timestamp']:,} ({join_method_counts['timestamp']/len(ml_v2_df)*100:.1f}%)")
print(f"  - symbol+side: {join_method_counts['symbol_side']:,} ({join_method_counts['symbol_side']/len(ml_v2_df)*100:.1f}%)")
if fallback_warnings["missing_decision_id"] > 0:
    print(
        f"  WARNING: {fallback_warnings['missing_decision_id']:,} decisiones sin decision_id "
        "usaron fallback."
    )
if fallback_warnings["timestamp"] > 0:
    print(
        f"  WARNING: {fallback_warnings['timestamp']:,} joins por timestamp (±{tolerance_seconds}s)."
    )
if fallback_warnings["symbol_side"] > 0:
    print(
        f"  WARNING: {fallback_warnings['symbol_side']:,} joins por symbol+side."
    )

print("\n" + "=" * 80)
print("5. CREATING TARGET")
print("=" * 80)

ml_v2_df['target'] = (ml_v2_df['r_multiple'] > 0).astype(int)

print(f"\nTarget distribution:")
target_counts = ml_v2_df['target'].value_counts()
for target_val, count in target_counts.items():
    pct = count / len(ml_v2_df) * 100
    label = "R > 0 (winning)" if target_val == 1 else "R <= 0 (losing)"
    print(f"  {label}: {count:,} ({pct:.2f}%)")

print("\n" + "=" * 80)
print("6. FEATURE PREPARATION")
print("=" * 80)

print("\nExcluding rsi_normalized...")
if 'rsi_normalized' in ml_v2_df.columns:
    ml_v2_df = ml_v2_df.drop(columns=['rsi_normalized'])
    print("  rsi_normalized excluded")

numeric_features = [
    'ema_cross_diff_pct', 'atr_pct',
    'price_to_fast_pct', 'price_to_slow_pct',
    'trend_direction', 'trend_strength'
]

print(f"\nNumeric features: {numeric_features}")

for f in numeric_features:
    if f not in ml_v2_df.columns:
        print(f"  WARNING: {f} not found")
    else:
        missing = ml_v2_df[f].isna().sum()
        if missing > 0:
            print(f"  {f}: {missing} missing values, filling with 0")
            ml_v2_df[f] = ml_v2_df[f].fillna(0)

categorical_features = ['regime', 'volatility_level', 'strategy_signal']

print(f"\nCategorical features: {categorical_features}")

for cat in categorical_features:
    if cat not in ml_v2_df.columns:
        print(f"  WARNING: {cat} not found")
    else:
        missing = ml_v2_df[cat].isna().sum()
        if missing > 0:
            print(f"  {cat}: {missing} missing values, filling with 'unknown'")
            ml_v2_df[cat] = ml_v2_df[cat].fillna('unknown')

print("\nOne-hot encoding categorical features...")
for cat in categorical_features:
    if cat in ml_v2_df.columns:
        dummies = pd.get_dummies(ml_v2_df[cat], prefix=cat, dummy_na=False)
        ml_v2_df = pd.concat([ml_v2_df, dummies], axis=1)
        ml_v2_df = ml_v2_df.drop(columns=[cat])
        print(f"  {cat}: {len(dummies.columns)} one-hot columns created")

print("\n" + "=" * 80)
print("7. FINAL DATASET")
print("=" * 80)

feature_cols = [c for c in ml_v2_df.columns if c not in [
    'timestamp', 'symbol', 'target', 'r_multiple', 'pnl', 
    'exit_type', 'duration_seconds', 'join_time_diff',
    'decision_outcome', 'executed_action', 'was_executed',
    'reject_reason', 'reason',
    'decision_buy_possible', 'decision_sell_possible', 'decision_hold_possible'
]]

print(f"\nFinal feature list ({len(feature_cols)} features):")
for i, feat in enumerate(feature_cols, 1):
    print(f"  {i}. {feat}")

print(f"\nDataset shape: {ml_v2_df.shape}")
print(f"  Rows: {len(ml_v2_df):,}")
print(f"  Columns: {len(ml_v2_df.columns):,}")

print("\nSaving ml_v2_dataset.csv...")
output_cols = feature_cols + ['target', 'r_multiple', 'pnl', 'timestamp', 'symbol', 'exit_type']
output_cols = [c for c in output_cols if c in ml_v2_df.columns]

ml_v2_df[output_cols].to_csv('ml_v2_dataset.csv', index=False)
print(f"  Saved: ml_v2_dataset.csv")
print(f"  Columns saved: {len(output_cols)}")

print("\n" + "=" * 80)
print("8. SUMMARY")
print("=" * 80)

print(f"\nRows processed:")
print(f"  Initial decisions: {initial_decisions:,}")
print(f"  Filtered (BUY/SELL + executed): {len(decisions):,}")
print(f"  Successfully joined: {len(ml_v2_df):,}")
print(f"  Final dataset size: {len(ml_v2_df):,}")

print(f"\nTarget distribution:")
print(f"  R > 0 (winning): {target_counts.get(1, 0):,} ({target_counts.get(1, 0)/len(ml_v2_df)*100:.2f}%)")
print(f"  R <= 0 (losing): {target_counts.get(0, 0):,} ({target_counts.get(0, 0)/len(ml_v2_df)*100:.2f}%)")

print(f"\nFeatures:")
print(f"  Numeric: {len([f for f in feature_cols if ml_v2_df[f].dtype in [np.float64, np.int64]])}")
print(f"  Categorical (one-hot): {len([f for f in feature_cols if f.startswith('regime_') or f.startswith('volatility_') or f.startswith('strategy_')])}")

print("\n" + "=" * 80)
print("DATASET READY FOR ML v2 TRAINING")
print("=" * 80)
print(f"\nFile: ml_v2_dataset.csv")
print(f"Rows: {len(ml_v2_df):,}")
print(f"Features: {len(feature_cols)}")
print(f"Target: r_multiple > 0")
print("\n" + "=" * 80)
