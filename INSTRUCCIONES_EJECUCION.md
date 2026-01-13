# 🚀 INSTRUCCIONES DE EJECUCIÓN - Bot de Trading

## ✅ Estado: BOT ESTABILIZADO Y LISTO

**Fecha:** 12 enero 2026  
**Cambios aplicados:** Limpieza de imports, entrypoint único, robustez MLSignalFilter

---

## 📋 PASO 1: Preparar Entorno

### 1.1 Verificar Ubicación

```powershell
# Asegurarse de estar en la raíz del proyecto
cd C:\Users\gonza\OneDrive\Desktop\daily-trading

# Verificar estructura
dir
```

**Debes ver:**
```
daily-trading\  ← Carpeta principal del bot
tools\
diagnostics\
start.bat
...
```

---

### 1.2 Crear/Activar Virtualenv (Recomendado)

```powershell
# Opción A: Crear nuevo virtualenv en la raíz
python -m venv venv

# Opción B: O crear dentro de daily-trading/
cd daily-trading
python -m venv venv
cd ..
```

**Activar virtualenv:**

```powershell
# Si está en la raíz
.\venv\Scripts\activate

# Si está en daily-trading/
.\daily-trading\venv\Scripts\activate
```

**Verificar activación:**
```powershell
# Debe aparecer (venv) al inicio del prompt
(venv) PS C:\Users\gonza\OneDrive\Desktop\daily-trading>
```

---

### 1.3 Instalar Dependencias

```powershell
# Con virtualenv activado
cd daily-trading
pip install -r requirements.txt
```

**Dependencias principales:**
- pandas, numpy
- ccxt (exchange)
- scikit-learn, joblib (ML)
- fastapi, uvicorn (API)
- python-dotenv

**Verificar instalación:**

```powershell
python -m pip check
```

Debe decir: `No broken requirements found.`

---

## 📋 PASO 2: Configurar Bot (Opcional)

### 2.1 Archivo .env (Opcional)

Crear `daily-trading/.env` con tus configuraciones:

```env
# Modo de trading
TRADING_MODE=PAPER
MARKET=CRYPTO
SYMBOL=BTC/USDT
TIMEFRAME=5m

# API Keys (opcional en PAPER mode)
BINANCE_API_KEY=
BINANCE_SECRET_KEY=
BINANCE_TESTNET=true

# Configuración de riesgo
INITIAL_CAPITAL=10000
RISK_PER_TRADE=0.02
MAX_DAILY_LOSS=0.03
MAX_DAILY_TRADES=200

# Debugging
ENABLE_DEBUG_STRATEGY=false
ENABLE_ML=false
MVP_MODE_ENABLED=true

# Dashboard
ENABLE_DASHBOARD=true
DASHBOARD_PORT=8000
```

**⚠️ IMPORTANTE:** `ENABLE_DEBUG_STRATEGY=false` para producción

---

### 2.2 Verificar Configuración

```powershell
cd daily-trading
python -c "from config import Config; c = Config(); print(f'Mode: {c.TRADING_MODE}, Market: {c.MARKET}, DEBUG: {c.ENABLE_DEBUG_STRATEGY}')"
```

**Output esperado:**
```
Mode: PAPER, Market: CRYPTO, DEBUG: False
```

---

## 📋 PASO 3: Ejecutar Bot

### Opción A: Script BAT (Recomendado)

```batch
# Desde la raíz del proyecto
start.bat
```

**Qué hace:**
1. ✅ Activa virtualenv (si existe)
2. ✅ Cambia a daily-trading/
3. ✅ Ejecuta python main.py
4. ✅ Muestra logs en consola

---

### Opción B: Manual

```powershell
# 1. Activar virtualenv
.\venv\Scripts\activate

# 2. Ir a daily-trading
cd daily-trading

# 3. Ejecutar bot
python main.py
```

---

## 📋 PASO 4: Verificar que Funciona

### 4.1 Output Esperado

Al ejecutar `start.bat` o `python main.py`, debes ver:

