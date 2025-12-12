import pandas as pd

def clean_training_data(path="src/ml/training_data.csv"):
    df = pd.read_csv(path)

    # Quitar filas vacías o corruptas
    df = df.dropna()

    # Remove trades con tamaño 0 o precios inválidos
    df = df[df["size"] > 0]
    df = df[df["entry_price"] > 0]
    df = df[df["exit_price"] > 0]

    # Convertir target a 0/1 por si quedó raro
    df["target"] = df["target"].apply(lambda x: 1 if float(x) >= 1 else 0)

    # Limitar outliers absurdos
    df = df[df["pnl"].abs() < df["r_value"].abs() * 20]  # trades imposibles

    df.to_csv(path, index=False)
    print("🧹 Dataset limpiado y guardado.")
    return df


if __name__ == "__main__":
    clean_training_data()
