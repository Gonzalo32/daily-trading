#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baseline ML Model Training
Binary classification: EXECUTED vs NOT EXECUTED
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, 
    f1_score, classification_report, confusion_matrix
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
print("BASELINE ML MODEL TRAINING")
print("=" * 80)

df = pd.read_csv('src/ml/decisions.csv')
print(f"\nDataset loaded: {len(df):,} samples")

df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
df = df.sort_values('timestamp')

print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")

print("\n" + "=" * 80)
print("1. DATA PREPARATION")
print("=" * 80)

print("\nDropping rsi_normalized feature...")
if 'rsi_normalized' in df.columns:
    df = df.drop(columns=['rsi_normalized'])
    print("  rsi_normalized excluded")

numeric_features = [
    'ema_cross_diff_pct', 'atr_pct',
    'price_to_fast_pct', 'price_to_slow_pct',
    'trend_direction', 'trend_strength'
]

print(f"\nNumeric features to use: {numeric_features}")

for f in numeric_features:
    if f not in df.columns:
        print(f"  WARNING: {f} not found in dataset")
        numeric_features.remove(f)

X = df[numeric_features].copy()
print(f"\nFeature matrix shape: {X.shape}")

missing = X.isna().sum()
if missing.sum() > 0:
    print(f"\nMissing values:")
    for col, count in missing[missing > 0].items():
        print(f"  {col}: {count}")
    X = X.fillna(0)

y = (df['decision_outcome'] == 'executed').astype(int)
print(f"\nTarget distribution:")
print(f"  EXECUTED (1): {y.sum():,} ({y.sum()/len(y)*100:.2f}%)")
print(f"  NOT EXECUTED (0): {(1-y).sum():,} ({(1-y).sum()/len(y)*100:.2f}%)")

print("\n" + "=" * 80)
print("2. TIME-AWARE SPLIT")
print("=" * 80)

split_idx = int(len(df) * 0.8)
X_train = X.iloc[:split_idx]
X_test = X.iloc[split_idx:]
y_train = y.iloc[:split_idx]
y_test = y.iloc[split_idx:]

print(f"\nTrain set: {len(X_train):,} samples")
print(f"  Time range: {df.iloc[0]['timestamp']} to {df.iloc[split_idx-1]['timestamp']}")
print(f"  EXECUTED rate: {y_train.sum()/len(y_train)*100:.2f}%")

print(f"\nTest set: {len(X_test):,} samples")
print(f"  Time range: {df.iloc[split_idx]['timestamp']} to {df.iloc[-1]['timestamp']}")
print(f"  EXECUTED rate: {y_test.sum()/len(y_test)*100:.2f}%")

print("\n" + "=" * 80)
print("3. MODEL TRAINING")
print("=" * 80)

if HAS_LIGHTGBM:
    print("\nTraining LightGBM classifier...")
    model = lgb.LGBMClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42,
        verbose=-1
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
print("4. MODEL EVALUATION")
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
    print(f"  WARNING: Potential overfitting (AUC gap > 0.1)")
elif auc_diff > 0.05:
    print(f"  CAUTION: Moderate overfitting (AUC gap > 0.05)")
else:
    print(f"  OK: No significant overfitting detected")

print("\n--- Confusion Matrix (Test) ---")
cm = confusion_matrix(y_test, y_test_pred)
print(f"  True Negatives: {cm[0,0]}")
print(f"  False Positives: {cm[0,1]}")
print(f"  False Negatives: {cm[1,0]}")
print(f"  True Positives: {cm[1,1]}")

print("\n" + "=" * 80)
print("5. FEATURE IMPORTANCE")
print("=" * 80)

if HAS_LIGHTGBM:
    importances = model.feature_importances_
else:
    importances = np.abs(model.coef_[0])

feature_importance = pd.DataFrame({
    'feature': numeric_features,
    'importance': importances
}).sort_values('importance', ascending=False)

print("\nFeature importance ranking:")
for idx, row in feature_importance.iterrows():
    print(f"  {row['feature']}: {row['importance']:.6f}")

print("\n" + "=" * 80)
print("6. FINAL VERDICT")
print("=" * 80)

issues = []

if test_auc < 0.5:
    issues.append("Test AUC < 0.5 (worse than random)")
    verdict = "NO"
elif test_auc < 0.6:
    issues.append("Test AUC < 0.6 (weak predictive power)")
    verdict = "NO"
elif auc_diff > 0.15:
    issues.append(f"Severe overfitting (AUC gap: {auc_diff:.4f})")
    verdict = "NO"
elif test_precision < 0.3 or test_recall < 0.3:
    issues.append("Very low precision or recall (< 0.3)")
    verdict = "NO"
else:
    verdict = "YES"

if verdict == "YES":
    print(f"\nBaseline ML viable: YES")
    print(f"\nModel performance:")
    print(f"  Test ROC-AUC: {test_auc:.4f}")
    print(f"  Test Precision: {test_precision:.4f}")
    print(f"  Test Recall: {test_recall:.4f}")
    print(f"  Overfitting gap: {auc_diff:.4f}")
else:
    print(f"\nBaseline ML viable: NO")
    print(f"\nIssues:")
    for issue in issues:
        print(f"  - {issue}")
    print(f"\nCurrent metrics:")
    print(f"  Test ROC-AUC: {test_auc:.4f}")
    print(f"  Test Precision: {test_precision:.4f}")
    print(f"  Test Recall: {test_recall:.4f}")

print("\n" + "=" * 80)
