#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML v2 Baseline Training and Evaluation
Target: r_multiple > 0 (market-dependent)
Compares against ML v1 (EXECUTED target)
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, 
    f1_score, classification_report, confusion_matrix,
    roc_curve, precision_recall_curve
)
import warnings
warnings.filterwarnings('ignore')

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    print("LightGBM not available, using Logistic Regression")

print("=" * 80)
print("ML v2 BASELINE TRAINING & EVALUATION")
print("=" * 80)
print(f"Target: r_multiple > 0 (market-dependent)")
print(f"Timestamp: {datetime.now()}")
print("=" * 80)

print("\n" + "=" * 80)
print("1. LOADING ML v2 DATASET")
print("=" * 80)

try:
    df = pd.read_csv('ml_v2_dataset.csv')
    print(f"\nDataset loaded: {len(df):,} samples")
    print(f"Columns: {len(df.columns)}")
except Exception as e:
    print(f"\n❌ ERROR loading ml_v2_dataset.csv: {e}")
    exit(1)

if 'target' not in df.columns:
    print("\n❌ ERROR: 'target' column not found in dataset")
    exit(1)

print(f"\nTarget distribution:")
target_counts = df['target'].value_counts()
for val, count in target_counts.items():
    pct = count / len(df) * 100
    label = "R > 0 (winning)" if val == 1 else "R <= 0 (losing)"
    print(f"  {label}: {count:,} ({pct:.2f}%)")

print("\n" + "=" * 80)
print("2. FEATURE PREPARATION")
print("=" * 80)

exclude_cols = [
    'timestamp', 'symbol', 'target', 'r_multiple', 'pnl', 
    'exit_type', 'duration_seconds', 'join_time_diff', 'join_method',
    'decision_outcome', 'executed_action', 'was_executed',
    'reject_reason', 'reason',
    'decision_buy_possible', 'decision_sell_possible', 'decision_hold_possible'
]

feature_cols = [c for c in df.columns if c not in exclude_cols]
print(f"\nFeatures to use: {len(feature_cols)}")
print(f"Feature list:")
for i, feat in enumerate(feature_cols, 1):
    print(f"  {i}. {feat}")

X = df[feature_cols].copy()
y = df['target'].copy()

print(f"\nFeature matrix shape: {X.shape}")

missing = X.isna().sum()
if missing.sum() > 0:
    print(f"\nMissing values:")
    for col, count in missing[missing > 0].items():
        print(f"  {col}: {count}")
    X = X.fillna(0)
else:
    print("\n[OK] No missing values")

print("\n" + "=" * 80)
print("3. TIME-AWARE SPLIT")
print("=" * 80)

if 'timestamp' in df.columns:
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.sort_values('timestamp')
    split_idx = int(len(df) * 0.8)
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]
    
    print(f"\nTrain set: {len(X_train):,} samples")
    if 'timestamp' in df.columns:
        print(f"  Time range: {df.iloc[0]['timestamp']} to {df.iloc[split_idx-1]['timestamp']}")
    print(f"  Target distribution: {y_train.value_counts().to_dict()}")
    
    print(f"\nTest set: {len(X_test):,} samples")
    if 'timestamp' in df.columns:
        print(f"  Time range: {df.iloc[split_idx]['timestamp']} to {df.iloc[-1]['timestamp']}")
    print(f"  Target distribution: {y_test.value_counts().to_dict()}")
else:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrain set: {len(X_train):,} samples (random split)")
    print(f"Test set: {len(X_test):,} samples")

print("\n" + "=" * 80)
print("4. MODEL TRAINING")
print("=" * 80)

if HAS_LIGHTGBM:
    print("\nTraining LightGBM classifier...")
    model = lgb.LGBMClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42,
        verbose=-1,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)
    model_name = "LightGBM"
else:
    print("\nTraining Logistic Regression...")
    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)
    model_name = "Logistic Regression"

print(f"  Model: {model_name}")
print(f"  Training completed")

