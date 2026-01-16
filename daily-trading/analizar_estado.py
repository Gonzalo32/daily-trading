"""Script para analizar el estado actual del sistema"""
import pandas as pd
import os
from pathlib import Path

print("=" * 60)
print("📊 ANÁLISIS DEL ESTADO DEL SISTEMA")
print("=" * 60)

# 1. Estado de training_data.csv
training_file = "src/ml/training_data.csv"
if os.path.exists(training_file):
    df = pd.read_csv(training_file)
    total_trades = len(df)
    if total_trades > 0:
        ganadores = len(df[df["target"] == 1])
        perdedores = len(df[df["target"] == 0])
        win_rate = (ganadores / total_trades * 100) if total_trades > 0 else 0
        
        print(f"\n✅ training_data.csv encontrado")
        print(f"   📈 Trades totales: {total_trades}")
        print(f"   ✅ Ganadores (target=1): {ganadores}")
        print(f"   ❌ Perdedores (target=0): {perdedores}")
        print(f"   📊 Win Rate: {win_rate:.1f}%")
    else:
        print(f"\n⚠️ training_data.csv existe pero está vacío")
        total_trades = 0
else:
    print(f"\n❌ training_data.csv NO existe")
    total_trades = 0

# 2. Estado para Machine Learning
print(f"\n🤖 ESTADO DE MACHINE LEARNING:")
print(f"   📋 Trades necesarios para ML básico: 50")
print(f"   📋 Trades necesarios para auto-trainer: 5000")
print(f"   📋 Trades necesarios para modo avanzado: 500")
print(f"   📈 Trades actuales: {total_trades}")

if total_trades < 50:
    faltan_basico = 50 - total_trades
    print(f"   ⏳ Faltan {faltan_basico} trades para ML básico")
elif total_trades < 500:
    faltan_avanzado = 500 - total_trades
    print(f"   ✅ ML básico disponible (faltan {faltan_avanzado} para modo avanzado)")
elif total_trades < 5000:
    faltan_autotrain = 5000 - total_trades
    print(f"   ✅ Modo avanzado disponible (faltan {faltan_autotrain} para auto-trainer)")
else:
    print(f"   ✅ Sistema completamente operativo para ML")

# 3. Racha de aciertos
if total_trades > 0:
    print(f"\n🔥 RACHA DE ACIERTOS:")
    # Calcular racha desde el final
    consecutive_wins = 0
    consecutive_losses = 0
    for i in range(len(df) - 1, -1, -1):
        if df.iloc[i]["target"] == 1:
            consecutive_wins += 1
            if consecutive_losses > 0:
                break
        else:
            consecutive_losses += 1
            if consecutive_wins > 0:
                break
    
    print(f"   🔥 Racha actual de ganancias: {consecutive_wins}")
    print(f"   ❄️ Racha actual de pérdidas: {consecutive_losses}")

# 4. Verificar archivos necesarios
print(f"\n📁 ARCHIVOS DEL SISTEMA:")
archivos_necesarios = [
    "src/data/market_data.py",
    "src/ml/trade_recorder.py",
    "src/metrics/metrics_collector.py",
    ".env",
    "logs",
    "models"
]

for archivo in archivos_necesarios:
    existe = os.path.exists(archivo) or os.path.isdir(archivo)
    estado = "✅" if existe else "❌"
    print(f"   {estado} {archivo}")

print("\n" + "=" * 60)
