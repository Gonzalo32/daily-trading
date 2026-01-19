"""
Pipeline de decisiones centralizado.
Garantiza invariantes globales y normalización consistente de rechazos.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from src.utils.decision_constants import (
    DecisionOutcome,
    ExecutedAction,
    validate_decision_consistency
)


@dataclass
class TickDecision:
    """
    Estructura interna por tick que garantiza invariantes.
    ÚNICA fuente de verdad para executed_action y decision_outcome.
    """
    strategy_signal_action: Optional[str]  # "BUY", "SELL", o None
    executed_action: str  # "BUY", "SELL", "HOLD" (siempre presente)
    decision_outcome: str  # DecisionOutcome enum value (siempre presente)
    # String libre con detalles (None si no aplica)
    reject_reason: Optional[str]

    def __post_init__(self):
        """Valida invariantes al crear"""
        # Validar que executed_action y decision_outcome sean válidos
        if not validate_decision_consistency(
            self.executed_action,
            self.decision_outcome,
            self.strategy_signal_action
        )[0]:
            raise ValueError(
                f"TickDecision inválido: executed_action={self.executed_action}, "
                f"decision_outcome={self.decision_outcome}, "
                f"strategy_signal={self.strategy_signal_action}"
            )

    def to_dict(self) -> dict:
        """Convierte a dict para DecisionSample"""
        return {
            "executed_action": self.executed_action,
            "decision_outcome": self.decision_outcome,
            "reject_reason": self.reject_reason or "",
        }


def normalize_rejection(source: str, detail: str) -> Tuple[str, str]:
    """
    Normaliza un rechazo a (decision_outcome, reject_reason).

    Args:
        source: "ml", "risk", "limits", "execution"
        detail: String libre con detalles del rechazo

    Returns:
        (decision_outcome: DecisionOutcome enum value, reject_reason: str)

    Garantiza que decision_outcome SIEMPRE sea un valor del Enum.
    """
    source_lower = source.lower()

    if source_lower in ["ml", "ml_filter", "filter", "filters"]:
        return DecisionOutcome.REJECTED_BY_FILTERS.value, detail

    elif source_lower in ["risk", "risk_manager", "exposure", "position", "correlation"]:
        return DecisionOutcome.REJECTED_BY_RISK.value, detail

    elif source_lower in ["limits", "daily_limit", "daily_limits", "max_trades", "max_loss"]:
        return DecisionOutcome.REJECTED_BY_LIMITS.value, detail

    elif source_lower in ["execution", "executor", "order", "error"]:
        return DecisionOutcome.REJECTED_BY_EXECUTION.value, detail

    else:
        # Fallback seguro: rechazo por riesgo genérico
        return DecisionOutcome.REJECTED_BY_RISK.value, f"{source}: {detail}"


def create_tick_decision_no_signal() -> TickDecision:
    """
    Crea TickDecision para caso sin señal.
    Invariante A: strategy_signal is None => executed_action="HOLD" AND decision_outcome="no_signal"
    """
    return TickDecision(
        strategy_signal_action=None,
        executed_action=ExecutedAction.HOLD.value,
        decision_outcome=DecisionOutcome.NO_SIGNAL.value,
        reject_reason=None
    )


def create_tick_decision_executed(signal_action: str) -> TickDecision:
    """
    Crea TickDecision para caso ejecutado exitosamente.
    Invariante B: executed_action in {"BUY","SELL"} => decision_outcome MUST be "executed"

    Args:
        signal_action: "BUY" o "SELL"
    """
    if signal_action.upper() not in [ExecutedAction.BUY.value, ExecutedAction.SELL.value]:
        raise ValueError(
            f"signal_action debe ser BUY o SELL, recibido: {signal_action}")

    return TickDecision(
        strategy_signal_action=signal_action.upper(),
        executed_action=signal_action.upper(),
        decision_outcome=DecisionOutcome.EXECUTED.value,
        reject_reason=None
    )


def create_tick_decision_rejected(
    signal_action: str,
    rejection_source: str,
    rejection_detail: str
) -> TickDecision:
    """
    Crea TickDecision para caso rechazado.
    Invariante C: executed_action="HOLD" AND strategy_signal != None => 
                  decision_outcome MUST start with "rejected_*" y reject_reason NO vacío

    Args:
        signal_action: "BUY" o "SELL" (la señal original)
        rejection_source: "ml", "risk", "limits", "execution"
        rejection_detail: String con detalles del rechazo
    """
    if signal_action.upper() not in [ExecutedAction.BUY.value, ExecutedAction.SELL.value]:
        raise ValueError(
            f"signal_action debe ser BUY o SELL, recibido: {signal_action}")

    decision_outcome, reject_reason = normalize_rejection(
        rejection_source, rejection_detail)

    if not reject_reason:
        raise ValueError("reject_reason no puede estar vacío para rechazos")

    return TickDecision(
        strategy_signal_action=signal_action.upper(),
        executed_action=ExecutedAction.HOLD.value,
        decision_outcome=decision_outcome,
        reject_reason=reject_reason
    )


def run_decision_invariant_smoke_tests() -> bool:
    """
    Ejecuta tests rápidos de invariantes sin framework.
    Retorna True si todos pasan, False si alguno falla.
    """
    try:
        # Test 1: No signal
        decision1 = create_tick_decision_no_signal()
        assert decision1.executed_action == ExecutedAction.HOLD.value
        assert decision1.decision_outcome == DecisionOutcome.NO_SIGNAL.value
        assert decision1.strategy_signal_action is None
        assert validate_decision_consistency(
            decision1.executed_action,
            decision1.decision_outcome,
            decision1.strategy_signal_action
        )[0]

        # Test 2: Signal + ML reject
        decision2 = create_tick_decision_rejected(
            "BUY", "ml", "ML probability below threshold (0.52 < 0.55)"
        )
        assert decision2.executed_action == ExecutedAction.HOLD.value
        assert decision2.decision_outcome == DecisionOutcome.REJECTED_BY_FILTERS.value
        assert decision2.strategy_signal_action == "BUY"
        assert decision2.reject_reason is not None
        assert validate_decision_consistency(
            decision2.executed_action,
            decision2.decision_outcome,
            decision2.strategy_signal_action
        )[0]

        # Test 3: Signal + risk reject
        decision3 = create_tick_decision_rejected(
            "SELL", "risk", "Max positions reached: 2/2"
        )
        assert decision3.executed_action == ExecutedAction.HOLD.value
        assert decision3.decision_outcome == DecisionOutcome.REJECTED_BY_RISK.value
        assert decision3.reject_reason is not None

        # Test 4: Signal + execution error
        decision4 = create_tick_decision_rejected(
            "BUY", "execution", "Order execution failed: insufficient balance"
        )
        assert decision4.executed_action == ExecutedAction.HOLD.value
        assert decision4.decision_outcome == DecisionOutcome.REJECTED_BY_EXECUTION.value

        # Test 5: Signal + executed ok
        decision5 = create_tick_decision_executed("BUY")
        assert decision5.executed_action == ExecutedAction.BUY.value
        assert decision5.decision_outcome == DecisionOutcome.EXECUTED.value
        assert decision5.strategy_signal_action == "BUY"
        assert validate_decision_consistency(
            decision5.executed_action,
            decision5.decision_outcome,
            decision5.strategy_signal_action
        )[0]

        # Test 6: normalize_rejection con diferentes sources
        outcome1, reason1 = normalize_rejection("ml", "test")
        assert outcome1 == DecisionOutcome.REJECTED_BY_FILTERS.value

        outcome2, reason2 = normalize_rejection("limits", "test")
        assert outcome2 == DecisionOutcome.REJECTED_BY_LIMITS.value

        outcome3, reason3 = normalize_rejection("risk", "test")
        assert outcome3 == DecisionOutcome.REJECTED_BY_RISK.value

        outcome4, reason4 = normalize_rejection("execution", "test")
        assert outcome4 == DecisionOutcome.REJECTED_BY_EXECUTION.value

        return True

    except AssertionError as e:
        print(f"❌ Smoke test falló: {e}")
        return False
    except Exception as e:
        print(f"❌ Error en smoke tests: {e}")
        return False
