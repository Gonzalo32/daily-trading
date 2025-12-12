from pathlib import Path
import pandas as pd
from ml_model import TradingMLModel

DATA_FILE = Path("src/ml/training_data.csv")


def main():
    if not DATA_FILE.exists():
        print(f"❌ No se encontró {DATA_FILE}")
        return

    df = pd.read_csv(DATA_FILE)
    if "target" not in df.columns:
        print("❌ El dataset no tiene columna 'target'")
        return

    print(f"📦 Filas en dataset: {len(df)}")

    # Separar train/test simple (hold-out)
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    split = int(len(df) * 0.8)
    train_df = df.iloc[:split].copy()
    test_df = df.iloc[split:].copy()

    print(f"🧪 Train: {len(train_df)} | Test: {len(test_df)}")

    # Entrenar modelo temporalmente para diagnóstico
    model = TradingMLModel(min_probability=0.55)
    model.train(train_df, target_col="target")

    # Evaluar
    metrics = model.evaluate(test_df, target_col="target")

    print("📊 Métricas del modelo:")
    for k, v in metrics.items():
        print(f" - {k}: {v}")


if __name__ == "__main__":
    main()
