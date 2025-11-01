import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


class TradingMLModel:
    def __init__(self, model_path: str = "models/model.pkl"):
        self.model_path = model_path
        self.model = None

    def train(self, df: pd.DataFrame, target_col: str = "target"):
        if target_col not in df.columns:
            raise ValueError(f"Columna de objetivo '{target_col}' no encontrada en los datos.")

        X = df.drop(columns=[target_col])
        y = df[target_col]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        print("📊 Evaluación del modelo:\n", classification_report(y_test, y_pred))

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        print(f"✅ Modelo guardado en {self.model_path}")

    def load_model(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Modelo no encontrado en {self.model_path}")
        self.model = joblib.load(self.model_path)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            self.load_model()
        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            self.load_model()
        return self.model.predict_proba(X)
