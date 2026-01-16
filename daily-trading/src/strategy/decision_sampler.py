

from datetime import datetime
from typing import Dict, Optional, Any, List
from dataclasses import dataclass

from config import Config
from src.utils.logging_setup import setup_logging


@dataclass
class DecisionSample:
    timestamp: datetime
    symbol: str
    features: Dict[str, float]
    decision_space: Dict[str, bool]
    strategy_signal: Optional[str]
    executed_action: Optional[str]
    reason: str
    market_context: Dict[str, Any]


class DecisionSampler:

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(
            __name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL
        )

    def create_decision_sample(
        self,
        market_data: Dict[str, Any],
        strategy,
        strategy_signal: Optional[Dict[str, Any]] = None,
        executed_action: Optional[str] = None,
        regime_info: Optional[Dict[str, Any]] = None
    ) -> DecisionSample:
        try:
            indicators = market_data.get("indicators", {})
            price = market_data.get("price", 0)
            symbol = market_data.get("symbol", "UNKNOWN")
            timestamp = market_data.get("timestamp", datetime.now())

            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(
                        timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()

            features = self._extract_relative_features(indicators, price)

            if hasattr(strategy, 'get_decision_space'):
                decision_space = strategy.get_decision_space(market_data)
            else:
                self.logger.warning(
                    "⚠️ Strategy no tiene get_decision_space(), usando fallback")
                decision_space = self._determine_decision_space_fallback(
                    indicators, price, strategy_signal
                )

            strategy_action = None
            if strategy_signal:
                strategy_action = strategy_signal.get("action")

            if executed_action is None:
                if strategy_action is None:
                    executed_action = "HOLD"
                else:
                    executed_action = "HOLD"

            reason = self._build_reason(
                strategy_signal, decision_space, executed_action
            )
            market_context = {
                "regime": regime_info.get("regime", "unknown") if regime_info else "unknown",
                "volatility": regime_info.get("metrics", {}).get("volatility_level", "medium") if regime_info else "medium",
                "volume": market_data.get("volume", 0),
                "price": price,
            }

            return DecisionSample(
                timestamp=timestamp,
                symbol=symbol,
                features=features,
                decision_space=decision_space,
                strategy_signal=strategy_action,
                executed_action=executed_action,
                reason=reason,
                market_context=market_context
            )

        except Exception as e:
            self.logger.exception(f"❌ Error creando DecisionSample: {e}")
            # Retornar sample básico en caso de error
            return DecisionSample(
                timestamp=datetime.now(),
                symbol=market_data.get("symbol", "UNKNOWN"),
                features={},
                decision_space={"buy": False, "sell": False, "hold": True},
                strategy_signal=None,
                executed_action="HOLD",
                reason=f"Error: {str(e)}",
                market_context={}
            )

    def _extract_relative_features(
        self,
        indicators: Dict[str, float],
        price: float
    ) -> Dict[str, float]:
        try:
            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            rsi = indicators.get("rsi", 50)
            atr = indicators.get("atr", 0)

            features = {}

            if slow_ma > 0:
                features["ema_diff_pct"] = (
                    (fast_ma - slow_ma) / slow_ma) * 100
            else:
                features["ema_diff_pct"] = 0.0

            features["rsi_normalized"] = (rsi - 50) / 50
            features["atr_pct"] = (atr / price * 100) if price > 0 else 0.0

            if fast_ma > 0:
                features["price_to_fast_pct"] = (
                    (price - fast_ma) / fast_ma) * 100
            else:
                features["price_to_fast_pct"] = 0.0

            if slow_ma > 0:
                features["price_to_slow_pct"] = (
                    (price - slow_ma) / slow_ma) * 100
            else:
                features["price_to_slow_pct"] = 0.0

            if fast_ma > slow_ma:
                features["trend_direction"] = 1.0
            elif fast_ma < slow_ma:
                features["trend_direction"] = -1.0
            else:
                features["trend_direction"] = 0.0

            features["trend_strength"] = abs(features["ema_diff_pct"]) / 100.0

            return features

        except Exception as e:
            self.logger.exception(
                f"❌ Error extrayendo features relativas: {e}")
            return {}

    def _determine_decision_space_fallback(
        self,
        indicators: Dict[str, float],
        price: float,
        strategy_signal: Optional[Dict[str, Any]]
    ) -> Dict[str, bool]:
        decision_space = {
            "buy": False,
            "sell": False,
            "hold": True  # HOLD siempre disponible
        }

        try:
            if strategy_signal:
                action = strategy_signal.get("action")
                if action == "BUY":
                    decision_space["buy"] = True
                elif action == "SELL":
                    decision_space["sell"] = True

            return decision_space

        except Exception as e:
            self.logger.exception(
                f"❌ Error en fallback de decision_space: {e}")
            return {"buy": False, "sell": False, "hold": True}

    def _build_reason(
        self,
        strategy_signal: Optional[Dict[str, Any]],
        decision_space: Dict[str, bool],
        executed_action: Optional[str]
    ) -> str:
        """Construye una razón legible para la decisión"""
        if executed_action == "HOLD":
            if strategy_signal is None:
                return "HOLD: No signal from strategy"
            else:
                return f"HOLD: Signal {strategy_signal.get('action')} rejected or not executed"
        elif executed_action in ["BUY", "SELL"]:
            if strategy_signal:
                return strategy_signal.get("reason", f"{executed_action} executed")
            else:
                return f"{executed_action} executed (no strategy signal)"
        else:
            return "Unknown action"

    def to_dict(self, sample: DecisionSample) -> Dict[str, Any]:
        """Convierte DecisionSample a dict para guardar en CSV"""
        return {
            "timestamp": sample.timestamp.isoformat() if isinstance(sample.timestamp, datetime) else str(sample.timestamp),
            "symbol": sample.symbol,
            # Features relativas
            "ema_diff_pct": sample.features.get("ema_diff_pct", 0),
            "rsi_normalized": sample.features.get("rsi_normalized", 0),
            "atr_pct": sample.features.get("atr_pct", 0),
            "price_to_fast_pct": sample.features.get("price_to_fast_pct", 0),
            "price_to_slow_pct": sample.features.get("price_to_slow_pct", 0),
            "trend_direction": sample.features.get("trend_direction", 0),
            "trend_strength": sample.features.get("trend_strength", 0),
            # Decision space
            "decision_buy_possible": sample.decision_space.get("buy", False),
            "decision_sell_possible": sample.decision_space.get("sell", False),
            "decision_hold_possible": sample.decision_space.get("hold", True),
            # Strategy signal
            "strategy_signal": sample.strategy_signal or "NONE",
            # Executed action
            "executed_action": sample.executed_action or "HOLD",
            # Context
            "regime": sample.market_context.get("regime", "unknown"),
            "volatility": sample.market_context.get("volatility", "medium"),
            "reason": sample.reason,
        }
