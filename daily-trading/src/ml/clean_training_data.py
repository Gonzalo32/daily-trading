import pandas as pd

def clean_training_data(path="src/ml/training_data.csv"):
    df = pd.read_csv(path)

                                     
    df = df.dropna()

                                                    
    df = df[df["size"] > 0]
    df = df[df["entry_price"] > 0]
    df = df[df["exit_price"] > 0]

                                              
    df["target"] = df["target"].apply(lambda x: 1 if float(x) >= 1 else 0)

                               
    df = df[df["pnl"].abs() < df["r_value"].abs() * 20]                     

    df.to_csv(path, index=False)
    print("🧹 Dataset limpiado y guardado.")
    return df


if __name__ == "__main__":
    clean_training_data()
