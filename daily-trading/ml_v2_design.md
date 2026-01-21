# ML v2 Design: Market-Dependent Target

## 1. Why EXECUTED is a Bad ML Target

**Problem Analysis:**
- Test AUC: 0.4887 (worse than random 0.5)
- EXECUTED is a **system-level decision**, not a market outcome
- EXECUTED depends on:
  - Risk validation (system rules)
  - Daily limits (system constraints)
  - Position limits (system constraints)
  - NOT market conditions

**Root Cause:**
- Market features (EMA, ATR, RSI) cannot predict system-level blocking
- 51.52% REJECTED_BY_EXECUTION due to "Risk validation failed"
- This is a **risk management decision**, not a market signal

**Conclusion:**
EXECUTED is **not learnable from market features alone**. It requires system state (risk limits, position counts, daily PnL) which are not in the feature set.

---

## 2. New Target Definition

### Selected Target: **R > 0** (R-multiple > 0)

**Mathematical Definition:**
```
target = 1 if r_multiple > 0 else 0
where r_multiple = pnl / r_value
```

**Justification:**
1. **Market-dependent**: R-multiple reflects actual market outcome, not system rules
2. **Risk-normalized**: Accounts for position sizing and stop loss
3. **Actionable**: Model learns "will this trade be profitable relative to risk?"
4. **Robust**: Works across different position sizes and market conditions

**Alternative Targets Considered:**
- `pnl > 0`: Too sensitive to position size, not risk-normalized
- `take_profit_hit == True`: Too rare (binary, low positive rate), less informative

**Target Distribution (Expected):**
- Positive R: ~40-50% (typical win rate)
- Negative R: ~50-60% (typical loss rate)
- Balanced enough for binary classification

---

## 3. Dataset Join Strategy

### Source Tables:
1. **decisions.csv**: DecisionSamples with market features at signal time
2. **training_data.csv**: Completed trades with pnl, r_multiple, exit_type

### Join Logic:
```python
# Join on:
# - timestamp (entry_time from trade ≈ timestamp from decision)
# - symbol (must match)
# - executed_action == side (BUY/SELL must match)

# Match criteria:
# 1. decisions.executed_action == "BUY" or "SELL"
# 2. decisions.decision_outcome == "executed"
# 3. decisions.timestamp ≈ trades.timestamp (within 5 seconds tolerance)
# 4. decisions.symbol == trades.symbol
```

### Resulting Schema:
```
ML v2 Dataset:
- All features from decisions.csv (market context at entry)
- Target: r_multiple > 0 (from training_data.csv)
- Additional: r_multiple (continuous), pnl, exit_type, duration_seconds
```

---

## 4. Features to Keep

### Numeric Features (from decisions.csv):
- `ema_cross_diff_pct` ✅ (keep)
- `atr_pct` ✅ (keep)
- `price_to_fast_pct` ✅ (keep)
- `price_to_slow_pct` ✅ (keep)
- `trend_direction` ✅ (keep)
- `trend_strength` ✅ (keep)
- `rsi_normalized` ❌ (exclude - 99.9% zeros)

### Categorical Features:
- `regime` ✅ (keep - encode as one-hot)
- `volatility_level` ✅ (keep - encode as one-hot)
- `strategy_signal` ✅ (keep - BUY/SELL/NONE)

### Decision Space (optional):
- `decision_buy_possible` ✅ (keep)
- `decision_sell_possible` ✅ (keep)
- `decision_hold_possible` ✅ (keep)

### Features to Add from Trade Results:
- `r_value` (risk amount) - for context, not prediction
- `exit_type` (SL/TP/time) - for analysis only, not prediction

**Total Features: 6 numeric + 3 categorical = 9-12 features after encoding**

---

## 5. Success Criteria

### Minimum Viable Model:
- **ROC-AUC > 0.55**: Better than random, shows some signal
- **Precision@Top20% > 0.60**: Top 20% predictions have >60% win rate
- **Recall@Top20% > 0.40**: Captures at least 40% of winning trades in top predictions

### Good Model:
- **ROC-AUC > 0.65**: Clear predictive signal
- **Precision@Top20% > 0.70**: Strong win rate in top predictions
- **Recall@Top20% > 0.50**: Captures majority of winners

### Excellent Model:
- **ROC-AUC > 0.75**: Strong predictive power
- **Precision@Top20% > 0.80**: Very high win rate
- **Recall@Top20% > 0.60**: Captures most winners

### Overfitting Thresholds:
- Train-Test AUC gap < 0.10: Acceptable
- Train-Test AUC gap > 0.15: Overfitting detected

---

## 6. Dataset Schema for ML v2

### Input Features:
```python
{
    # Market features (at entry time)
    'ema_cross_diff_pct': float,
    'atr_pct': float,
    'price_to_fast_pct': float,
    'price_to_slow_pct': float,
    'trend_direction': float,  # -1, 0, 1
    'trend_strength': float,
    
    # Context features
    'regime': str,  # 'trending', 'ranging', 'unknown'
    'volatility_level': str,  # 'low', 'normal', 'high'
    'strategy_signal': str,  # 'BUY', 'SELL', 'NONE'
    
    # Decision space
    'decision_buy_possible': bool,
    'decision_sell_possible': bool,
    'decision_hold_possible': bool,
}
```

### Target:
```python
{
    'target': int,  # 1 if r_multiple > 0, else 0
    'r_multiple': float,  # continuous (for regression option)
}
```

### Metadata (for analysis, not training):
```python
{
    'timestamp': datetime,
    'symbol': str,
    'pnl': float,
    'exit_type': str,  # 'SL', 'TP', 'time', 'unknown'
    'duration_seconds': float,
}
```

---

## 7. Go / No-Go Decision

### ✅ GO for ML v2

**Reasons:**
1. **Target is learnable**: R > 0 is market-dependent, not system-dependent
2. **Data available**: Both decisions.csv and training_data.csv exist
3. **Join feasible**: Timestamp + symbol matching is straightforward
4. **Features sufficient**: 6 numeric + 3 categorical features is reasonable
5. **Success criteria clear**: AUC > 0.55 is achievable baseline

**Risks:**
- Join may miss some trades (timestamp mismatch)
- Need to handle trades without matching decisions
- May need time tolerance for matching (±5 seconds)

**Next Steps:**
1. Implement join script (decisions ↔ trades)
2. Create ML v2 dataset with target = (r_multiple > 0)
3. Train baseline model
4. Evaluate against success criteria

---

## Summary

**Target:** `r_multiple > 0` (binary classification)

**Dataset:** Join decisions.csv (features) + training_data.csv (target)

**Features:** 6 numeric + 3 categorical (exclude rsi_normalized)

**Success:** AUC > 0.55, Precision@Top20% > 0.60

**Verdict:** ✅ **GO** - ML v2 is viable with market-dependent target
