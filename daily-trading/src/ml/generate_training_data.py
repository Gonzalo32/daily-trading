import pandas as pd
import numpy as np
from datetime import datetime, timedelta

                                              
num_rows = 200
start_date = datetime.now() - timedelta(days=num_rows)
timestamps = [start_date + timedelta(days=i) for i in range(num_rows)]

                                     
np.random.seed(42)
price = np.cumsum(np.random.randn(num_rows) * 2 + 100)
open_prices = price + np.random.randn(num_rows)
high_prices = open_prices + abs(np.random.rand(num_rows) * 5)
low_prices = open_prices - abs(np.random.rand(num_rows) * 5)
close_prices = price + np.random.randn(num_rows)
volume = np.random.randint(100, 1000, size=num_rows)

                                
fast_ma = pd.Series(close_prices).rolling(window=5).mean().fillna(method='bfill')
slow_ma = pd.Series(close_prices).rolling(window=15).mean().fillna(method='bfill')
rsi = np.random.uniform(30, 70, size=num_rows)
macd = fast_ma - slow_ma
macd_signal = pd.Series(macd).ewm(span=9, adjust=False).mean().fillna(method='bfill')
atr = np.random.uniform(0.5, 3.0, size=num_rows)

                                                                        
labels = np.random.choice([0, 1], size=num_rows)

                 
df = pd.DataFrame({
    "timestamp": timestamps,
    "open": open_prices,
    "high": high_prices,
    "low": low_prices,
    "close": close_prices,
    "volume": volume,
    "fast_ma": fast_ma,
    "slow_ma": slow_ma,
    "rsi": rsi,
    "macd": macd,
    "macd_signal": macd_signal,
    "atr": atr,
    "label": labels
})

df.to_csv("training_data.csv", index=False)
print("✅ training_data.csv creado exitosamente.")
