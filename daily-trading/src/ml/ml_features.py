from typing import Any, Dict, Optional


def _normalize_volatility_level(regime_info: Optional[Dict[str, Any]]) -> str:
    if not regime_info:
        return "normal"

    metrics = regime_info.get("metrics", {})
    if isinstance(metrics, dict) and "volatility_level" in metrics:
        return str(metrics.get("volatility_level", "normal"))

    raw = regime_info.get("volatility", "normal")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, (int, float)):
        if raw > 0.7:
            return "high"
        if raw < 0.3:
            return "low"
        return "normal"
    return "normal"


def build_entry_features(
    signal: Optional[Dict[str, Any]],
    market_data: Dict[str, Any],
    regime_info: Optional[Dict[str, Any]] = None,
    bot_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    price = 0.0
    if signal and signal.get("price") is not None:
        price = float(signal.get("price", 0) or 0)
    else:
        price = float(market_data.get("price", 0) or 0)

    indicators = market_data.get("indicators", {}) or {}
    fast_ma = float(indicators.get("fast_ma", price) or price)
    slow_ma = float(indicators.get("slow_ma", price) or price)
    rsi = float(indicators.get("rsi", 50) or 50)
    atr = float(indicators.get("atr", 0) or 0)

    ema_cross_diff_pct = ((fast_ma - slow_ma) / slow_ma * 100) if slow_ma > 0 else 0.0
    atr_pct = (atr / price * 100) if price > 0 else 0.0
    rsi_normalized = (rsi - 50) / 50
    price_to_fast_pct = ((price - fast_ma) / fast_ma * 100) if fast_ma > 0 else 0.0
    price_to_slow_pct = ((price - slow_ma) / slow_ma * 100) if slow_ma > 0 else 0.0

    if fast_ma > slow_ma:
        trend_direction = 1.0
    elif fast_ma < slow_ma:
        trend_direction = -1.0
    else:
        trend_direction = 0.0

    trend_strength = abs(ema_cross_diff_pct) / 100.0

    risk_multiplier = None
    if signal:
        risk_multiplier = signal.get("risk_multiplier", 1.0)

    features = {
        "atr_value": atr,
        "rsi_normalized": rsi_normalized,
        "ema_cross_diff_pct": ema_cross_diff_pct,
        "atr_pct": atr_pct,
        "price_to_fast_pct": price_to_fast_pct,
        "price_to_slow_pct": price_to_slow_pct,
        "trend_direction": trend_direction,
        "trend_strength": trend_strength,
        "risk_multiplier": risk_multiplier,
        "regime": (regime_info.get("regime", "unknown") if regime_info else "unknown"),
        "volatility_level": _normalize_volatility_level(regime_info),
    }

    if bot_state:
        features["daily_pnl_normalized"] = bot_state.get("daily_pnl_normalized")
        features["daily_trades_normalized"] = bot_state.get("daily_trades_normalized")
        features["consecutive_signals"] = bot_state.get("consecutive_signals")

    return features
