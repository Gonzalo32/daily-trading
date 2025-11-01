
import pandas as pd
from ml_model import TradingMLModel

# Reemplaza esto por tu fuente real de datos
df = pd.read_csv("src/ml/training_data.csv")

# La columna target debe estar definida (0: no comprar, 1: comprar, por ejemplo)
model = TradingMLModel()
model.train(df, target_col="target")
