"""
Constantes y validaciones para decisiones de trading.
Garantiza consistencia en decision_outcome y executed_action en todo el sistema.
"""

from enum import Enum
from typing import Set, Optional


class DecisionOutcome(Enum):
    """Valores permitidos para decision_outcome - ÚNICA FUENTE DE VERDAD"""
    NO_SIGNAL = "no_signal"
    EXECUTED = "executed"
    REJECTED_BY_RISK = "rejected_by_risk"
    REJECTED_BY_LIMITS = "rejected_by_limits"
    REJECTED_BY_FILTERS = "rejected_by_filters"
    REJECTED_BY_EXECUTION = "rejected_by_execution"


class ExecutedAction(Enum):
    """Valores permitidos para executed_action"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# Sets para validación rápida
VALID_DECISION_OUTCOMES: Set[str] = {e.value for e in DecisionOutcome}
VALID_EXECUTED_ACTIONS: Set[str] = {e.value for e in ExecutedAction}


def validate_decision_outcome(value: str) -> bool:
    """Valida que decision_outcome sea uno de los valores permitidos"""
    return value in VALID_DECISION_OUTCOMES


def validate_executed_action(value: str) -> bool:
    """Valida que executed_action sea uno de los valores permitidos"""
    return value in VALID_EXECUTED_ACTIONS


def validate_decision_consistency(
    executed_action: str,
    decision_outcome: str,
    strategy_signal: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Valida consistencia entre executed_action y decision_outcome.

    Reglas:
    - HOLD nunca con decision_outcome == "executed"
    - executed_action != HOLD => decision_outcome == "executed"
    - strategy_signal == None => executed_action == "HOLD" y decision_outcome == "no_signal"

    Returns:
        (is_valid, error_message)
    """
    if not validate_executed_action(executed_action):
        return False, f"executed_action inválido: {executed_action}"

    if not validate_decision_outcome(decision_outcome):
        return False, f"decision_outcome inválido: {decision_outcome}"

    # Regla 1: HOLD nunca con executed
    if executed_action == ExecutedAction.HOLD.value and decision_outcome == DecisionOutcome.EXECUTED.value:
        return False, "HOLD no puede tener decision_outcome='executed'"

    # Regla 2: BUY/SELL siempre con executed
    if executed_action in [ExecutedAction.BUY.value, ExecutedAction.SELL.value]:
        if decision_outcome != DecisionOutcome.EXECUTED.value:
            return False, f"executed_action={executed_action} debe tener decision_outcome='executed', pero tiene '{decision_outcome}'"

    # Regla 3: Sin señal => HOLD + no_signal
    if strategy_signal is None or strategy_signal == "NONE":
        if executed_action != ExecutedAction.HOLD.value:
            return False, f"Sin señal debe tener executed_action='HOLD', pero tiene '{executed_action}'"
        if decision_outcome != DecisionOutcome.NO_SIGNAL.value:
            return False, f"Sin señal debe tener decision_outcome='no_signal', pero tiene '{decision_outcome}'"

    return True, None
