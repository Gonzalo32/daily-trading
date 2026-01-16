# -*- coding: utf-8 -*-
"""
Script para corregir automáticamente training_data.csv
"""
import csv
import os
import pandas as pd
import shutil
from pathlib import Path

CSV_FILE = "src/ml/training_data.csv"
BACKUP_FILE = "src/ml/training_data.csv.backup"

# Columnas esperadas según trade_recorder.py
EXPECTED_COLUMNS = [
    "timestamp", "symbol", "side",
    "entry_price", "exit_price", "pnl",
    "size", "stop_loss", "take_profit",
    "duration_seconds",
    "risk_amount", "atr_value", "r_value",
    "target"
]

def fix_csv():
    """Corrige el CSV automáticamente"""
    print("=" * 60)
    print("CORRIGIENDO training_data.csv")
    print("=" * 60)
    
    if not os.path.exists(CSV_FILE):
        print(f"ERROR: {CSV_FILE} no existe")
        return False
    
    # Hacer backup
    if os.path.exists(CSV_FILE):
        shutil.copy2(CSV_FILE, BACKUP_FILE)
        print(f"Backup creado: {BACKUP_FILE}")
    
    # Leer todas las líneas
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Total de lineas leidas: {len(lines)}")
    
    # Identificar líneas con formato nuevo (14 columnas)
    new_format_lines = []
    old_format_lines = []
    
    for i, line in enumerate(lines):
        fields = line.strip().split(',')
        if len(fields) == 14:
            new_format_lines.append((i, line))
        else:
            old_format_lines.append((i, line))
    
    print(f"Lineas con formato nuevo (14 cols): {len(new_format_lines)}")
    print(f"Lineas con formato viejo: {len(old_format_lines)}")
    
    if not new_format_lines:
        print("ERROR: No se encontraron lineas con formato nuevo")
        return False
    
    # Crear nuevo CSV con header correcto y solo líneas nuevas
    with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        # Escribir header correcto
        writer.writerow(EXPECTED_COLUMNS)
        
        # Escribir solo líneas con formato nuevo (sin el header viejo)
        for i, line in new_format_lines:
            if i == 0:  # Saltar el header viejo
                continue
            fields = line.strip().split(',')
            if len(fields) == 14:
                writer.writerow(fields)
    
    # Verificar con pandas
    try:
        df = pd.read_csv(CSV_FILE)
        print(f"\nCSV corregido exitosamente!")
        print(f"  Filas: {len(df)}")
        print(f"  Columnas: {len(df.columns)}")
        print(f"  Columnas: {list(df.columns)}")
        
        # Estadísticas básicas
        if 'target' in df.columns:
            wins = len(df[df['target'] == 1])
            losses = len(df[df['target'] == 0])
            print(f"\nEstadisticas:")
            print(f"  Ganadores: {wins}")
            print(f"  Perdedores: {losses}")
            if len(df) > 0:
                print(f"  Win Rate: {wins/len(df)*100:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"ERROR al verificar CSV: {e}")
        return False

if __name__ == "__main__":
    fix_csv()
