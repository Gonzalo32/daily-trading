

import pandas as pd
import os
import csv
import shutil
from datetime import datetime
from config import Config
from src.utils.logging_setup import setup_logging


class TradeRecorder:
    """
    Registro compacto y útil para ML:
    Guarda risk_amount, atr_value, r_value y resultado real (pnl).
    """

    FULL_SCHEMA = [
        "timestamp",
        "symbol",
        "side",
        "entry_price",
        "exit_price",
        "pnl",
        "size",
        "stop_loss",
        "take_profit",
        "duration_seconds",
        "risk_amount",
        "atr_value",
        "r_value",
        "risk_multiplier",
        "ema_cross_diff_pct",
        "atr_pct",
        "rsi_normalized",
        "price_to_fast_pct",
        "price_to_slow_pct",
        "trend_direction",
        "trend_strength",
        "regime",
        "volatility_level",
        "target",
        "trade_type",
        "exit_type",
        "r_multiple",
        "time_in_trade",
    ]

    def __init__(self, data_file: str = "src/ml/training_data_v2.csv", decisions_file: str = "src/ml/decisions.csv"):
        self.data_file = data_file
        self.decisions_file = decisions_file
        self.logger = setup_logging(__name__)
        self.enable_auto_train = Config.ENABLE_AUTO_TRAIN
        self.enable_training_schema_migration = Config.ENABLE_TRAINING_SCHEMA_MIGRATION
        self.trade_columns = list(self.FULL_SCHEMA)
        self._warned_missing_decision_id_column = False

        if not os.path.exists(self.data_file) or os.path.getsize(self.data_file) == 0:
            self._initialize_trades_file()
            self.trade_columns = list(self.FULL_SCHEMA)

        if not os.path.exists(self.decisions_file):
            self._initialize_decisions_file()

    def _load_trade_columns(self):
        return list(self.FULL_SCHEMA)

    def _initialize_trades_file(self):
        df = pd.DataFrame(columns=self.FULL_SCHEMA)
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        df.to_csv(self.data_file, index=False)
        self.logger.info(f"Archivo de TRADES creado: {self.data_file}")

    def _initialize_decisions_file(self):
        df = pd.DataFrame(columns=[
            "timestamp", "symbol", "decision_id",
            "ema_cross_diff_pct", "atr_pct", "rsi_normalized",
            "price_to_fast_pct", "price_to_slow_pct",
            "trend_direction", "trend_strength",
            "decision_buy_possible", "decision_sell_possible", "decision_hold_possible",
            "strategy_signal", "executed_action", "was_executed",
            "regime", "volatility_level",
            "decision_outcome", "reject_reason", "reason"
        ])
        os.makedirs(os.path.dirname(self.decisions_file), exist_ok=True)
        df.to_csv(self.decisions_file, index=False)
        self.logger.info(
            f"Archivo de DECISIONES creado: {self.decisions_file}")

    def record_trade(self, position: dict, exit_price: float, pnl: float, market_data_context: dict = None):
        """
        Guarda el trade ejecutado en el CSV con features relativas.

        Args:
            position: Datos de la posición (entry_price, exit_price, etc.)
            exit_price: Precio de salida
            pnl: P&L del trade
            market_data_context: Contexto de mercado al momento de entrada (opcional)
        """
        try:
            duration = None
            if position.get("exit_time") and position.get("entry_time"):
                duration = (position["exit_time"] -
                            position["entry_time"]).total_seconds()

            r_value = position.get("r_value")
            if r_value is None:
                r_value = 1.0
            else:
                try:
                    r_value = float(r_value)
                except (ValueError, TypeError):
                    r_value = 1.0

            entry_price = position.get("entry_price", 0)

            market_data = market_data_context or {}
            indicators = market_data.get("indicators", {})

            fast_ma = indicators.get("fast_ma", entry_price)
            slow_ma = indicators.get("slow_ma", entry_price)
            rsi = indicators.get("rsi", 50)
            atr = indicators.get("atr", 0)

            ema_cross_diff_pct = ((fast_ma - slow_ma) /
                                  slow_ma * 100) if slow_ma > 0 else 0
            atr_pct = (atr / entry_price * 100) if entry_price > 0 else 0
            rsi_normalized = (rsi - 50) / 50
            price_to_fast_pct = ((entry_price - fast_ma) /
                                 fast_ma * 100) if fast_ma > 0 else 0
            price_to_slow_pct = ((entry_price - slow_ma) /
                                 slow_ma * 100) if slow_ma > 0 else 0
            trend_direction = 1.0 if fast_ma > slow_ma else (
                -1.0 if fast_ma < slow_ma else 0.0)
            trend_strength = abs(ema_cross_diff_pct) / 100.0

            regime_info = market_data.get("regime_info", {})
            regime = regime_info.get("regime", "unknown")
            volatility = regime_info.get("volatility", "normal")

            record = {
                "timestamp": position.get("entry_time"),
                "symbol": position.get("symbol"),
                "side": position.get("side"),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "size": position.get("size"),
                "stop_loss": position.get("stop_loss"),
                "take_profit": position.get("take_profit"),
                "duration_seconds": duration,

                "risk_amount": position.get("risk_amount"),
                "atr_value": position.get("atr_value"),
                "r_value": r_value,
                "risk_multiplier": position.get("risk_multiplier", 1.0),
                "ema_cross_diff_pct": ema_cross_diff_pct,
                "atr_pct": atr_pct,
                "rsi_normalized": rsi_normalized,
                "price_to_fast_pct": price_to_fast_pct,
                "price_to_slow_pct": price_to_slow_pct,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,

                "regime": regime,
                "volatility_level": volatility,

                "target": 1 if pnl >= r_value else 0,
                "trade_type": "executed",

                "exit_type": position.get("exit_type", "unknown"),
                "r_multiple": pnl / r_value if r_value > 0 else 0,
                "time_in_trade": duration
            }

            row = {col: record.get(col) for col in self.trade_columns}

            df = pd.DataFrame([row], columns=self.trade_columns)
            df.to_csv(self.data_file, mode="a", index=False, header=False)

            self.logger.info(
                f"trade saved | {record['symbol']} | PnL={pnl:.2f} | Target={record['target']}"
            )

            if self.enable_auto_train:
                try:
                    from src.ml.auto_trainer import auto_train_if_needed
                    auto_train_if_needed()
                except Exception as e:
                    self.logger.warning(
                        f"Auto-train no disponible o falló: {e}"
                    )

        except Exception as e:
            self.logger.exception(f"Error guardando trade: {e}")

    def record_rejected_signal(self, signal: dict, market_data: dict, reason: str, regime_info: dict = None):
        """
        Registra una señal rechazada (para entrenar clasificación de "no trade").

        Args:
            signal: Señal que fue rechazada
            market_data: Datos de mercado al momento de la señal
            reason: Razón del rechazo
            regime_info: Información del régimen de mercado
        """
        try:
            indicators = market_data.get("indicators", {})
            price = market_data.get("price", 0)

            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            rsi = indicators.get("rsi", 50)
            atr = indicators.get("atr", 0)

            # ⚠️ CRÍTICO: Solo usar columnas que existen en el header inicial
            # NO usar ema_fast_diff_pct ni ema_slow_diff_pct (no existen en header)
            ema_cross_diff_pct = ((fast_ma - slow_ma) /
                                  slow_ma * 100) if slow_ma > 0 else 0
            atr_pct = (atr / price * 100) if price > 0 else 0
            rsi_normalized = (rsi - 50) / 50
            price_to_fast_pct = ((price - fast_ma) /
                                 fast_ma * 100) if fast_ma > 0 else 0
            price_to_slow_pct = ((price - slow_ma) /
                                 slow_ma * 100) if slow_ma > 0 else 0
            trend_direction = 1.0 if fast_ma > slow_ma else -1.0
            trend_strength = abs(ema_cross_diff_pct) / 100.0

            regime = regime_info.get(
                "regime", "unknown") if regime_info else "unknown"
            volatility = regime_info.get(
                "volatility", "normal") if regime_info else "normal"

            record = {
                "timestamp": market_data.get("timestamp"),
                "symbol": market_data.get("symbol"),
                "side": signal.get("action", "UNKNOWN"),
                "entry_price": price,
                "exit_price": None,
                "pnl": None,
                "size": None,
                "stop_loss": signal.get("stop_loss"),
                "take_profit": signal.get("take_profit"),
                "duration_seconds": None,

                "risk_amount": None,
                "atr_value": atr,
                "r_value": None,
                "risk_multiplier": None,

                # ⚠️ Solo columnas que existen en header inicial
                "ema_cross_diff_pct": ema_cross_diff_pct,
                "atr_pct": atr_pct,
                "rsi_normalized": rsi_normalized,
                "price_to_fast_pct": price_to_fast_pct,
                "price_to_slow_pct": price_to_slow_pct,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,

                "regime": regime,
                "volatility_level": volatility,

                "target": 0,
                "trade_type": f"rejected_{reason}",
                "exit_type": None,
                "r_multiple": None,
                "time_in_trade": None
            }

            row = {col: record.get(col) for col in self.trade_columns}

            df = pd.DataFrame([row], columns=self.trade_columns)
            df.to_csv(self.data_file, mode="a", index=False, header=False)

            if not hasattr(self, '_rejected_count'):
                self._rejected_count = 0
            self._rejected_count += 1
            if self._rejected_count % 10 == 0:
                self.logger.debug(
                    f"Senal rechazada guardada ML (#{self._rejected_count}) | Razon: {reason}"
                )

        except Exception as e:
            self.logger.exception(f"Error guardando senal rechazada: {e}")

    def record_no_signal_context(self, market_data: dict, regime_info: dict = None):
        """
        Registra contexto cuando NO hay señal (para entrenar clasificación de "no trade").

        Args:
            market_data: Datos de mercado cuando no había señal
            regime_info: Información del régimen de mercado
        """
        try:

            if not hasattr(self, '_no_signal_count'):
                self._no_signal_count = 0
            self._no_signal_count += 1

            if self._no_signal_count % 20 != 0:
                return

            indicators = market_data.get("indicators", {})
            price = market_data.get("price", 0)

            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            rsi = indicators.get("rsi", 50)
            atr = indicators.get("atr", 0)

            # ⚠️ CRÍTICO: Solo usar columnas que existen en el header inicial
            # NO usar ema_fast_diff_pct ni ema_slow_diff_pct (no existen en header)
            ema_cross_diff_pct = ((fast_ma - slow_ma) /
                                  slow_ma * 100) if slow_ma > 0 else 0
            atr_pct = (atr / price * 100) if price > 0 else 0
            rsi_normalized = (rsi - 50) / 50
            price_to_fast_pct = ((price - fast_ma) /
                                 fast_ma * 100) if fast_ma > 0 else 0
            price_to_slow_pct = ((price - slow_ma) /
                                 slow_ma * 100) if slow_ma > 0 else 0
            trend_direction = 1.0 if fast_ma > slow_ma else -1.0
            trend_strength = abs(ema_cross_diff_pct) / 100.0

            regime = regime_info.get(
                "regime", "unknown") if regime_info else "unknown"
            volatility = regime_info.get(
                "volatility", "normal") if regime_info else "normal"

            record = {
                "timestamp": market_data.get("timestamp"),
                "symbol": market_data.get("symbol"),
                "side": "NO_SIGNAL",
                "entry_price": price,
                "exit_price": None,
                "pnl": None,
                "size": None,
                "stop_loss": None,
                "take_profit": None,
                "duration_seconds": None,

                "risk_amount": None,
                "atr_value": atr,
                "r_value": None,
                "risk_multiplier": None,

                # ⚠️ Solo columnas que existen en header inicial
                "ema_cross_diff_pct": ema_cross_diff_pct,
                "atr_pct": atr_pct,
                "rsi_normalized": rsi_normalized,
                "price_to_fast_pct": price_to_fast_pct,
                "price_to_slow_pct": price_to_slow_pct,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,

                "regime": regime,
                "volatility_level": volatility,

                "target": 0,
                "trade_type": "no_signal",
                "exit_type": None,
                "r_multiple": None,
                "time_in_trade": None
            }

            row = {col: record.get(col) for col in self.trade_columns}

            df = pd.DataFrame([row], columns=self.trade_columns)
            df.to_csv(self.data_file, mode="a", index=False, header=False)

            if self._no_signal_count % 200 == 0:
                self.logger.debug(
                    f"Contexto sin senal guardado ML (#{self._no_signal_count})"
                )

        except Exception as e:
            self.logger.exception(f"Error guardando contexto sin senal: {e}")

    def record_decision_sample(self, decision_sample, decision_sampler=None):
        """
        Registra un DecisionSample completo en decisions.csv (incluye HOLD explícito).

        Este método registra TODAS las decisiones, no solo trades ejecutados.
        Permite al ML aprender del espacio completo de decisiones.

        Args:
            decision_sample: DecisionSample de decision_sampler
            decision_sampler: Instancia de DecisionSampler para usar to_dict() como fuente única
        """
        try:
            # ⚠️ CRÍTICO: Usar DecisionSampler.to_dict() como ÚNICA FUENTE DE VERDAD
            # Esto garantiza consistencia y alineación con el formato del CSV
            if decision_sampler and hasattr(decision_sampler, 'to_dict'):
                record = decision_sampler.to_dict(decision_sample)
            else:
                # Fallback si no hay DecisionSampler (no debería pasar en producción)
                self.logger.warning(
                    "⚠️ DecisionSampler no disponible, usando fallback para record_decision_sample")
                from datetime import datetime
                from src.utils.decision_constants import DecisionOutcome, ExecutedAction

                if isinstance(decision_sample, dict):
                    features = decision_sample.get("features", {})
                    decision_space = decision_sample.get("decision_space", {})
                    market_context = decision_sample.get("market_context", {})
                    timestamp = decision_sample.get("timestamp")
                    symbol = decision_sample.get("symbol")
                    decision_id = decision_sample.get("decision_id", "")
                    strategy_signal = decision_sample.get("strategy_signal")
                    executed_action = decision_sample.get(
                        "executed_action", ExecutedAction.HOLD.value)
                    decision_outcome = decision_sample.get(
                        "decision_outcome", DecisionOutcome.NO_SIGNAL.value)
                    reject_reason = decision_sample.get("reject_reason")
                    reason = decision_sample.get("reason", "")
                else:
                    features = decision_sample.features
                    decision_space = decision_sample.decision_space
                    market_context = decision_sample.market_context
                    timestamp = decision_sample.timestamp
                    symbol = decision_sample.symbol
                    decision_id = getattr(decision_sample, "decision_id", "")
                    strategy_signal = decision_sample.strategy_signal
                    executed_action = decision_sample.executed_action or ExecutedAction.HOLD.value
                    decision_outcome = decision_sample.decision_outcome or DecisionOutcome.NO_SIGNAL.value
                    reject_reason = decision_sample.reject_reason
                    reason = decision_sample.reason or ""

                # Validar strategy_signal ∈ {"BUY","SELL","NONE"}
                strategy_signal_normalized = strategy_signal
                if strategy_signal and strategy_signal.upper() in ["BUY", "SELL"]:
                    strategy_signal_normalized = strategy_signal.upper()
                elif strategy_signal is None or strategy_signal == "NONE":
                    strategy_signal_normalized = "NONE"
                else:
                    self.logger.warning(
                        f"⚠️ strategy_signal inválido: {strategy_signal}. Usando NONE.")
                    strategy_signal_normalized = "NONE"

                # was_executed derivado de executed_action (no de flags externos)
                was_executed = (executed_action in [
                                ExecutedAction.BUY.value, ExecutedAction.SELL.value])

                record = {
                    "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
                    "symbol": symbol,
                    "decision_id": decision_id or "",
                    "ema_cross_diff_pct": features.get("ema_diff_pct", 0),
                    "atr_pct": features.get("atr_pct", 0),
                    "rsi_normalized": features.get("rsi_normalized", 0),
                    "price_to_fast_pct": features.get("price_to_fast_pct", 0),
                    "price_to_slow_pct": features.get("price_to_slow_pct", 0),
                    "trend_direction": features.get("trend_direction", 0),
                    "trend_strength": features.get("trend_strength", 0),
                    "decision_buy_possible": decision_space.get("buy", False),
                    "decision_sell_possible": decision_space.get("sell", False),
                    "decision_hold_possible": decision_space.get("hold", True),
                    "strategy_signal": strategy_signal_normalized,
                    "executed_action": executed_action,
                    "was_executed": was_executed,
                    "regime": market_context.get("regime", "unknown"),
                    # Unificado: volatility_level
                    "volatility_level": market_context.get("volatility_level", market_context.get("volatility", "medium")),
                    "decision_outcome": decision_outcome,
                    "reject_reason": reject_reason or "",
                    "reason": reason
                }

            df = pd.DataFrame([record])
            df.to_csv(self.decisions_file, mode="a", index=False, header=False)

            if not hasattr(self, '_decision_sample_count'):
                self._decision_sample_count = 0
            self._decision_sample_count += 1

            decision_id = record.get("decision_id", "")
            if self._decision_sample_count % 100 == 0:
                log_msg = (
                    f"📚 DecisionSample guardado (#{self._decision_sample_count}) | "
                    f"Action: {record['executed_action']} | Outcome: {record['decision_outcome']}"
                )
                if decision_id:
                    log_msg += f" | decision_id={decision_id}"
                self.logger.debug(log_msg)

        except Exception as e:
            self.logger.exception(f"❌ Error guardando DecisionSample: {e}")

    def get_training_data(self, limit: int = None):
        """
        Retorna el dataset completo de training o las últimas N filas.
        """
        try:
            if not os.path.exists(self.data_file):
                self.logger.warning(
                    "⚠️ No hay archivo de training_data todavía.")
                return pd.DataFrame()

            try:
                df = pd.read_csv(
                    self.data_file, on_bad_lines='skip', encoding='utf-8')
            except Exception as parse_error:
                self.logger.warning(
                    f"⚠️ Error parseando CSV: {parse_error}. Intentando corregir...")

                try:
                    df = pd.read_csv(
                        self.data_file, sep=',', error_bad_lines=False, warn_bad_lines=False, encoding='utf-8')
                except:

                    self.logger.warning(
                        "⚠️ No se pudo leer training_data.csv. Usando DataFrame vacío.")
                    return pd.DataFrame()

            if limit is not None and limit > 0:
                df = df.tail(limit)

            return df

        except Exception as e:
            self.logger.warning(
                f"⚠️ Error leyendo training_data: {e}. Continuando con DataFrame vacío.")
            return pd.DataFrame()
