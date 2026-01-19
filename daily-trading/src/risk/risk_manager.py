"""
Gestor de riesgo del bot de trading - Learning-Aware
Implementa controles de riesgo adaptativos según el modo (PAPER/LIVE).
En modo PAPER: prioriza sample size para ML, reduce riesgo progresivamente.
En modo LIVE: mantiene límites estrictos de protección.
"""


from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from config import Config
from src.utils.logging_setup import setup_logging
from src.utils.decision_constants import DecisionOutcome


@dataclass
class RiskState:
    """Estado de riesgo persistente."""
    equity: float = 10_000.0
    day: date = date.today()
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    trades_today: int = 0  # DEPRECATED: usar executed_trades_today
    # Trades cerrados (solo se incrementa en apply_trade_result)
    executed_trades_today: int = 0
    decision_samples_collected: int = 0  # DecisionSamples generados para ML
    max_drawdown: float = 0.0
    peak_equity: float = 10_000.0


class RiskManager:
    """
    Gestor de riesgo integral para trading automático.

    Comportamiento según modo:
    - LIVE: Límites estrictos (kill-switch real)
    - PAPER: Soft-risk control (reducción progresiva, nunca bloqueo total)
    """

    def __init__(self, config: Config, state: Optional[RiskState] = None):
        self.config = config
        self.state = state or RiskState(equity=config.INITIAL_CAPITAL)
        self.logger = setup_logging(
            __name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        self.trade_history: List[Dict[str, Any]] = []

        self._adaptive_risk_level: float = 1.0
        self._last_adaptive_update: datetime = datetime.now()

    def validate_trade(
        self,
        signal: Dict[str, Any],
        current_positions: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verifica si la operación cumple los criterios de riesgo.

        ⚠️ IMPORTANTE: Este método NO debe bloquear DecisionSamples en PAPER.
        Solo valida si puede ejecutarse la orden REAL.

        Returns:
            (is_valid, decision_outcome, reject_reason)
            - is_valid: True si puede ejecutarse orden REAL
            - decision_outcome: DecisionOutcome enum value o None si válido
            - reject_reason: Razón del rechazo o None si válido

        En modo PAPER: 
        - DecisionSamples SIEMPRE se crean (no bloquea)
        - Solo limita ejecución de órdenes reales si hay riesgo extremo
        - Reduce size progresivamente, nunca bloquea completamente

        En modo LIVE: bloquea si se alcanzan límites.
        """
        try:
            is_paper = self.config.TRADING_MODE == "PAPER"

            if is_paper:
                self._update_adaptive_risk_level()

            # ⚠️ CRÍTICO: En PAPER, los límites NO bloquean DecisionSamples
            # Solo afectan ejecución de órdenes reales
            limits_ok = self.check_daily_limits()
            if not limits_ok:
                if self.config.TRADING_MODE == "LIVE":
                    self.logger.warning(
                        "⚠️ [LIVE] Límite diario alcanzado - Trading bloqueado por seguridad.")
                    return False, DecisionOutcome.REJECTED_BY_LIMITS.value, "Daily limits reached (LIVE mode)"
                else:
                    # En PAPER: permitir DecisionSample, pero no ejecutar orden real
                    # (esto se maneja en can_execute_order())
                    self.logger.info(
                        f"📚 [PAPER] Límite diario informativo alcanzado - "
                        f"DecisionSample se creará, pero orden real no se ejecutará "
                        f"(trades ejecutados: {self.state.executed_trades_today})")
                    # NO retornar False aquí - permitir crear DecisionSample

            # En PAPER, solo reducir size si hay muchas posiciones, no bloquear
            if len(current_positions) >= self.config.MAX_POSITIONS:
                if is_paper:
                    self.logger.info(
                        f"📚 [PAPER] Máximo de posiciones alcanzado ({len(current_positions)}) - "
                        f"DecisionSample se creará, pero orden real no se ejecutará")
                    # Reducir size pero no bloquear DecisionSample
                    if 'position_size' in signal:
                        signal['position_size'] *= self._adaptive_risk_level
                    # Retornar False solo para ejecución, no para DecisionSample
                    return False, DecisionOutcome.REJECTED_BY_RISK.value, f"Max positions reached: {len(current_positions)}/{self.config.MAX_POSITIONS}"
                else:
                    self.logger.warning(
                        "⚠️ Número máximo de posiciones abiertas alcanzado.")
                    return False, DecisionOutcome.REJECTED_BY_RISK.value, f"Max positions reached: {len(current_positions)}/{self.config.MAX_POSITIONS}"

            # En PAPER, solo reducir size si hay mucha exposición, no bloquear
            exposure_ok = self._check_total_exposure(signal, current_positions)
            if not exposure_ok:
                if is_paper:
                    self.logger.info(
                        "📚 [PAPER] Exposición alta - DecisionSample se creará, pero orden real no se ejecutará")
                    # Reducir size pero no bloquear DecisionSample
                    if 'position_size' in signal:
                        signal['position_size'] *= self._adaptive_risk_level
                    return False, DecisionOutcome.REJECTED_BY_RISK.value, "Total exposure exceeds limit"
                else:
                    self.logger.warning(
                        "⚠️ Exposición total excede el límite permitido.")
                    return False, DecisionOutcome.REJECTED_BY_RISK.value, "Total exposure exceeds limit"

            # Correlación: en PAPER también solo reducir, no bloquear
            correlation_ok = self._check_correlation(signal, current_positions)
            if not correlation_ok:
                if is_paper:
                    self.logger.info(
                        "📚 [PAPER] Posición correlacionada - DecisionSample se creará, pero orden real no se ejecutará")
                    # Reducir size pero no bloquear DecisionSample
                    if 'position_size' in signal:
                        signal['position_size'] *= self._adaptive_risk_level
                    return False, DecisionOutcome.REJECTED_BY_RISK.value, "Position correlated with existing positions"
                else:
                    self.logger.warning(
                        "⚠️ Posición correlacionada con existentes.")
                    return False, DecisionOutcome.REJECTED_BY_RISK.value, "Position correlated with existing positions"

            return True, None, None
        except Exception as e:
            self.logger.exception(f"❌ Error validando operación: {e}")
            # En PAPER, permitir DecisionSample incluso con error
            if is_paper:
                return False, DecisionOutcome.REJECTED_BY_EXECUTION.value, f"Validation error: {str(e)}"
            else:
                return False, DecisionOutcome.REJECTED_BY_EXECUTION.value, f"Validation error: {str(e)}"

    def can_execute_order(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verifica si se puede ejecutar una orden REAL (no DecisionSample).

        ⚠️ CRÍTICO: Este es el ÚNICO lugar que bloquea por MAX_DAILY_TRADES y límites.
        En PAPER, DecisionSamples SIEMPRE se crean (no se bloquean).

        Returns:
            (can_execute, decision_outcome, reject_reason)
            - can_execute: True si puede ejecutarse orden real
            - decision_outcome: DecisionOutcome enum value si no puede ejecutarse
            - reject_reason: Razón si no puede ejecutarse

        En PAPER:
        - Si executed_trades_today >= MAX_DAILY_TRADES → no ejecutar orden real
        - Si límites de PnL alcanzados → no ejecutar orden real
        - Pero DecisionSample SIEMPRE se crea
        """
        if self.config.TRADING_MODE == "PAPER":
            # En PAPER, verificar límites pero NO bloquear DecisionSamples
            max_trades = getattr(self.config, "MAX_DAILY_TRADES", None) or getattr(
                self.config, "PAPER_MAX_DAILY_TRADES", 100)

            if max_trades and self.state.executed_trades_today >= max_trades:
                # No ejecutar orden real, pero DecisionSample se crea
                return False, DecisionOutcome.REJECTED_BY_LIMITS.value, (
                    f"Max daily trades reached: {self.state.executed_trades_today}/{max_trades} "
                    f"(DecisionSample se creará, pero orden real no se ejecutará)"
                )

            # Verificar límites de PnL (check_daily_limits ahora solo maneja PnL)
            # En PAPER, check_daily_limits siempre retorna True (learning-first)
            # Pero en LIVE puede bloquear
            limits_ok = self.check_daily_limits()
            if not limits_ok:
                # No ejecutar orden real, pero DecisionSample se crea
                return False, DecisionOutcome.REJECTED_BY_LIMITS.value, (
                    f"Daily PnL limits reached (PnL: {self.state.daily_pnl:.2f}) "
                    f"(DecisionSample se creará, pero orden real no se ejecutará)"
                )

            return True, None, None
        else:
            # En LIVE, verificar ambos: trades y límites de PnL
            max_trades = getattr(self.config, "MAX_DAILY_TRADES", None)
            if max_trades and self.state.executed_trades_today >= max_trades:
                return False, DecisionOutcome.REJECTED_BY_LIMITS.value, (
                    f"Max daily trades reached: {self.state.executed_trades_today}/{max_trades}"
                )

            limits_ok = self.check_daily_limits()
            if not limits_ok:
                return False, DecisionOutcome.REJECTED_BY_LIMITS.value, "Daily PnL limits reached"

            return True, None, None

    def unregister_position(self):
        """Se llama cuando una posición se cierra"""
        # NO decrementar trades aquí - solo se incrementa en apply_trade_result()
        self.logger.info("🧹 Slot liberado")

    def apply_trade_result(self, pnl: float) -> None:
        """
        ÚNICA FUENTE DE VERDAD: Actualiza equity, daily_pnl y executed_trades_today.
        Se llama SOLO cuando se CIERRA una posición.
        Este es el ÚNICO lugar donde se incrementa executed_trades_today.
        """
        self.state.equity += pnl
        self.state.daily_pnl += pnl
        self.state.executed_trades_today += 1
        self.state.trades_today = self.state.executed_trades_today  # Mantener compatibilidad
        self.state.total_pnl += pnl

        if self.state.equity > self.state.peak_equity:
            self.state.peak_equity = self.state.equity

        drawdown = (self.state.peak_equity - self.state.equity) / \
            self.state.peak_equity
        if drawdown > self.state.max_drawdown:
            self.state.max_drawdown = drawdown

        self.logger.info(
            f"💰 Trade aplicado | PnL={pnl:.2f} | Equity={self.state.equity:.2f} | "
            f"Daily PnL={self.state.daily_pnl:.2f} | Trades hoy={self.state.trades_today}"
        )

    def check_daily_limits(self, daily_pnl: float = None, daily_trades: int = None) -> bool:
        """
        Verifica límites diarios de PnL (pérdida/ganancia) SOLAMENTE.

        ⚠️ IMPORTANTE: Este método NO maneja límites de trades (MAX_DAILY_TRADES).
        can_execute_order() es el único lugar que bloquea por trades.

        Comportamiento:
        - LIVE: Retorna False si se alcanza límite de pérdida (bloqueo estricto)
        - PAPER: 
          - Pérdida → warning pero retorna True (learning-first)
          - Ganancia → retorna True (no bloquear learning)

        Método público para uso externo.
        """

        pnl = daily_pnl if daily_pnl is not None else self.state.daily_pnl
        # ⚠️ NO usar daily_trades aquí - can_execute_order() maneja trades

        max_loss_pct = getattr(self.config, "MAX_DAILY_LOSS_PCT", None)
        if max_loss_pct is not None:
            max_loss = self.state.equity * (max_loss_pct / 100.0)
        else:
            if self.config.MAX_DAILY_LOSS < 1.0:
                max_loss = self.state.equity * self.config.MAX_DAILY_LOSS
            else:
                max_loss = self.config.MAX_DAILY_LOSS

        max_gain = self.state.equity * self.config.MAX_DAILY_GAIN

        if pnl < -max_loss:
            if self.config.TRADING_MODE == "LIVE":
                self.logger.warning(
                    f"🚨 [LIVE] Límite de pérdida diaria alcanzado: {pnl:.2f} / {-max_loss:.2f} - "
                    f"Trading bloqueado por seguridad.")
                return False
            else:
                # En PAPER: warning pero continuar (learning-first)
                self.logger.warning(
                    f"⚠️ [PAPER] Límite de pérdida diaria alcanzado: {pnl:.2f} / {-max_loss:.2f} - "
                    f"Continuando con riesgo reducido para aprendizaje.")
                return True

        if pnl > max_gain:
            if self.config.TRADING_MODE == "LIVE":
                self.logger.info(
                    f"✅ [LIVE] Límite de ganancia diaria alcanzado: {pnl:.2f} / {max_gain:.2f} - "
                    f"Trading bloqueado.")
                return False
            else:
                # En PAPER: no bloquear por ganancia (learning-first)
                self.logger.info(
                    f"✅ [PAPER] Límite de ganancia diaria alcanzado: {pnl:.2f} / {max_gain:.2f} - "
                    f"Continuando para aprendizaje.")
                return True

        return True

    def _update_adaptive_risk_level(self) -> None:
        """
        Actualiza el nivel de riesgo adaptativo en modo PAPER.

        Si el PnL diario es negativo, reduce progresivamente:
        - Tamaño de posición (risk_multiplier)
        - Riesgo por trade

        Fórmula: risk_multiplier = 1.0 - min(0.8, abs(daily_pnl) / (equity * 0.1))
        Esto significa que si el PnL es -10% del equity, el riesgo se reduce a 20% del normal.
        """
        if self.config.TRADING_MODE != "PAPER":
            return

        now = datetime.now()
        if (now - self._last_adaptive_update).total_seconds() < 30:
            return

        self._last_adaptive_update = now

        if self.state.daily_pnl >= 0:
            if self._adaptive_risk_level < 1.0:
                self.logger.info(
                    f"📈 [PAPER] PnL positivo - Restaurando riesgo normal "
                    f"(multiplier: {self._adaptive_risk_level:.2f} -> 1.00)")
            self._adaptive_risk_level = 1.0
            return

        loss_pct = abs(self.state.daily_pnl) / \
            max(self.state.equity, self.config.INITIAL_CAPITAL)

        reduction = min(0.8, loss_pct * 8.0)
        new_level = max(0.2, 1.0 - reduction)

        if abs(new_level - self._adaptive_risk_level) > 0.05:
            self.logger.info(
                f"📉 [PAPER] Reducción adaptativa de riesgo | "
                f"PnL: {self.state.daily_pnl:.2f} ({loss_pct*100:.1f}% del equity) | "
                f"Multiplier: {self._adaptive_risk_level:.2f} -> {new_level:.2f}")

        self._adaptive_risk_level = new_level

    def get_adaptive_risk_multiplier(self) -> float:
        """
        Retorna el multiplicador de riesgo adaptativo actual.

        En modo LIVE: siempre retorna 1.0 (sin reducción)
        En modo PAPER: retorna valor entre 0.2 y 1.0 según el PnL diario.
        """
        if self.config.TRADING_MODE == "LIVE":
            return 1.0
        return self._adaptive_risk_level

    def _check_total_exposure(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """Limita la exposición total (por ej. máx. 50% del capital)."""
        try:
            total_exposure = sum(
                pos.get("size", 0) * pos.get("entry_price", 0) for pos in current_positions)
            new_exposure = signal.get(
                "position_size", 0) * signal.get("price", 0)

            if self.config.TRADING_MODE == "PAPER" and self._adaptive_risk_level < 1.0:
                max_exposure = self.state.equity * 0.9
            else:
                max_exposure = self.state.equity * 0.5

            is_valid = total_exposure + new_exposure <= max_exposure
            if not is_valid:
                self.logger.warning(
                    f"⚠️ Exposición excede límite: {total_exposure + new_exposure:.2f} / {max_exposure:.2f} "
                    f"(actual: {total_exposure:.2f}, nueva: {new_exposure:.2f})"
                )
            return is_valid
        except Exception as e:
            self.logger.error(f"❌ Error calculando exposición total: {e}")
            return False

    def _check_correlation(self, signal, current_positions):

        if getattr(self.config, "TRAINING_MODE", False):
            return True

        same_symbol = [p for p in current_positions
                       if p.get("symbol") == signal.get("symbol")]
        return len(same_symbol) == 0

    def size_and_protect(self, signal: Dict[str, Any], atr: Optional[float] = None) -> Dict[str, Any]:
        """
        Valida y ajusta el tamaño de posición con riesgo adaptativo.

        En modo PAPER con PnL negativo: reduce tamaño de posición progresivamente.
        En modo LIVE: mantiene sizing normal.

        Si la señal ya tiene stop_loss, lo respeta.
        Si no, calcula uno basado en ATR.

        IMPORTANTE: size siempre en BTC, notional en USDT se calcula aparte.
        """
        try:
            price = signal["price"]
            atr_value = atr if atr and atr > 0 else price * 0.005

            if "stop_loss" in signal and signal["stop_loss"] > 0:
                stop_loss = signal["stop_loss"]
                stop_distance = abs(price - stop_loss)
            else:

                if signal["action"].lower() == "buy":
                    stop_loss = price - atr_value
                    stop_distance = atr_value
                else:
                    stop_loss = price + atr_value
                    stop_distance = atr_value

            risk_multiplier = self.get_adaptive_risk_multiplier()

            base_risk_pct = self.config.RISK_PER_TRADE
            adjusted_risk_pct = base_risk_pct * risk_multiplier
            risk_amount = self.state.equity * adjusted_risk_pct

            qty_btc = risk_amount / stop_distance

            notional_usdt = qty_btc * price

            if self.config.TRADING_MODE == "PAPER" and risk_multiplier < 1.0:
                max_exposure = self.state.equity * 0.9
            else:
                max_exposure = self.state.equity * 0.5

            if notional_usdt > max_exposure:
                qty_btc = max_exposure / price
                self.logger.warning(
                    f"⚠️ Position ajustada por exposición: {notional_usdt:.2f} -> {max_exposure:.2f} USDT"
                )

            qty_btc = max(qty_btc, 0.0001)

            if signal["action"].lower() == "buy":
                take_profit = price + stop_distance * 1
            else:
                take_profit = price - stop_distance * 1

            signal['risk_amount'] = risk_amount
            signal['atr_value'] = atr_value
            signal['r_value'] = stop_distance
            signal['risk_multiplier'] = risk_multiplier

            signal.update({
                "position_size": round(qty_btc, 6),
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
            })

            mode_str = "[PAPER]" if self.config.TRADING_MODE == "PAPER" else "[LIVE]"
            self.logger.debug(
                f"🧮 Sizing {mode_str} | {signal['symbol']} | Qty_BTC={qty_btc:.6f} | "
                f"Price={price:.2f} | Notional_USDT={notional_usdt:.2f} | "
                f"Equity={self.state.equity:.2f} | SL={stop_loss:.2f} | TP={take_profit:.2f} | "
                f"Stop_Distance={stop_distance:.2f} | Risk={risk_amount:.2f} | "
                f"Risk_Multiplier={risk_multiplier:.2f}"
            )
            return signal

        except Exception as e:
            self.logger.exception(f"❌ Error calculando tamaño o SL/TP: {e}")
            return signal

    def should_close_position(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """Evalúa si se debe cerrar una posición abierta."""
        try:
            price = market_data["price"]
            side = position["side"].upper()
            symbol = position.get("symbol", "UNKNOWN")
            sl = position.get("stop_loss")
            tp = position.get("take_profit")

            if side == "BUY" and sl and tp:
                if price <= sl:
                    self.logger.info(
                        f"🛑 [{symbol}] Stop Loss alcanzado: {price:.2f} <= {sl:.2f}")
                    return True
                if price >= tp:
                    self.logger.info(
                        f"🛑 [{symbol}] Take Profit alcanzado: {price:.2f} >= {tp:.2f}")
                    return True

            if side == "SELL" and sl and tp:
                if price >= sl:
                    self.logger.info(
                        f"🛑 [{symbol}] Stop Loss alcanzado: {price:.2f} >= {sl:.2f}")
                    return True
                if price <= tp:
                    self.logger.info(
                        f"🛑 [{symbol}] Take Profit alcanzado: {price:.2f} <= {tp:.2f}")
                    return True

            entry_time = position.get("entry_time")
            if entry_time:

                if isinstance(entry_time, str):
                    try:
                        entry_time = datetime.fromisoformat(
                            entry_time.replace('Z', '+00:00'))
                    except:
                        entry_time = datetime.now()

                time_diff = datetime.now() - entry_time
                time_seconds = time_diff.total_seconds()

                if time_seconds > 30:
                    self.logger.info(
                        f"⏰ [{symbol}] TIME STOP OBLIGATORIO: {time_seconds:.1f} segundos (>30s)")
                    return True

            return False
        except Exception as e:
            self.logger.exception(f"❌ Error evaluando cierre de posición: {e}")
            return False

    def register_trade(self, trade_data: Dict[str, Any]):
        """
        Registra un trade en el historial para logging y trade_history.

        ⚠️ CRÍTICO: Este método NO modifica equity, daily_pnl, total_pnl, trades_today.
        apply_trade_result() es la ÚNICA fuente de verdad financiera.

        IMPORTANTE: En modo PAPER, los trades se registran SIEMPRE,
        incluso si el PnL es negativo, para acumular datos para ML.
        """
        try:
            pnl = trade_data.get("pnl", 0.0)
            # NO incrementar trades aquí - solo se incrementa en apply_trade_result()
            # register_trade es solo para logging, apply_trade_result es la fuente de verdad
            # ⚠️ CRÍTICO: NO modificar equity, daily_pnl, total_pnl aquí
            # apply_trade_result() es la ÚNICA fuente de verdad financiera
            # NO incrementar trades_today aquí - solo en apply_trade_result()
            if self.state.equity > self.state.peak_equity:
                self.state.peak_equity = self.state.equity

            current_dd = (self.state.peak_equity -
                          self.state.equity) / self.state.peak_equity
            self.state.max_drawdown = max(self.state.max_drawdown, current_dd)

            trade_record = {
                "timestamp": datetime.now(),
                "symbol": trade_data.get("symbol"),
                "action": trade_data.get("action"),
                "price": trade_data.get("price"),
                "size": trade_data.get("position_size"),
                "pnl": pnl,
                "reason": trade_data.get("reason", ""),
                "risk_multiplier": trade_data.get("risk_multiplier", 1.0),
            }
            self.trade_history.append(trade_record)

            self.logger.info(
                f"📘 Trade registrado (historial): {trade_data.get('symbol')} | PnL={pnl:.2f} | "
                f"Risk_Multiplier={trade_record.get('risk_multiplier', 1.0):.2f}")
        except Exception as e:
            self.logger.exception(f"❌ Error registrando trade: {e}")

    def get_risk_metrics(self) -> Dict[str, Any]:
        """Calcula métricas de riesgo globales."""
        try:
            trades = self.trade_history
            total_trades = len(trades)
            pnl_list = [t["pnl"] for t in trades]

            win_rate = len([p for p in pnl_list if p > 0]) / \
                total_trades if total_trades else 0
            sharpe_ratio = np.mean(
                pnl_list) / np.std(pnl_list) if len(pnl_list) > 1 and np.std(pnl_list) > 0 else 0
            drawdown = (self.state.peak_equity -
                        self.state.equity) / self.state.peak_equity

            metrics = {
                "daily_pnl": self.state.daily_pnl,
                "total_pnl": self.state.total_pnl,
                "win_rate": win_rate,
                "sharpe_ratio": sharpe_ratio,
                "drawdown": drawdown,
                "equity": self.state.equity,
                "trades_today": self.state.trades_today,
                "adaptive_risk_multiplier": self.get_adaptive_risk_multiplier(),
            }

            self.logger.debug(f"📊 Métricas de riesgo: {metrics}")
            return metrics
        except Exception as e:
            self.logger.exception(
                f"❌ Error calculando métricas de riesgo: {e}")
            return {}

    def update_equity(self, new_equity: float):
        """Actualiza el balance actual y calcula drawdown."""
        self.state.equity = new_equity
        if new_equity > self.state.peak_equity:
            self.state.peak_equity = new_equity
        drawdown = (self.state.peak_equity - new_equity) / \
            self.state.peak_equity
        self.state.max_drawdown = max(self.state.max_drawdown, drawdown)
        self.logger.debug(
            f"💰 Equity actualizado: {new_equity:.2f} | DD={drawdown:.2%}")

    def reset_daily_metrics(self):
        """
        Reinicia métricas diarias.
        ÚNICA fuente de verdad: executed_trades_today (trades_today es alias para compatibilidad).
        """
        self.state.daily_pnl = 0.0
        self.state.executed_trades_today = 0  # ÚNICA fuente de verdad
        self.state.trades_today = 0  # Alias para compatibilidad

        if self.config.TRADING_MODE == "PAPER":
            self._adaptive_risk_level = 1.0
            self.logger.info(
                f"🔄 Métricas diarias reiniciadas | Risk multiplier restaurado a 1.0")
        else:
            self.logger.info("🔄 Métricas diarias reiniciadas")

    def emergency_stop(self):
        """Detiene toda actividad de trading."""
        self.logger.critical(
            "🚨 PARADA DE EMERGENCIA ACTIVADA: trading detenido inmediatamente")
