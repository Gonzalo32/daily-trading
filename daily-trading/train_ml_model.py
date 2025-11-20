"""
Script para entrenar el modelo ML de filtrado de señales
Ejecutar periódicamente (ej: cada semana) para mejorar el modelo
"""

import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
from datetime import datetime

def load_training_data(csv_path: str = "src/ml/trading_history.csv") -> pd.DataFrame:
    """Cargar datos de entrenamiento desde CSV"""
    if not os.path.exists(csv_path):
        print(f"❌ No se encontró el archivo de datos: {csv_path}")
        print("ℹ️ El bot debe haber ejecutado al menos algunas operaciones para generar datos")
        return None
    
    df = pd.read_csv(csv_path)
    print(f"✅ Datos cargados: {len(df)} operaciones registradas")
    return df

def prepare_features(df: pd.DataFrame) -> tuple:
    """Preparar features y target para entrenamiento"""
    
    # Features que usará el modelo (mismas que en MLSignalFilter)
    feature_columns = [
        # Técnicos
        'rsi', 'macd', 'macd_signal', 'fast_ma', 'slow_ma', 'atr',
        'ma_diff_pct', 'rsi_normalized', 'macd_strength',
        # Contexto
        'volatility_normalized', 'volume_relative', 'hour_of_day',
        'regime_trending_bullish', 'regime_trending_bearish', 'regime_ranging',
        'regime_high_volatility', 'regime_low_volatility', 'regime_chaotic',
        # Estado del bot
        'daily_pnl_normalized', 'daily_trades', 'consecutive_signals',
        # Señal
        'signal_strength', 'signal_buy', 'signal_sell',
    ]
    
    # Verificar que todas las columnas existan
    missing_cols = [col for col in feature_columns if col not in df.columns]
    if missing_cols:
        print(f"⚠️ Columnas faltantes: {missing_cols}")
        # Rellenar con 0
        for col in missing_cols:
            df[col] = 0
    
    X = df[feature_columns].fillna(0)  # Rellenar NaN con 0
    
    # Target: usar 'target' binario (1 si alcanzó al menos 1R)
    y = df['target'].fillna(0).astype(int)
    
    print(f"✅ Features preparadas: {X.shape}")
    print(f"   - Win rate en datos: {y.mean():.2%}")
    
    return X, y, feature_columns

def train_model(X, y, model_type='random_forest'):
    """Entrenar modelo ML"""
    
    print(f"\n🤖 Entrenando modelo: {model_type}...")
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"   - Train set: {len(X_train)} muestras")
    print(f"   - Test set: {len(X_test)} muestras")
    
    # Seleccionar modelo
    if model_type == 'random_forest':
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced'  # Importante para datos desbalanceados
        )
    elif model_type == 'gradient_boosting':
        model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
    else:
        raise ValueError(f"Modelo no soportado: {model_type}")
    
    # Entrenar
    model.fit(X_train, y_train)
    
    # Evaluar
    print("\n📊 Evaluación del modelo:")
    print("=" * 60)
    
    # Predicciones
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    y_proba_test = model.predict_proba(X_test)[:, 1]
    
    # Métricas de train
    train_score = model.score(X_train, y_train)
    print(f"✅ Accuracy en TRAIN: {train_score:.2%}")
    
    # Métricas de test
    test_score = model.score(X_test, y_test)
    print(f"✅ Accuracy en TEST: {test_score:.2%}")
    
    # ROC AUC
    try:
        roc_auc = roc_auc_score(y_test, y_proba_test)
        print(f"✅ ROC AUC Score: {roc_auc:.3f}")
    except:
        print("⚠️ No se pudo calcular ROC AUC (probablemente solo una clase en test)")
    
    # Classification report
    print("\n📋 Classification Report (TEST):")
    print(classification_report(y_test, y_pred_test, target_names=['Malo', 'Bueno']))
    
    # Confusion matrix
    print("\n🔢 Confusion Matrix (TEST):")
    cm = confusion_matrix(y_test, y_pred_test)
    print(cm)
    print(f"   - True Negatives: {cm[0][0]}")
    print(f"   - False Positives: {cm[0][1]}")
    print(f"   - False Negatives: {cm[1][0]}")
    print(f"   - True Positives: {cm[1][1]}")
    
    # Feature importance
    print("\n🔝 Top 10 Features más importantes:")
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(feature_importance.head(10).to_string(index=False))
    
    # Cross-validation
    print("\n🔄 Cross-validation (5-fold):")
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
    print(f"   - CV Scores: {cv_scores}")
    print(f"   - CV Mean: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
    
    return model, test_score

def save_model(model, model_path: str = "models/signal_filter_model.pkl"):
    """Guardar modelo entrenado"""
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    print(f"\n✅ Modelo guardado en: {model_path}")
    
    # Guardar metadata
    metadata = {
        'training_date': datetime.now().isoformat(),
        'model_type': type(model).__name__,
    }
    metadata_path = model_path.replace('.pkl', '_metadata.joblib')
    joblib.dump(metadata, metadata_path)
    print(f"✅ Metadata guardada en: {metadata_path}")

def main():
    """Función principal de entrenamiento"""
    print("=" * 60)
    print("🤖 ENTRENAMIENTO DE MODELO ML - FILTRO DE SEÑALES")
    print("=" * 60)
    
    # 1. Cargar datos
    print("\n📥 Paso 1: Cargar datos de trading...")
    df = load_training_data()
    
    if df is None or len(df) < 50:
        print("\n❌ No hay suficientes datos para entrenar el modelo")
        print("ℹ️ Se necesitan al menos 50 operaciones registradas")
        print("ℹ️ Ejecuta el bot por un tiempo para generar datos de entrenamiento")
        return
    
    # 2. Preparar features
    print("\n🔧 Paso 2: Preparar features...")
    X, y, feature_columns = prepare_features(df)
    
    # 3. Entrenar modelo
    print("\n🎯 Paso 3: Entrenar modelo...")
    model, test_score = train_model(X, y, model_type='random_forest')
    
    # 4. Guardar modelo
    print("\n💾 Paso 4: Guardar modelo...")
    save_model(model)
    
    print("\n" + "=" * 60)
    print("✅ ENTRENAMIENTO COMPLETADO")
    print("=" * 60)
    print(f"📊 Accuracy final: {test_score:.2%}")
    print("ℹ️ El modelo estará activo en la próxima ejecución del bot")
    print("ℹ️ Se recomienda re-entrenar el modelo cada 1-2 semanas con nuevos datos")

if __name__ == "__main__":
    main()

