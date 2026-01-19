import pandas as pd
from pathlib import Path

DATA_FILE = Path("src/ml/training_data.csv")


def main():
    if not DATA_FILE.exists():
        print(f"❌ No se encontró {DATA_FILE}")
        return

    df = pd.read_csv(DATA_FILE)
    print(f"📦 Filas totales: {len(df)}")

                
    dups = df.duplicated().sum()
    print(f"🔁 Filas duplicadas: {dups}")
    if dups > 0:
        df = df.drop_duplicates()
        print(f"✅ Duplicados eliminados. Nuevas filas: {len(df)}")

                                    
    before = len(df)
    df = df.dropna(subset=["pnl", "target"])
    print(f"🧹 Filas sin pnl/target eliminadas: {before - len(df)}")

                                 
    if "r_value" in df.columns:
        bad_target = ((df["pnl"] >= df["r_value"]) & (df["target"] == 0)) | \
                     ((df["pnl"] < df["r_value"]) & (df["target"] == 1))
        print(f"⚠️ Filas con target incoherente (según regla >= 1R): {bad_target.sum()}")

    df.to_csv(DATA_FILE, index=False)
    print("💾 Dataset validado y guardado de nuevo.")


if __name__ == "__main__":
    main()
