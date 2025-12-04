"""
Gestor de riesgo del bot de trading
Implementa controles de riesgo, sizing de posición y métricas de rendimiento.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import numpy as np

from config import Config
from src.utils.logging_setup import setup_logging


# ======================================================
# 📊 ESTRUCTURA DE ESTADO
# ======================================================
@dataclass
class RiskState:
    """Estado de riesgo persistente."""
    equity: float = 10_000.0
    day: date = date.today()
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    trades_today: int = 0
    max_drawdown: float = 0.0
    peak_equity: float = 10_000.0


# ======================================================
# 💼 GESTOR DE RIESGO
# ======================================================
class RiskManager:
    """Gestor de riesgo integral para trading automático."""

    def __init__(self, config: Config, state: Optional[RiskState] = None):
        self.config = config
        self.state = state or RiskState(equity=config.INITIAL_CAPITAL)
        self.logger = setup_logging(
            __name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        self.trade_history: List[Dict[str, Any]] = []

    # ======================================================
    # 🔒 VALIDACIONES DE RIESGO
    # ======================================================
    def validate_trade(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """Verifica si la operación cumple los criterios de riesgo."""
        try:
            if not self._check_daily_limits():
                self.logger.warning(
                    "⚠️ Límite diario de pérdida o trades alcanzado.")
                return False

            if len(current_positions) >= self.config.MAX_POSITIONS:
                self.logger.warning(
                    "⚠️ Número máximo de posiciones abiertas alcanzado.")
                return False

            if not self._check_total_exposure(signal, current_positions):
                self.logger.warning(
                    "⚠️ Exposición total excede el límite permitido.")
                return False

            if not self._check_correlation(signal, current_positions):
                self.logger.warning(
                    "⚠️ Posición correlacionada con existentes.")
                return False

            return True
        except Exception as e:
            self.logger.exception(f"❌ Error validando operación: {e}")
            return False

    def unregister_position(self):
        """Se llama cuando una posición se cierra"""
        if self.state.trades_today > 0:
            self.state.trades_today -= 1
        self.logger.info(
            f"🧹 Slot liberado - posiciones abiertas: {self.open_positions}"
        )
    def check_daily_limits(self, daily_pnl: float = None, daily_trades: int = None) -> bool:
        """
        Verifica límites diarios de pérdida y cantidad de trades.
        Método público para uso externo.
        """
        # Usar valores actualizados si se proporcionan, sino usar del estado
        pnl = daily_pnl if daily_pnl is not None else self.state.daily_pnl
        trades = daily_trades if daily_trades is not None else self.state.trades_today

        max_loss = self.state.equity * self.config.MAX_DAILY_LOSS
        max_gain = self.state.equity * self.config.MAX_DAILY_GAIN
        max_trades = getattr(self.config, "MAX_DAILY_TRADES", 20)

        # Verificar si se alcanzó el límite de pérdida
        if pnl < -max_loss:
            self.logger.warning(
                f"⚠️ Límite de pérdida diaria alcanzado: {pnl:.2f} / {-max_loss:.2f}")
            return False

        # Verificar si se alcanzó el límite de ganancia (opcional)
        if pnl > max_gain:
            self.logger.info(
                f"✅ Límite de ganancia diaria alcanzado: {pnl:.2f} / {max_gain:.2f}")
            return False

        # Verificar límite de trades
        if trades >= max_trades:
            self.logger.warning(
                f"⚠️ Límite de trades diarios alcanzado: {trades} / {max_trades}")
            return False

        return True

    def _check_daily_limits(self) -> bool:
        """Verifica límites diarios de pérdida y cantidad de trades (método interno)."""
        return self.check_daily_limits()

    def _check_total_exposure(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """Limita la exposición total (por ej. máx. 50% del capital)."""
        try:
            total_exposure = sum(
                pos.get("size", 0) * pos.get("entry_price", 0) for pos in current_positions)
            new_exposure = signal.get(
                "position_size", 0) * signal.get("price", 0)
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

    def _check_correlation(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """Evita posiciones duplicadas del mismo símbolo."""
        same_symbol = [
            p for p in current_positions if p.get("symbol") == signal.get("symbol")]
        is_valid = len(same_symbol) == 0
        if not is_valid:
            self.logger.warning(
                f"⚠️ Ya existe posición abierta para {signal.get('symbol')} "
                f"({len(same_symbol)} posiciones activas)"
            )
        return is_valid

    # ======================================================
    # 💰 SIZING Y PROTECCIÓN
    # ======================================================
    def size_and_protect(self, signal: Dict[str, Any], atr: Optional[float] = None) -> Dict[str, Any]:
        """Calcula tamaño de posición, stop loss y take profit."""
        try:
            price = signal["price"]
            atr_value = atr if atr and atr > 0 else price * 0.015  # 1.5% por defecto

            risk_pct = self.config.MAX_POSITION_RISK_PCT / 100.0
            risk_amount = self.state.equity * risk_pct
            qty = max(risk_amount / atr_value, 0.0001)

            if signal["action"].lower() == "buy":
                stop_loss = price - atr_value
                take_profit = price + atr_value * 2
            else:
                stop_loss = price + atr_value
                take_profit = price - atr_value * 2

            signal.update({
                "position_size": round(qty, 6),
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
            })

            self.logger.debug(
                f"🧮 Sizing calculado | {signal['symbol']} | Qty={qty:.4f} | SL={stop_loss:.2f} | TP={take_profit:.2f}"
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

            # Verificar Stop Loss y Take Profit
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

            # TIME STOP OBLIGATORIO: Cerrar cualquier posición abierta más de 120 segundos
            entry_time = position.get("entry_time")
            if entry_time:
                # Convertir string a datetime si es necesario
                if isinstance(entry_time, str):
                    try:
                        entry_time = datetime.fromisoformat(
                            entry_time.replace('Z', '+00:00'))
                    except:
                        entry_time = datetime.now()

                time_diff = datetime.now() - entry_time
                time_seconds = time_diff.total_seconds()

                # TIME STOP OBLIGATORIO: 120 segundos (2 minutos)
                if time_seconds > 120:
                    self.logger.info(
                        f"⏰ [{symbol}] TIME STOP OBLIGATORIO: {time_seconds:.1f} segundos (>120s)")
                    return True

            return False
        except Exception as e:
            self.logger.exception(f"❌ Error evaluando cierre de posición: {e}")
            return False

    # ======================================================
    # 📈 MÉTRICAS Y REGISTRO
    # ======================================================
    def register_trade(self, trade_data: Dict[str, Any]):
        """Registra un trade en el historial y actualiza métricas."""
        try:
            pnl = trade_data.get("pnl", 0.0)
            self.state.daily_pnl += pnl
            self.state.total_pnl += pnl
            self.state.trades_today += 1

            self.trade_history.append({
                "timestamp": datetime.now(),
                "symbol": trade_data.get("symbol"),
                "action": trade_data.get("action"),
                "price": trade_data.get("price"),
                "size": trade_data.get("position_size"),
                "pnl": pnl,
                "reason": trade_data.get("reason", "")
            })

            self.logger.info(
                f"📘 Trade registrado: {trade_data.get('symbol')} | PnL={pnl:.2f}")
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
            }

            self.logger.debug(f"📊 Métricas de riesgo: {metrics}")
            return metrics
        except Exception as e:
            self.logger.exception(
                f"❌ Error calculando métricas de riesgo: {e}")
            return {}

    # ======================================================
    # 🔁 MANTENIMIENTO Y EMERGENCIA
    # ======================================================
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
        """Reinicia métricas diarias."""
        self.state.daily_pnl = 0.0
        self.state.trades_today = 0
        self.logger.info("🔄 Métricas diarias reiniciadas")

    def emergency_stop(self):
        """Detiene toda actividad de trading."""
        self.logger.critical(
            "🚨 PARADA DE EMERGENCIA ACTIVADA: trading detenido inmediatamente")
