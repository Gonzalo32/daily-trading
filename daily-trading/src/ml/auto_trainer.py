import os
import json
from typing import Dict, Any

import pandas as pd

from src.utils.logging_setup import setup_logging
from src.ml.ml_model import TradingMLModel

DATA_FILE = "src/ml/training_data.csv"
METADATA_FILE = "models/training_metadata.json"

MIN_ROWS = 5_000         # mínimo absoluto para entrenar
MIN_DELTA_ROWS = 2_000   # entrenar solo si hay 2000 filas nuevas


logger = setup_logging(__name__)


def load_metadata() -> Dict[str, Any]:
    if not os.path.exists(METADATA_FILE):
        return {"last_trained_rows": 0}
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_trained_rows": 0}


def save_metadata(meta: Dict[str, Any]):
    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def auto_train_if_needed() -> bool:
    """
    Re-entrena el modelo solo si hay suficientes datos nuevos.
    Devuelve True si entrenó, False si no hizo nada.
    """
    if not os.path.exists(DATA_FILE):
        logger.warning(f"⚠️ No existe {DATA_FILE}, nada para entrenar.")
        return False

    df = pd.read_csv(DATA_FILE)
    n_rows = len(df)

    if n_rows < MIN_ROWS:
        logger.info(
            f"📉 Datos insuficientes para entrenar. "
            f"Tengo {n_rows}, necesito al menos {MIN_ROWS}."
        )
        return False

    meta = load_metadata()
    last_trained_rows = meta.get("last_trained_rows", 0)
    delta = n_rows - last_trained_rows

    if delta < MIN_DELTA_ROWS:
        logger.info(
            f"⏸ Aún no se alcanzó el umbral de nuevas filas. "
            f"Nuevas filas: {delta}, mínimo requerido: {MIN_DELTA_ROWS}."
        )
        return False

    logger.info(
        f"🚀 Re-entrenando modelo ML con {n_rows} filas "
        f"(+{delta} nuevas desde el último entrenamiento)..."
    )

    model = TradingMLModel()
    model.train(df, target_col="target")

    meta["last_trained_rows"] = n_rows
    save_metadata(meta)

    logger.info("✅ Re-entrenamiento completado y metadata actualizada.")
    return True


def main():
    auto_train_if_needed()


if __name__ == "__main__":
    main()
