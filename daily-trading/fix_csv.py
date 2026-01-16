# -*- coding: utf-8 -*-
"""
Script para diagnosticar y corregir problemas en training_data.csv
"""
import csv
import os
import pandas as pd
from pathlib import Path

CSV_FILE = "src/ml/training_data.csv"
BACKUP_FILE = "src/ml/training_data.csv.backup"

def diagnose_csv():
    """Diagnostica problemas en el CSV"""
    print("=" * 60)
    print("DIAGNOSTICO DE training_data.csv")
    print("=" * 60)
    
    if not os.path.exists(CSV_FILE):
        print(f"ERROR: {CSV_FILE} no existe")
        return
    
    # Leer línea por línea para encontrar el problema
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Total de lineas: {len(lines)}")
    
    # Leer header
    if len(lines) > 0:
        header = lines[0].strip().split(',')
        print(f"Columnas esperadas (header): {len(header)}")
        print(f"Columnas: {header}")
    
    # Verificar cada línea
    problematic_lines = []
    for i, line in enumerate(lines[1:], start=2):  # Empezar desde línea 2 (después del header)
        fields = line.strip().split(',')
        if len(fields) != len(header):
            problematic_lines.append({
                'line_num': i,
                'expected': len(header),
                'found': len(fields),
                'content': line[:100]  # Primeros 100 caracteres
            })
    
    if problematic_lines:
        print(f"\nPROBLEMAS ENCONTRADOS: {len(problematic_lines)} lineas")
        for prob in problematic_lines:
            print(f"  Linea {prob['line_num']}: Esperadas {prob['expected']} columnas, encontradas {prob['found']}")
            print(f"    Contenido: {prob['content']}")
    else:
        print("\nNo se encontraron problemas de formato")
    
    return problematic_lines

def fix_csv():
    """Corrige el CSV eliminando líneas problemáticas"""
    print("\n" + "=" * 60)
    print("CORRIGIENDO CSV")
    print("=" * 60)
    
    # Hacer backup
    if os.path.exists(CSV_FILE):
        import shutil
        shutil.copy2(CSV_FILE, BACKUP_FILE)
        print(f"Backup creado: {BACKUP_FILE}")
    
    # Leer CSV con pandas usando error_bad_lines (deprecated) o on_bad_lines
    try:
        # Intentar leer con pandas, ignorando líneas mal formadas
        df = pd.read_csv(CSV_FILE, on_bad_lines='skip', encoding='utf-8')
        print(f"CSV leido correctamente: {len(df)} filas")
        
        # Columnas esperadas
        expected_cols = [
            "timestamp", "symbol", "side",
            "entry_price", "exit_price", "pnl",
            "size", "stop_loss", "take_profit",
            "duration_seconds",
            "risk_amount", "atr_value", "r_value",
            "target"
        ]
        
        # Verificar columnas
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            print(f"ADVERTENCIA: Faltan columnas: {missing_cols}")
        
        # Limpiar datos
        # Eliminar filas con valores nulos críticos
        initial_len = len(df)
        df = df.dropna(subset=['entry_price', 'exit_price', 'pnl', 'target'])
        
        # Asegurar que target sea 0 o 1
        df['target'] = df['target'].astype(int).clip(0, 1)
        
        # Guardar CSV corregido
        df.to_csv(CSV_FILE, index=False, encoding='utf-8')
        print(f"CSV corregido y guardado: {len(df)} filas (se eliminaron {initial_len - len(df)} filas problemáticas)")
        
        return True
        
    except Exception as e:
        print(f"ERROR al corregir: {e}")
        # Intentar método alternativo: leer línea por línea
        return fix_csv_manual()

def fix_csv_manual():
    """Corrige el CSV manualmente línea por línea"""
    print("\nIntentando correccion manual...")
    
    if not os.path.exists(CSV_FILE):
        return False
    
    # Leer todas las líneas
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        return False
    
    # Header
    header = lines[0].strip().split(',')
    expected_cols = len(header)
    
    # Filtrar líneas válidas
    valid_lines = [lines[0]]  # Header
    removed = 0
    
    for i, line in enumerate(lines[1:], start=2):
        fields = line.strip().split(',')
        # Si tiene el número correcto de campos o está muy cerca, intentar arreglarlo
        if len(fields) == expected_cols:
            valid_lines.append(line)
        elif len(fields) == expected_cols + 1:
            # Probablemente hay una coma extra, intentar unir los dos últimos campos
            # o eliminar el último si es vacío
            if fields[-1].strip() == '':
                fields = fields[:-1]
                valid_lines.append(','.join(fields) + '\n')
            else:
                # Unir los dos últimos campos
                fields[-2] = fields[-2] + fields[-1]
                fields = fields[:-1]
                valid_lines.append(','.join(fields) + '\n')
        elif len(fields) == expected_cols - 1:
            # Faltan campos, agregar valores por defecto
            while len(fields) < expected_cols:
                fields.append('')
            valid_lines.append(','.join(fields) + '\n')
        else:
            removed += 1
            print(f"  Eliminando linea {i}: {len(fields)} campos (esperados {expected_cols})")
    
    # Escribir CSV corregido
    with open(CSV_FILE, 'w', encoding='utf-8') as f:
        f.writelines(valid_lines)
    
    print(f"CSV corregido: {len(valid_lines)-1} lineas validas, {removed} eliminadas")
    return True

if __name__ == "__main__":
    # Diagnosticar
    problems = diagnose_csv()
    
    # Corregir si hay problemas
    if problems:
        print("\n" + "=" * 60)
        response = input("¿Desea corregir el CSV? (s/n): ")
        if response.lower() == 's':
            fix_csv()
        else:
            print("Correccion cancelada")
    else:
        print("\nEl CSV parece estar bien. Verificando con pandas...")
        try:
            df = pd.read_csv(CSV_FILE)
            print(f"CSV valido: {len(df)} filas, {len(df.columns)} columnas")
        except Exception as e:
            print(f"ERROR al leer con pandas: {e}")
            print("Intentando corregir...")
            fix_csv()