print("\n" + "=" * 80)
print("5. MODEL EVALUATION")
print("=" * 80)

y_train_pred = model.predict(X_train)
y_test_pred = model.predict(X_test)
y_train_proba = model.predict_proba(X_train)[:, 1]
y_test_proba = model.predict_proba(X_test)[:, 1]

print("\n--- Train Set Metrics ---")
train_auc = roc_auc_score(y_train, y_train_proba)
train_precision = precision_score(y_train, y_train_pred)
train_recall = recall_score(y_train, y_train_pred)
train_f1 = f1_score(y_train, y_train_pred)

print(f"  ROC-AUC: {train_auc:.4f}")
print(f"  Precision: {train_precision:.4f}")
print(f"  Recall: {train_recall:.4f}")
print(f"  F1-Score: {train_f1:.4f}")

print("\n--- Test Set Metrics ---")
test_auc = roc_auc_score(y_test, y_test_proba)
test_precision = precision_score(y_test, y_test_pred)
test_recall = recall_score(y_test, y_test_pred)
test_f1 = f1_score(y_test, y_test_pred)

print(f"  ROC-AUC: {test_auc:.4f}")
print(f"  Precision: {test_precision:.4f}")
print(f"  Recall: {test_recall:.4f}")
print(f"  F1-Score: {test_f1:.4f}")

print("\n--- Overfitting Check ---")
auc_diff = train_auc - test_auc
print(f"  Train AUC - Test AUC: {auc_diff:.4f}")
if auc_diff > 0.1:
    print(f"  [WARNING] Potential overfitting (AUC gap > 0.1)")
elif auc_diff > 0.05:
    print(f"  [CAUTION] Moderate overfitting (AUC gap > 0.05)")
else:
    print(f"  [OK] No significant overfitting detected")

print("\n" + "=" * 80)
print("6. PRECISION@TopK & RECALL@TopK EVALUATION")
print("=" * 80)

def precision_at_topk(y_true, y_proba, k_percent=20):
    """Calculate precision at top K% of predictions"""
    k = int(len(y_true) * k_percent / 100)
    top_k_indices = np.argsort(y_proba)[-k:]
    top_k_true = y_true.iloc[top_k_indices] if hasattr(y_true, 'iloc') else y_true[top_k_indices]
    return precision_score([1] * len(top_k_true), top_k_true) if len(top_k_true) > 0 else 0.0

def recall_at_topk(y_true, y_proba, k_percent=20):
    """Calculate recall at top K% of predictions"""
    k = int(len(y_true) * k_percent / 100)
    top_k_indices = np.argsort(y_proba)[-k:]
    top_k_true = y_true.iloc[top_k_indices] if hasattr(y_true, 'iloc') else y_true[top_k_indices]
    total_positive = y_true.sum()
    return (top_k_true.sum() / total_positive) if total_positive > 0 else 0.0

print("\n--- Test Set: Precision@TopK & Recall@TopK ---")
for k in [10, 20, 30]:
    prec_k = precision_at_topk(y_test, y_test_proba, k)
    rec_k = recall_at_topk(y_test, y_test_proba, k)
    print(f"  Top {k}%:")
    print(f"    Precision@{k}%: {prec_k:.4f}")
    print(f"    Recall@{k}%: {rec_k:.4f}")

prec_top20 = precision_at_topk(y_test, y_test_proba, 20)
rec_top20 = recall_at_topk(y_test, y_test_proba, 20)

print("\n" + "=" * 80)
print("7. FEATURE IMPORTANCE")
print("=" * 80)

if HAS_LIGHTGBM:
    importances = model.feature_importances_
else:
    importances = np.abs(model.coef_[0])

feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': importances
}).sort_values('importance', ascending=False)

print("\nTop 10 most important features:")
for idx, row in feature_importance.head(10).iterrows():
    print(f"  {row['feature']}: {row['importance']:.6f}")

print("\n" + "=" * 80)
print("8. SUCCESS CRITERIA EVALUATION")
print("=" * 80)

