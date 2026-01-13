# 🚀 ENTRYPOINT OFICIAL DEL BOT

## ✅ Entrypoint Único Definido

**Archivo:** `daily-trading/main.py`

Este es el **ÚNICO** punto de entrada oficial para ejecutar el bot de trading.

---

## 📁 Estructura Confirmada

```
C:\Users\gonza\OneDrive\Desktop\daily-trading\
├── daily-trading/              ← Directorio principal del bot
│   ├── main.py                 ← ⭐ ENTRYPOINT OFICIAL
│   ├── config.py               ← Configuración
│   ├── src/                    ← Código fuente
│   │   ├── data/
│   │   ├── strategy/
│   │   ├── risk/
│   │   ├── execution/
│   │   ├── ml/
│   │   └── ...
│   ├── logs/                   ← Logs del bot
│   ├── models/                 ← Modelos ML
│   └── venv/                   ← Virtualenv (opcional)
├── start.bat                   ← Script de inicio (ejecuta daily-trading/main.py)
├── tools/                      ← Scripts de utilidad
└── diagnostics/                ← Reportes de diagnóstico
```

---

## 🎯 Comando de Ejecución

### Opción 1: Script BAT (Recomendado para Windows)

```batch
# Desde la raíz del proyecto
start.bat
```

**Qué hace:**
1. Activa virtualenv (si existe)
2. Cambia a `daily-trading/`
3. Ejecuta `python main.py`
4. Desactiva virtualenv al finalizar

---

### Opción 2: Manual (PowerShell/CMD)

```powershell
# Desde la raíz del proyecto
cd daily-trading
python main.py
```

**O con virtualenv:**

```powershell
# Desde la raíz del proyecto
.\venv\Scripts\activate          # Activar venv (si existe)
cd daily-trading
python main.py
```

---

## ⚠️ Otros Archivos Python (NO son el entrypoint)

Estos archivos tienen `if __name__ == "__main__"` pero **NO** son el entrypoint del bot:

| Archivo | Propósito | Cuándo usar |
|---------|-----------|-------------|
| `backtest.py` | Backtesting | `python backtest.py --start-date 2023-01-01` |
| `monitor.py` | Monitoreo | `python monitor.py` |
| `quick_start.py` | Setup inicial | `python quick_start.py` |
| `run_pipeline.py` | Pipeline ML | `python run_pipeline.py` |
| `setup.py` | Instalación | `python setup.py` |
| `src/ml/auto_trainer.py` | Entrenamiento ML | `python -m src.ml.auto_trainer` |
| `src/ml/train_ml_model.py` | Entrenamiento manual | `python -m src.ml.train_ml_model` |
| `src/ml/stats_dashboard.py` | Dashboard stats | `python -m src.ml.stats_dashboard` |

**Estos son utilidades auxiliares, NO el bot principal.**

---

## 🔧 Scripts BAT Actualizados

| Script | Ubicación | Función |
|--------|-----------|---------|
| **`start.bat`** | Raíz | ⭐ Script principal - Ejecuta `daily-trading/main.py` |
| `run.bat` | Raíz | Alias de `start.bat` |
| `quick.bat` | Raíz | Acceso rápido |
| `daily-trading/start.bat` | Dentro de daily-trading | Script local (desde dentro de la carpeta) |

**Todos ejecutan el mismo entrypoint:** `daily-trading/main.py`

---

## ✅ Verificación

Para confirmar que el entrypoint funciona:

```powershell
# Test de import
cd daily-trading
python -c "import main; print('✅ Import OK')"

# Test de ejecución (debería iniciar el bot)
python main.py
```

**Output esperado:**
```
🚀 Iniciando Bot de Day Trading Avanzado...
============================================================
...
✅ Componentes inicializados correctamente
🔄 Iniciando bucle principal de trading...
```

---

## 🚨 Si el Bot No Inicia

### Problema 1: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'src'
```

**Solución:** Asegurate de estar en `daily-trading/`:

```powershell
cd daily-trading
python main.py
```

---

### Problema 2: No se encuentra main.py

```
❌ Error: No se encontró daily-trading\main.py
```

**Solución:** Ejecutá desde la raíz del proyecto:

```powershell
cd C:\Users\gonza\OneDrive\Desktop\daily-trading
start.bat
```

---

### Problema 3: joblib no instalado

```
ModuleNotFoundError: No module named 'joblib'
```

**Solución:** Instalar dependencias:

```powershell
cd daily-trading
pip install -r requirements.txt
```

---

## 📊 Logs

El bot guarda logs en:

```
daily-trading/logs/trading_bot.log
```

Para ver los últimos logs:

```powershell
Get-Content daily-trading\logs\trading_bot.log -Tail 50
```

---

## 🎯 Resumen

**Entrypoint:** `daily-trading/main.py`  
**Comando:** `start.bat` (desde raíz) o `python main.py` (desde daily-trading/)  
**Modo:** PAPER trading (sin dinero real)  
**Logs:** `daily-trading/logs/trading_bot.log`

---

**Última actualización:** 12 enero 2026  
**Commit que definió el entrypoint:** [Estabilización y limpieza]
