import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from src.utils.logging_setup import setup_logging

OUTPUT_FILE = "src/ml/training_data_synth.csv"
N_ROWS = 100_000  # cantidad de filas sintéticas a generar


def generate_synthetic_trades(n_rows: int = N_ROWS) -> pd.DataFrame:
    """
    Genera trades sintéticos compatibles con TradeRecorder / training_data.csv
    """

    rng = np.random.default_rng(seed=42)
    logger = setup_logging(__name__)

    # Timestamps distribuidos en los últimos 30 días
    now = datetime.utcnow()
    start_time = now - timedelta(days=30)
    timestamps = [
        start_time + timedelta(
            seconds=int(rng.uniform(0, 30 * 24 * 3600))
        )
        for _ in range(n_rows)
    ]

    # Siempre BTC/USDT por ahora
    symbols = np.array(["BTC/USDT"] * n_rows)

    # Lados BUY / SELL
    sides = rng.choice(["BUY", "SELL"], size=n_rows, p=[0.5, 0.5])

    # Precios de entrada alrededor de 90k +/- 10%
    base_price = 90_000
    entry_price = rng.normal(loc=base_price, scale=base_price * 0.05, size=n_rows)
    entry_price = np.clip(entry_price, base_price * 0.7, base_price * 1.3)

    # ATR ~ 0.5% del precio
    atr_value = entry_price * rng.uniform(0.003, 0.008, size=n_rows)

    # r_value = distancia de riesgo ≈ atr_value
    r_value = atr_value * rng.uniform(0.8, 1.2, size=n_rows)

    # Tamaño de posición: suponemos riesgo 2% de un capital aleatorio
    equity = rng.uniform(5_000, 20_000, size=n_rows)
    risk_amount = equity * 0.02
    size = risk_amount / r_value

    # Stop loss y take profit 1:1
    stop_loss = np.where(
        sides == "BUY",
        entry_price - r_value,
        entry_price + r_value
    )
    take_profit = np.where(
        sides == "BUY",
        entry_price + r_value,
        entry_price - r_value
    )

    # Duración entre 5s y 5 minutos
    duration_seconds = rng.uniform(5, 300, size=n_rows)

    # Generamos resultado de PnL en múltiplos de R
    # Mezcla de trades perdedores, pequeños ganadores y buenos ganadores
    r_multiple = rng.choice(
        [-1.0, -0.5, -0.25, 0.25, 0.5, 1.0, 2.0, 3.0],
        size=n_rows,
        p=[0.20, 0.10, 0.10, 0.15, 0.15, 0.15, 0.10, 0.05]
    )
    pnl = r_multiple * r_value  # PnL en dólares aproximado

    # Precio de salida consistente con el PnL
    exit_price = np.where(
        sides == "BUY",
        entry_price + pnl / size,
        entry_price - pnl / size
    )

    # Target: 1 si ganó al menos 1R
    target = (pnl >= r_value).astype(int)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "symbol": symbols,
        "side": sides,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl": pnl,
        "size": size,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "duration_seconds": duration_seconds,
        "risk_amount": risk_amount,
        "atr_value": atr_value,
        "r_value": r_value,
        "target": target,
    })

    logger.info(f"✅ Dataset sintético generado con {len(df)} filas")
    return df


def main():
    logger = setup_logging(__name__)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    df = generate_synthetic_trades(N_ROWS)
    df.to_csv(OUTPUT_FILE, index=False)

    logger.info(f"💾 Dataset sintético guardado en: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
