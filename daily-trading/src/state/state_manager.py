"""
StateManager
Persistencia mínima del estado del bot (PAPER).
"""

import json
import os
from datetime import datetime
from typing import Dict, Any


class StateManager:
    """Gestor de persistencia del estado del bot"""
    
    def __init__(self, path: str = "state.json"):
        self.path = path

    def load(self) -> Dict[str, Any]:
        """Carga el estado desde disco"""
        if not os.path.exists(self.path):
            return {}

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self, state: Dict[str, Any]) -> None:
        """Guarda el estado a disco"""
        state["last_saved_at"] = datetime.utcnow().isoformat()

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
