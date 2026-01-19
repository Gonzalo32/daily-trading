
import pandas as pd
from src.ml.ml_model import TradingMLModel

                                                
model = TradingMLModel()
model.load_model()

df = pd.read_csv("data/test_data.csv")
X = df.drop(columns=["target"])
y = df["target"]

preds = model.predict(X)
df["prediction"] = preds
print(df[["prediction", "target"]].head(10))
