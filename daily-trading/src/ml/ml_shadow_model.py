from typing import Dict, Any


class ShadowMLModel:
    """
    Modelo stub para shadow mode.
    Devuelve un score neutro o ligeramente sesgado por RSI si existe.
    """

    def __init__(self, model_version: str, feature_version: str):
        self.model_version = model_version
        self.feature_version = feature_version

    def predict_proba(self, features: Dict[str, Any]) -> float:
        rsi_normalized = features.get("rsi_normalized")
        if rsi_normalized is None:
            return 0.5

        try:
            rsi_val = float(rsi_normalized)
        except (ValueError, TypeError):
            return 0.5

        score = 0.5 + (0.1 * rsi_val)
        if score < 0.0:
            return 0.0
        if score > 1.0:
            return 1.0
        return score

    def predict(self, features: Dict[str, Any]) -> int:
        return 1 if self.predict_proba(features) >= 0.5 else 0
