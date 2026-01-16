# -*- coding: utf-8 -*-
import pandas as pd
import os

training_file = "src/ml/training_data.csv"

if os.path.exists(training_file):
    df = pd.read_csv(training_file)
    total = len(df)
    if total > 0:
        wins = len(df[df["target"] == 1])
        losses = len(df[df["target"] == 0])
        wr = wins / total * 100
        
        print(f"Trades totales: {total}")
        print(f"Ganadores: {wins}")
        print(f"Perdedores: {losses}")
        print(f"Win Rate: {wr:.1f}%")
        
        # Racha
        cw = 0
        cl = 0
        for i in range(len(df)-1, -1, -1):
            if df.iloc[i]["target"] == 1:
                cw += 1
                if cl > 0:
                    break
            else:
                cl += 1
                if cw > 0:
                    break
        
        print(f"Racha ganancias: {cw}")
        print(f"Racha perdidas: {cl}")
        
        # Estado ML
        print(f"\nML Basico (50): {'OK' if total >= 50 else f'Faltan {50-total}'}")
        print(f"Modo Avanzado (500): {'OK' if total >= 500 else f'Faltan {500-total}'}")
        print(f"Auto-Trainer (5000): {'OK' if total >= 5000 else f'Faltan {5000-total}'}")
    else:
        print("Archivo vacio")
else:
    print("Archivo no existe")