```
🚀 Iniciando Bot de Day Trading Avanzado...
============================================================
✅ Python 3.11.5 detectado
✅ Conexión con Binance establecida (modo testnet: True)
✅ Componentes inicializados correctamente

🚀 MODO MVP ACTIVADO
============================================================
📊 Trades históricos: 0 / 500
...
🔄 Iniciando bucle principal de trading...
💓 Bot activo | Iteración #1 | PnL: 0.00 | Trades: 0 | Posiciones: 0
```

---

### 4.2 Verificar Logs

```powershell
# Ver últimos logs
Get-Content daily-trading\logs\trading_bot.log -Tail 50

# Ver solo errores
Get-Content daily-trading\logs\trading_bot.log | Select-String "ERROR"
```

---

### 4.3 Detener Bot

```
Ctrl + C
```

**Output esperado:**
```
🛑 Interrupción del usuario
🛑 Deteniendo Bot de Day Trading...
✅ Bot detenido correctamente
```

---

## 🔧 Troubleshooting

### Problema 1: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'pandas'
```

**Solución:**
```powershell
# Activar virtualenv
.\venv\Scripts\activate

# Instalar dependencias
cd daily-trading
pip install -r requirements.txt
```

---

### Problema 2: Bot crashea al iniciar

```
ERROR: 'MLSignalFilter' object has no attribute 'is_model_available'
```

**Solución:** Ya está arreglado en esta versión. Si persiste:

```powershell
# Limpiar cache
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force

# Re-ejecutar
start.bat
```

---

### Problema 3: joblib not found

```
⚠️ joblib no está instalado. ML deshabilitado.
```

**Solución:**
```powershell
pip install joblib
```

O ignorar (ML funcionará en modo fallback sin crashear).

---

### Problema 4: Sin señales

```
💓 Bot activo | Iteración #50 | PnL: 0.00 | Trades: 0 | Posiciones: 0
```

**Es normal:** La estrategia es selectiva y solo genera señales cuando:
- EMA5 > EMA13 y RSI < 70 (BUY)
- EMA5 < EMA13 y RSI > 30 (SELL)

**Para ver análisis:**
```powershell
# Ver logs de análisis
Get-Content daily-trading\logs\trading_bot.log | Select-String "Analizando"
```

---

## 📊 Monitoreo

### Ver Métricas en Tiempo Real

```powershell
# PnL actual
Get-Content daily-trading\logs\trading_bot.log | Select-String "PnL" | Select-Object -Last 10

# Trades ejecutados
Get-Content daily-trading\logs\trading_bot.log | Select-String "Trade registrado" | Select-Object -Last 20

# Posiciones cerradas
Get-Content daily-trading\logs\trading_bot.log | Select-String "Posición cerrada"
```

---

### Dashboard Web (Opcional)

Si `ENABLE_DASHBOARD=true`:

```
http://localhost:8000
```

---

## 🎯 Resumen de Comandos

```powershell
# 1. Setup inicial (una sola vez)
cd C:\Users\gonza\OneDrive\Desktop\daily-trading
python -m venv venv
.\venv\Scripts\activate
cd daily-trading
pip install -r requirements.txt

# 2. Ejecutar bot (cada vez)
cd ..
start.bat

# 3. Ver logs
Get-Content daily-trading\logs\trading_bot.log -Tail 50

# 4. Detener bot
Ctrl + C
```

---

## ✅ Checklist Pre-Ejecución

Antes de ejecutar `start.bat`:

```
□ Virtualenv creado y activado
□ Dependencias instaladas (pip check OK)
□ Config verificado (DEBUG=false)
□ Estructura correcta (daily-trading/main.py existe)
□ Logs vacíos o limpiados
```

---

## 📞 Soporte

**Documentación:**
- `ENTRYPOINT.md` - Definición del entrypoint único
- `DIAGNOSTICO_TECNICO_COMPLETO.md` - Análisis exhaustivo
- `DIAGNOSTICO_RAPIDO.md` - Soluciones rápidas

**Logs:**
- `daily-trading/logs/trading_bot.log`

**Script de diagnóstico:**
```powershell
powershell -ExecutionPolicy Bypass -File tools\collect_diagnostics.ps1
```

---

**Última actualización:** 12 enero 2026  
**Versión:** Estabilizada y lista para paper trading 24/7
