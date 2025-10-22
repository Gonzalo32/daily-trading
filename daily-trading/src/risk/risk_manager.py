"""
Gestor de riesgo del bot de trading
Implementa controles de riesgo, sizing de posición y métricas de rendimiento.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import numpy as np
from config import Config


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


class RiskManager:
    """Gestor de riesgo integral para trading automático."""

    def __init__(self, config: Config, state: Optional[RiskState] = None):
        self.config = config
        self.state = state or RiskState(equity=config.INITIAL_CAPITAL)
        self.logger = logging.getLogger(__name__)
        self.trade_history: List[Dict[str, Any]] = []

    # ======================================================
    # 🔒 VALIDACIONES DE RIESGO
    # ======================================================
    def validate_trade(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """Verifica si la operación cumple los criterios de riesgo."""
        try:
            if not self._check_daily_limits():
                self.logger.warning("⚠️ Límite diario alcanzado.")
                return False

            if len(current_positions) >= self.config.MAX_POSITIONS:
                self.logger.warning("⚠️ Número máximo de posiciones abiertas alcanzado.")
                return False

            if not self._check_total_exposure(signal, current_positions):
                self.logger.warning("⚠️ Exposición total excede el límite permitido.")
                return False

            if not self._check_correlation(signal, current_positions):
                self.logger.warning("⚠️ Posición correlacionada con existentes.")
                return False

            return True
        except Exception as e:
            self.logger.exception(f"❌ Error validando operación: {e}")
            return False

    def _check_daily_limits(self) -> bool:
        """Verifica límites diarios de pérdida y cantidad de trades."""
        max_loss = self.state.equity * (self.config.MAX_DAILY_LOSS_PCT / 100)
        max_trades = self.config.MAX_DAILY_TRADES
        return (
            abs(self.state.daily_pnl) < max_loss
            and self.state.trades_today < max_trades
        )

    def _check_total_exposure(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """Limita la exposición total (por ej. máx. 50% del capital)."""
        total_exposure = sum(pos["position_size"] * pos["entry_price"] for pos in current_positions)
        new_exposure = signal["position_size"] * signal["price"]
        max_exposure = self.state.equity * 0.5
        return total_exposure + new_exposure <= max_exposure

    def _check_correlation(self, signal: Dict[str, Any], current_positions: List[Dict[str, Any]]) -> bool:
        """Evita posiciones duplicadas del mismo símbolo."""
        same_symbol = [p for p in current_positions if p["symbol"] == signal["symbol"]]
        return len(same_symbol) == 0

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
            return signal
        except Exception as e:
            self.logger.exception(f"❌ Error calculando tamaño o SL/TP: {e}")
            return signal

    def should_close_position(self, position: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """Evalúa si se debe cerrar una posición abierta."""
        try:
            price = market_data["price"]
            side = position["side"].upper()
            sl = position["stop_loss"]
            tp = position["take_profit"]

            if side == "BUY" and (price <= sl or price >= tp):
                reason = "Stop Loss" if price <= sl else "Take Profit"
                self.logger.info(f"🛑 {reason} alcanzado ({price}) para {position['symbol']}")
                return True

            if side == "SELL" and (price >= sl or price <= tp):
                reason = "Stop Loss" if price >= sl else "Take Profit"
                self.logger.info(f"🛑 {reason} alcanzado ({price}) para {position['symbol']}")
                return True

            # Tiempo máximo de posición (opcional)
            entry_time = position.get("entry_time")
            if entry_time and datetime.now() - entry_time > timedelta(hours=4):
                self.logger.info("⏰ Tiempo máximo de posición alcanzado")
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
            self.logger.info(f"📘 Trade registrado: {trade_data.get('symbol')} | PnL={pnl:.2f}")
        except Exception as e:
            self.logger.exception(f"❌ Error registrando trade: {e}")

    def get_risk_metrics(self) -> Dict[str, Any]:
        """Calcula métricas de riesgo globales."""
        try:
            trades = self.trade_history
            total_trades = len(trades)
            pnl_list = [t["pnl"] for t in trades]

            win_rate = len([p for p in pnl_list if p > 0]) / total_trades if total_trades else 0
            sharpe_ratio = np.mean(pnl_list) / np.std(pnl_list) if len(pnl_list) > 1 and np.std(pnl_list) > 0 else 0
            drawdown = (self.state.peak_equity - self.state.equity) / self.state.peak_equity

            return {
                "daily_pnl": self.state.daily_pnl,
                "total_pnl": self.state.total_pnl,
                "win_rate": win_rate,
                "sharpe_ratio": sharpe_ratio,
                "drawdown": drawdown,
                "equity": self.state.equity,
                "trades_today": self.state.trades_today,
            }
        except Exception as e:
            self.logger.exception(f"❌ Error calculando métricas de riesgo: {e}")
            return {}

    # ======================================================
    # 🔁 MANTENIMIENTO Y EMERGENCIA
    # ======================================================
    def update_equity(self, new_equity: float):
        """Actualiza el balance actual y calcula drawdown."""
        self.state.equity = new_equity
        if new_equity > self.state.peak_equity:
            self.state.peak_equity = new_equity
        drawdown = (self.state.peak_equity - new_equity) / self.state.peak_equity
        self.state.max_drawdown = max(self.state.max_drawdown, drawdown)

    def reset_daily_metrics(self):
        """Reinicia métricas diarias."""
        self.state.daily_pnl = 0.0
        self.state.trades_today = 0
        self.logger.info("🔄 Métricas diarias reiniciadas")

    def emergency_stop(self):
        """Detiene toda actividad de trading."""
        self.logger.critical("🚨 PARADA DE EMERGENCIA ACTIVADA: trading detenido inmediatamente")
