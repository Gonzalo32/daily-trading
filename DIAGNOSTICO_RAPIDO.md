# 🚑 DIAGNÓSTICO RÁPIDO

Guía de referencia rápida para diagnosticar problemas del bot.

---

## 🔧 Script de Diagnóstico Automático

### Ejecutar Diagnóstico Completo

```powershell
powershell -ExecutionPolicy Bypass -File tools\collect_diagnostics.ps1
```

**Output:** `diagnostics/REPORT.md`

**Qué verifica:**
- ✅ Python y virtualenv
- ✅ Dependencias y conflictos
- ✅ Imports (detecta `is_model_available` error)
- ✅ Entry points
- ✅ Datos ML (CSV)
- ✅ Errores de lint

---

## 🐛 Soluciones Rápidas a Problemas Comunes

### 1. Error: `'MLSignalFilter' object has no attribute 'is_model_available'`

**Causa:** Cache de Python desactualizado

**Solución:**

```powershell
# Limpiar cache
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force

# Verificar fix
python -c "from src.ml.ml_signal_filter import MLSignalFilter; f = MLSignalFilter(); print('OK:', f.is_model_available())"
```

---

### 2. Bot crashea al iniciar

**Diagnóstico rápido:**

```powershell
# 1. Verificar imports
python -c "import main; print('OK main')"
python -c "from src.ml.ml_signal_filter import MLSignalFilter; print('OK ML')"

# 2. Ver último error en logs
Get-Content .\daily-trading\logs\trading_bot.log -Tail 50
```

---

### 3. Estado se pierde al reiniciar

**Problema:** Equity vuelve a 10,000, PnL a 0

**Causa:** No hay persistencia implementada (ver DIAGNOSTICO_TECNICO_COMPLETO.md #2)

**Workaround temporal:**

```python
# En main.py, al inicio de __init__:
import json
try:
    with open('state.json', 'r') as f:
        state = json.load(f)
        self.config.INITIAL_CAPITAL = state['equity']
        self.daily_pnl = state['daily_pnl']
except FileNotFoundError:
    pass
```

---

### 4. Modo DEBUG activo (ignora filtros)

**Verificar:**

```powershell
python -c "from config import Config; print('DEBUG:', Config.ENABLE_DEBUG_STRATEGY)"
```

**Desactivar:**

En `.env` o `config.py`:
```
ENABLE_DEBUG_STRATEGY=false
```

---

### 5. training_data.csv vacío (0 trades)

**Verificar:**

```powershell
python -c "import pandas as pd; df = pd.read_csv('src/ml/training_data.csv'); print(f'Trades: {len(df)}')"
```

**Causa:** Bot nunca completó un trade

**Solución:** Correr bot en paper hasta que cierre 1 posición

---

### 6. Dashboard no funciona

**Verificar puerto:**

```powershell
netstat -ano | findstr :8000
```

**Verificar config:**

```python
python -c "from config import Config; print('Dashboard:', Config.ENABLE_DASHBOARD, 'Port:', Config.DASHBOARD_PORT)"
```

**Acceder:**

```
http://localhost:8000
```

---

### 7. Posiciones no se cierran (time stop)

**Verificar time stop:**

```powershell
# Ver logs de posiciones
Get-Content .\daily-trading\logs\trading_bot.log | Select-String "TIME STOP"
```

**Causa probable:** Posición abierta < 30 segundos

---

### 8. PnL desincronizado (diferente en logs)

**Verificar:**

```python
# En consola Python
from src.risk.risk_manager import RiskManager
from config import Config
rm = RiskManager(Config())
print("RiskManager PnL:", rm.state.daily_pnl)

# Comparar con logs
```

**Causa:** Duplicación de PnL (ver DIAGNOSTICO_TECNICO_COMPLETO.md #3)

---

## 📊 Comandos Útiles de Diagnóstico

### Ver últimos 50 logs

```powershell
Get-Content .\daily-trading\logs\trading_bot.log -Tail 50
```

### Ver solo errores

```powershell
Get-Content .\daily-trading\logs\trading_bot.log | Select-String "ERROR"
```

### Ver señales generadas hoy

```powershell
$today = Get-Date -Format "yyyy-MM-dd"
Get-Content .\daily-trading\logs\trading_bot.log | Select-String "$today" | Select-String "Señal generada"
```

### Ver posiciones cerradas con PnL

```powershell
Get-Content .\daily-trading\logs\trading_bot.log | Select-String "Posición cerrada" | Select-String "PnL"
```

### Contar trades en CSV

```powershell
python -c "import pandas as pd; df = pd.read_csv('src/ml/training_data.csv'); print(f'Total trades: {len(df)}')"
```

### Ver estado de MetricsCollector

```powershell
python -c "import sqlite3; conn = sqlite3.connect('data/metrics.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM trades'); print('Trades en DB:', cursor.fetchone()[0])"
```

---

## 🔍 Checklist de Verificación Pre-Ejecución

**Antes de correr el bot en paper 24/7:**

```
□ Cache limpio (__pycache__ eliminado)
□ Imports OK (script diagnóstico pasa)
□ DEBUG = false
□ ENABLE_ML = false (hasta tener 500 trades)
□ Logs rotando correctamente
□ training_data.csv existe (aunque vacío)
□ Sin conflictos de dependencias (pip check)
```

**Comando único:**

```powershell
.\tools\collect_diagnostics.ps1
```

Revisar `diagnostics/REPORT.md` para verificar todo OK.

---

## 📁 Estructura de Archivos Clave

```
daily-trading/
├── main.py                          ← Entrypoint principal
├── config.py                        ← Configuración (DEBUG aquí)
├── logs/trading_bot.log             ← Logs principales
├── src/ml/training_data.csv         ← Trades guardados
├── data/metrics.db                  ← Métricas (si MetricsCollector integrado)
├── models/model.pkl                 ← Modelo ML (si entrenado)
├── diagnostics/REPORT.md            ← Output script diagnóstico
└── tools/collect_diagnostics.ps1   ← Script diagnóstico
```

---

## 🆘 En Caso de Emergencia

### Bot perdiendo dinero rápido (LIVE)

```powershell
# 1. Detener bot inmediatamente
Ctrl+C

# 2. Verificar posiciones abiertas en exchange
# (Binance web / API)

# 3. Cerrar posiciones manualmente si es necesario

# 4. Generar diagnóstico
.\tools\collect_diagnostics.ps1

# 5. Revisar logs
Get-Content .\daily-trading\logs\trading_bot.log -Tail 200

# 6. NO reiniciar hasta identificar problema
```

---

### Bot no responde

```powershell
# 1. Verificar proceso
Get-Process | Where-Object {$_.ProcessName -like "*python*"}

# 2. Si está colgado, matar proceso
Stop-Process -Name python -Force

# 3. Verificar logs
Get-Content .\daily-trading\logs\trading_bot.log -Tail 100

# 4. Diagnóstico
.\tools\collect_diagnostics.ps1
```

---

## 📞 Contacto y Soporte

**Documentación completa:**
- `DIAGNOSTICO_TECNICO_COMPLETO.md` - Análisis técnico exhaustivo
- `RESUMEN_EJECUTIVO.md` - Resumen de estado
- `tools/README.md` - Documentación de scripts

**Logs:**
- `daily-trading/logs/trading_bot.log`
- `diagnostics/REPORT.md` (generado)
- `diagnostics/COMMANDS.log` (generado)

---

**Última actualización:** 12 enero 2026