print("\nML v2 Success Criteria (from design):")
print("  Minimum Viable:")
print("    - ROC-AUC > 0.55")
print("    - Precision@Top20% > 0.60")
print("    - Recall@Top20% > 0.40")

criteria_met = {
    'auc': test_auc > 0.55,
    'prec_top20': prec_top20 > 0.60,
    'rec_top20': rec_top20 > 0.40
}

print(f"\nResults:")
print(f"  ROC-AUC: {test_auc:.4f} {'[PASS]' if criteria_met['auc'] else '[FAIL]'} (threshold: 0.55)")
print(f"  Precision@Top20%: {prec_top20:.4f} {'[PASS]' if criteria_met['prec_top20'] else '[FAIL]'} (threshold: 0.60)")
print(f"  Recall@Top20%: {rec_top20:.4f} {'[PASS]' if criteria_met['rec_top20'] else '[FAIL]'} (threshold: 0.40)")

all_met = all(criteria_met.values())
print(f"\nMinimum Viable Criteria: {'[MET]' if all_met else '[NOT MET]'}")

print("\n" + "=" * 80)
print("9. COMPARISON WITH ML v1 (EXECUTED target)")
print("=" * 80)

print("\nML v1 (EXECUTED target) - Expected characteristics:")
print("  - Target: decision_outcome == 'executed'")
print("  - Issue: System-dependent, not market-dependent")
print("  - Expected AUC: ~0.50-0.55 (near random)")

print("\nML v2 (r_multiple > 0 target) - Current results:")
print(f"  - Target: r_multiple > 0 (market-dependent)")
print(f"  - Test ROC-AUC: {test_auc:.4f}")
print(f"  - Test Precision: {test_precision:.4f}")
print(f"  - Test Recall: {test_recall:.4f}")
print(f"  - Precision@Top20%: {prec_top20:.4f}")
print(f"  - Recall@Top20%: {rec_top20:.4f}")

improvement = test_auc - 0.50
print(f"\nImprovement over random (AUC 0.50): {improvement:+.4f}")

if test_auc > 0.55:
    print("  [YES] ML v2 shows predictive value above random")
else:
    print("  [NO] ML v2 does not show significant predictive value")

print("\n" + "=" * 80)
print("10. FINAL VERDICT")
print("=" * 80)

if test_auc > 0.60 and prec_top20 > 0.65 and rec_top20 > 0.45:
    verdict = "EXCELLENT"
    verdict_msg = "ML v2 shows strong predictive value. Ready for production use."
elif test_auc > 0.55 and prec_top20 > 0.60 and rec_top20 > 0.40:
    verdict = "GOOD"
    verdict_msg = "ML v2 shows moderate predictive value. Suitable for filtering signals."
elif test_auc > 0.52:
    verdict = "WEAK"
    verdict_msg = "ML v2 shows minimal predictive value. May not be worth the complexity."
else:
    verdict = "NO_VALUE"
    verdict_msg = "ML v2 does not add predictive value. Consider alternative approaches."

print(f"\nVerdict: {verdict}")
print(f"Message: {verdict_msg}")

print(f"\nKey Metrics Summary:")
print(f"  Test ROC-AUC: {test_auc:.4f}")
print(f"  Precision@Top20%: {prec_top20:.4f}")
print(f"  Recall@Top20%: {rec_top20:.4f}")
print(f"  Overfitting gap: {auc_diff:.4f}")

print("\n" + "=" * 80)
print("11. SAVING MODEL")
print("=" * 80)

try:
    import joblib
    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "ml_v2_model.pkl")
    joblib.dump(model, model_path)
    print(f"\nModel saved: {model_path}")
    print("Model ready for ML v2 filter integration")
except Exception as e:
    print(f"\n[WARNING] Could not save model: {e}")
    print("Model will need to be retrained for production use")

print("\n" + "=" * 80)
print("TRAINING COMPLETE")
print("=" * 80)
