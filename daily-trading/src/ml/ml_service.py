import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from src.ml.ml_features import build_entry_features
from src.ml.ml_logger import MLDecisionLogger
from src.ml.ml_shadow_model import ShadowMLModel
from src.utils.logging_setup import setup_logging


class MLService:
    def __init__(self, config):
        self.config = config
        self.enabled = getattr(config, "ML_ENABLED", False)
        self.mode = getattr(config, "ML_MODE", "shadow").lower()
        self.threshold = float(getattr(config, "ML_THRESHOLD", 0.55))
        self.model_version = getattr(config, "MODEL_VERSION", "shadow_stub_v1")
        self.feature_version = getattr(config, "FEATURE_VERSION", "v1")
        self.db_path = getattr(config, "ML_DECISIONS_DB_PATH", "data/ml_decisions.db")

        self.logger = setup_logging(__name__)
        self.model = ShadowMLModel(self.model_version, self.feature_version)
        self.decision_logger = MLDecisionLogger(self.db_path)
        self._logged_decisions = 0

    def _serialize_features(self, features: Dict[str, Any]) -> Optional[str]:
        if not features:
            return None
        try:
            raw = json.dumps(features, ensure_ascii=True, sort_keys=True)
        except (TypeError, ValueError):
            return None
        if len(raw) > 4000:
            trimmed = dict(list(features.items())[:20])
            return json.dumps(trimmed, ensure_ascii=True, sort_keys=True)
        return raw

    def _ensure_decision_id(self, decision_id: Optional[str]) -> str:
        if decision_id:
            return decision_id
        return str(uuid.uuid4())

    def evaluate_and_log(
        self,
        signal: Optional[Dict[str, Any]],
        market_data: Dict[str, Any],
        regime_info: Optional[Dict[str, Any]],
        bot_state: Optional[Dict[str, Any]],
        decision_id: Optional[str] = None,
        trade_id: Optional[str] = None,
        executed: int = 0,
        trade_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        try:
            decision_id = self._ensure_decision_id(decision_id)
            symbol = "UNKNOWN"
            if signal and signal.get("symbol"):
                symbol = signal.get("symbol")
            elif market_data.get("symbol"):
                symbol = market_data.get("symbol")

            side = "NO_SIGNAL"
            if signal and signal.get("action"):
                side = str(signal.get("action")).upper()

            features = build_entry_features(
                signal=signal,
                market_data=market_data,
                regime_info=regime_info,
                bot_state=bot_state,
            )

            ml_score = float(self.model.predict_proba(features))
            ml_prediction = int(self.model.predict(features))

            if signal is None:
                ml_action = "NO_SIGNAL"
                reason = "Sin señal del strategy"
            else:
                if ml_score >= self.threshold:
                    ml_action = "ALLOW"
                else:
                    ml_action = "BLOCK"
                reason = "Strategy signal"

            would_execute = 1 if side in ["BUY", "SELL"] else 0

            record = {
                "created_at": datetime.utcnow().isoformat(),
                "decision_id": decision_id,
                "trade_id": trade_id,
                "symbol": symbol,
                "side": side,
                "mode": self.mode,
                "model_version": self.model_version,
                "feature_version": self.feature_version,
                "threshold": self.threshold,
                "ml_score": ml_score,
                "ml_prediction": ml_prediction,
                "ml_action": ml_action,
                "reason": reason,
                "features_json": self._serialize_features(features),
                "would_execute": would_execute,
                "executed": executed,
                "trade_type": trade_type,
                "target": None,
                "pnl": None,
                "r_multiple": None,
                "exit_type": None,
            }

            self.decision_logger.insert_decision(record)
            self._logged_decisions += 1
            if self._logged_decisions <= 5:
                self.logger.info(
                    "🧪 ML shadow | action=%s | score=%.4f | thr=%.2f | decision_id=%s",
                    ml_action,
                    ml_score,
                    self.threshold,
                    decision_id,
                )

            return record
        except Exception as e:
            self.logger.exception(f"❌ Error en MLService.evaluate_and_log: {e}")
            return None

    def update_execution_outcome(
        self,
        decision_id: Optional[str],
        executed: int,
        trade_type: Optional[str],
        trade_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        if not self.enabled or not decision_id:
            return
        self.decision_logger.update_execution_outcome(
            decision_id=decision_id,
            executed=executed,
            trade_type=trade_type,
            trade_id=trade_id,
            reason=reason,
        )

    def update_trade_outcome(
        self,
        decision_id: Optional[str],
        pnl: Optional[float],
        target: Optional[int],
        r_multiple: Optional[float],
        exit_type: Optional[str],
    ) -> None:
        if not self.enabled or not decision_id:
            return
        self.decision_logger.update_trade_outcome(
            decision_id=decision_id,
            pnl=pnl,
            target=target,
            r_multiple=r_multiple,
            exit_type=exit_type,
        )
