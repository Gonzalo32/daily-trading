

from datetime import datetime
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import uuid

from config import Config
from src.utils.logging_setup import setup_logging
from src.utils.decision_constants import (
    DecisionOutcome,
    ExecutedAction,
    validate_decision_outcome,
    validate_executed_action,
    validate_decision_consistency
)


@dataclass
class DecisionSample:
    timestamp: datetime
    symbol: str
    features: Dict[str, float]
    decision_space: Dict[str, bool]
    strategy_signal: Optional[str]
    executed_action: Optional[str]
    decision_outcome: Optional[str]
    reject_reason: Optional[str]
    reason: str
    market_context: Dict[str, Any]
    decision_id: Optional[str] = None


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
        regime_info: Optional[Dict[str, Any]] = None,
        decision_outcome: Optional[str] = None,
        reject_reason: Optional[str] = None
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

            # ⚠️ HARDENING A: Normalizar strategy_signal a {"BUY","SELL","NONE"}
            strategy_action = None
            if strategy_signal:
                strategy_action_raw = strategy_signal.get("action")
                if strategy_action_raw and isinstance(strategy_action_raw, str):
                    strategy_action_upper = strategy_action_raw.upper()
                    if strategy_action_upper in ["BUY", "SELL"]:
                        strategy_action = strategy_action_upper
                    else:
                        strategy_action = "NONE"
                else:
                    strategy_action = "NONE"
            else:
                strategy_action = "NONE"
            
            # Actualizar strategy_signal dict para consistencia
            if strategy_signal and strategy_action != "NONE":
                strategy_signal = {"action": strategy_action}
            else:
                strategy_signal = None

            reason = self._build_reason(
                strategy_signal,
                decision_space,
                executed_action,
                decision_outcome,
                reject_reason
            )
            # Unificar: usar volatility_level (string) en lugar de volatility
            volatility_level = "medium"
            if regime_info:
                metrics = regime_info.get("metrics", {})
                volatility_level = metrics.get("volatility_level", "medium")
                # Si viene como "volatility" en el nivel superior, mapearlo
                if "volatility" in regime_info:
                    vol_val = regime_info["volatility"]
                    if isinstance(vol_val, str):
                        volatility_level = vol_val
                    elif isinstance(vol_val, (int, float)):
                        # Mapear numérico a string
                        if vol_val > 0.7:
                            volatility_level = "high"
                        elif vol_val < 0.3:
                            volatility_level = "low"
                        else:
                            volatility_level = "normal"

            market_context = {
                "regime": regime_info.get("regime", "unknown") if regime_info else "unknown",
                "volatility_level": volatility_level,  # Unificado: siempre volatility_level
            }

            if decision_outcome and decision_outcome.startswith("rejected"):
                self.logger.info(
                    f"🧪 DecisionSample | outcome={decision_outcome} | reason={reject_reason or reason}"
                )
            else:
                self.logger.debug(
                    f"🧪 DecisionSample | outcome={decision_outcome} | action={executed_action}"
                )

            # ⚠️ HARDENING A: strategy_signal debe ser siempre {"BUY","SELL","NONE"}
            strategy_signal_final = strategy_action if strategy_action in ["BUY", "SELL"] else "NONE"
            
            decision_id = str(uuid.uuid4())
            
            return DecisionSample(
                timestamp=timestamp,
                symbol=symbol,
                features=features,
                decision_space=decision_space,
                strategy_signal=strategy_signal_final,  # ⚠️ HARDENING A: siempre normalizado
                executed_action=executed_action,
                decision_outcome=decision_outcome,
                reject_reason=reject_reason,
                reason=reason,
                market_context=market_context,
                decision_id=decision_id
            )

        except Exception as e:
            self.logger.exception(f"❌ Error creando DecisionSample: {e}")

            return DecisionSample(
                timestamp=datetime.now(),
                symbol=market_data.get("symbol", "UNKNOWN"),
                features={},
                decision_space={"buy": False, "sell": False, "hold": True},
                strategy_signal=None,
                executed_action=ExecutedAction.HOLD.value,
                decision_outcome=DecisionOutcome.REJECTED_BY_EXECUTION.value,
                reject_reason=f"Error creating DecisionSample: {str(e)}",
                reason=f"Error: {str(e)}",
                market_context={"regime": "unknown", "volatility_level": "medium"},
                decision_id=str(uuid.uuid4())
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
            "hold": True
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
        executed_action: Optional[str],
        decision_outcome: Optional[str],
        reject_reason: Optional[str]
    ) -> str:
        """
        Construye una razón legible para la decisión con trazabilidad completa.
        SOLO maneja valores del DecisionOutcome Enum (sin mapeo de valores antiguos).
        """
        strategy_action = strategy_signal.get(
            "action") if strategy_signal else None

        # Validar que decision_outcome sea válido (debe venir normalizado del pipeline)
        if decision_outcome and not validate_decision_outcome(decision_outcome):
            self.logger.warning(
                f"⚠️ decision_outcome inválido recibido: {decision_outcome}. "
                "Usando NO_SIGNAL como fallback seguro."
            )
            decision_outcome = DecisionOutcome.NO_SIGNAL.value

        if not decision_outcome:
            decision_outcome = DecisionOutcome.NO_SIGNAL.value

        # Validar executed_action
        if executed_action and not validate_executed_action(executed_action):
            self.logger.warning(
                f"⚠️ executed_action inválido recibido: {executed_action}. "
                "Usando HOLD como fallback seguro."
            )
            executed_action = ExecutedAction.HOLD.value

        if not executed_action:
            executed_action = ExecutedAction.HOLD.value

        # Construir razón según outcome (SOLO valores del Enum)
        if decision_outcome == DecisionOutcome.NO_SIGNAL.value:
            return "HOLD: No signal from strategy (market conditions not met)"

        elif decision_outcome == DecisionOutcome.EXECUTED.value:
            if executed_action in [ExecutedAction.BUY.value, ExecutedAction.SELL.value]:
                if strategy_signal:
                    base_reason = strategy_signal.get(
                        "reason", f"{executed_action} executed")
                    return f"{base_reason} | Outcome: EXECUTED"
                else:
                    return f"{executed_action} executed | Outcome: EXECUTED"
            else:
                # Inconsistencia detectada
                self.logger.error(
                    f"❌ INCONSISTENCIA: outcome=EXECUTED pero action={executed_action}"
                )
                return f"INCONSISTENT: outcome=executed but action={executed_action}"

        elif decision_outcome == DecisionOutcome.REJECTED_BY_FILTERS.value:
            if strategy_action:
                base = f"HOLD: Signal {strategy_action} rejected by ML Filters"
            else:
                base = "HOLD: Signal rejected by ML Filters"
            if reject_reason:
                return f"{base} - {reject_reason}"
            return base

        elif decision_outcome == DecisionOutcome.REJECTED_BY_RISK.value:
            if strategy_action:
                base = f"HOLD: Signal {strategy_action} rejected by Risk Manager"
            else:
                base = "HOLD: Signal rejected by Risk Manager"
            if reject_reason:
                return f"{base} - {reject_reason}"
            return base

        elif decision_outcome == DecisionOutcome.REJECTED_BY_LIMITS.value:
            if strategy_action:
                base = f"HOLD: Signal {strategy_action} rejected by Daily Limits"
            else:
                base = "HOLD: Signal rejected by Daily Limits"
            if reject_reason:
                return f"{base} - {reject_reason}"
            return base

        elif decision_outcome == DecisionOutcome.REJECTED_BY_EXECUTION.value:
            if strategy_action:
                base = f"HOLD: Signal {strategy_action} rejected by Execution Error"
            else:
                base = "HOLD: Signal rejected by Execution Error"
            if reject_reason:
                return f"{base} - {reject_reason}"
            return base

        else:
            # Fallback seguro (no debería llegar aquí)
            self.logger.error(
                f"❌ decision_outcome desconocido: {decision_outcome}. "
                "Usando formato genérico."
            )
            return f"Action: {executed_action} | Outcome: {decision_outcome}"

    def to_dict(self, sample: DecisionSample) -> Dict[str, Any]:
        """
        Convierte DecisionSample a dict para guardar en CSV.
        ÚNICA FUENTE DE VERDAD para el formato del CSV.
        """
        # Normalizar decision_outcome
        # ⚠️ NOTA: Este mapeo es SOLO para compatibilidad con datos antiguos.
        # En el pipeline normal, decision_outcome SIEMPRE debe venir del Enum.
        decision_outcome = sample.decision_outcome
        if decision_outcome and not validate_decision_outcome(decision_outcome):
            # Mapear valores antiguos (fallback de seguridad, no debería usarse en producción)
            self.logger.warning(
                f"⚠️ decision_outcome inválido recibido: {decision_outcome}. "
                "Mapeando a valor válido (esto no debería pasar en producción)."
            )
            outcome_map = {
                "accepted": DecisionOutcome.EXECUTED.value,
                "pending": DecisionOutcome.NO_SIGNAL.value,
                "rejected": DecisionOutcome.REJECTED_BY_RISK.value,
                "unknown": DecisionOutcome.NO_SIGNAL.value,
            }
            decision_outcome = outcome_map.get(
                decision_outcome, DecisionOutcome.NO_SIGNAL.value)
        elif not decision_outcome:
            decision_outcome = DecisionOutcome.NO_SIGNAL.value

        # Normalizar executed_action
        executed_action = sample.executed_action
        if executed_action and not validate_executed_action(executed_action):
            executed_action = ExecutedAction.HOLD.value
        elif not executed_action:
            executed_action = ExecutedAction.HOLD.value

        # ⚠️ HARDENING D: Validar consistencia usando decision_constants.py como fuente única
        is_valid, error = validate_decision_consistency(
            executed_action,
            decision_outcome,
            sample.strategy_signal
        )
        if not is_valid:
            self.logger.warning(
                f"⚠️ Inconsistencia en DecisionSample: {error}. Corrigiendo automáticamente...")
            # Corregir automáticamente según reglas de decision_constants.py
            if executed_action == ExecutedAction.HOLD.value and decision_outcome == DecisionOutcome.EXECUTED.value:
                # HOLD nunca con EXECUTED
                decision_outcome = DecisionOutcome.NO_SIGNAL.value
            elif executed_action in [ExecutedAction.BUY.value, ExecutedAction.SELL.value]:
                # BUY/SELL siempre con EXECUTED
                if decision_outcome != DecisionOutcome.EXECUTED.value:
                    decision_outcome = DecisionOutcome.EXECUTED.value
            # Validar strategy_signal NONE con HOLD + NO_SIGNAL
            if (sample.strategy_signal is None or sample.strategy_signal == "NONE"):
                if executed_action != ExecutedAction.HOLD.value:
                    executed_action = ExecutedAction.HOLD.value
                if decision_outcome != DecisionOutcome.NO_SIGNAL.value:
                    decision_outcome = DecisionOutcome.NO_SIGNAL.value

        # was_executed: True solo si decision_outcome == "executed"
        was_executed = (decision_outcome == DecisionOutcome.EXECUTED.value)

        # Validar strategy_signal ∈ {"BUY","SELL","NONE"}
        strategy_signal_normalized = sample.strategy_signal
        if strategy_signal_normalized and strategy_signal_normalized.upper() in ["BUY", "SELL"]:
            strategy_signal_normalized = strategy_signal_normalized.upper()
        elif strategy_signal_normalized is None or strategy_signal_normalized == "NONE":
            strategy_signal_normalized = "NONE"
        else:
            self.logger.warning(
                f"⚠️ strategy_signal inválido: {strategy_signal_normalized}. Usando NONE.")
            strategy_signal_normalized = "NONE"

        return {
            "timestamp": sample.timestamp.isoformat() if isinstance(sample.timestamp, datetime) else str(sample.timestamp),
            "symbol": sample.symbol,
            "decision_id": sample.decision_id or "",

            # Features (usar ema_cross_diff_pct para alinear con CSV)
            "ema_cross_diff_pct": sample.features.get("ema_diff_pct", 0),
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

            # Signal y acción (validado)
            "strategy_signal": strategy_signal_normalized,
            "executed_action": executed_action,
            "was_executed": was_executed,

            # Contexto de mercado (unificado: volatility_level)
            "regime": sample.market_context.get("regime", "unknown"),
            "volatility_level": sample.market_context.get("volatility_level", "medium"),

            # Outcome y razones
            "decision_outcome": decision_outcome,
            "reject_reason": sample.reject_reason or "",
            "reason": sample.reason,
        }
