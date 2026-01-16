# 📚 Learning Mode - Modo de Aprendizaje en Tiempo Real

## 🎯 Objetivo

El **Learning Mode** es un sistema de entrenamiento en tiempo real diseñado para acumular datos de trading de calidad y entrenar modelos de Machine Learning que aprendan **estrategias generalizables**, no valores absolutos de precio.

## 🔄 Modos de Operación

### 🔴 LIVE Mode
- **Gestión de riesgo estricta**: Límites duros de pérdida diaria y cantidad de trades
- **Comportamiento conservador**: Bloquea trading cuando se alcanzan límites
- **Protección de capital**: Prioridad en preservar el capital real

### 🧪 PAPER Mode (Learning Mode)
- **❌ NO bloquea trading** por pérdida diaria
- **❌ NO bloquea trading** por cantidad diaria
- **✅ Mantiene stop loss por trade**: Protección individual por operación
- **✅ Mantiene riesgo por trade muy bajo**: Riesgo adaptativo progresivo
- **✅ Permite operar continuamente**: Para acumular cientos de trades diarios
- **✅ Prioriza calidad y diversidad de datos**: Dataset robusto para ML

## 🧠 Enfoque de Aprendizaje (CRÍTICO)

### Features Normalizadas/Relativas

El sistema de ML **NO usa valores absolutos de precio** como features principales. En su lugar, prioriza:

1. **Retornos porcentuales**: `((fast_ma - price) / price * 100)`
2. **Pendientes de EMA**: Diferencia relativa entre EMAs
3. **Distancia relativa a medias**: Normalizado por precio
4. **RSI normalizado**: `(rsi - 50) / 50` → rango -1 a 1
5. **Volatilidad relativa**: `(atr / price * 100)` → ATR como % del precio
6. **Contexto de mercado**: Tendencia (alcista/bajista) y fuerza

### Generalización

El modelo puede generalizar a:
- ✅ Otros activos
- ✅ Otros precios futuros
- ✅ Diferentes condiciones de mercado

## 📊 Generación Eficiente de Datos

### En Modo PAPER (Learning Mode)

1. **Alta frecuencia de decisiones**: Permite acumular cientos de trades diarios
2. **Cooldown mínimo configurable**: `MIN_COOLDOWN_BETWEEN_TRADES` (default: 5 segundos)
3. **Registro completo**:
   - ✅ Trades ejecutados (con contexto completo)
   - ✅ Señales rechazadas (por ML, riesgo, etc.)
   - ✅ Contexto cuando NO se opera (muestreo 1/20)

### Clasificación de Datos

El sistema registra tres tipos de eventos para entrenar clasificación:

1. **`trade_type: "executed"`**: Trade que se ejecutó
   - Target: `1` si ganó ≥ 1R, `0` si no
2. **`trade_type: "rejected_*"`**: Señal rechazada por filtros
   - Target: `0` (no se ejecutó)
   - Razón: `ml_filter`, `risk_manager`, etc.
3. **`trade_type: "no_signal"`**: Contexto sin señal generada
   - Target: `0` (no se operó)
   - Muestreo: 1 de cada 20 casos para balancear dataset

## 🧪 Gestión de Riesgo Adaptativa

### En Modo PAPER (Learning Mode)

**Si el rendimiento empeora:**
- Reducción progresiva del tamaño de posición (`risk_multiplier`)
- Aumento de confirmaciones requeridas
- **NUNCA detiene completamente el bot** (prioridad: seguir aprendiendo)

**Fórmula de reducción adaptativa:**
```python
loss_pct = abs(daily_pnl) / equity
reduction = min(0.8, loss_pct * 8.0)  # Máximo 80% de reducción
risk_multiplier = max(0.2, 1.0 - reduction)  # Mínimo 20% del riesgo normal
```

**Ejemplos:**
- Si perdemos 5% del equity → `risk_multiplier = 0.6` (60% del riesgo normal)
- Si perdemos 10% del equity → `risk_multiplier = 0.2` (20% del riesgo normal)

### En Modo LIVE

- Riesgo siempre al 100% (`risk_multiplier = 1.0`)
- Bloqueo estricto cuando se alcanzan límites

## 🔧 Configuración

### Variables de Entorno Clave

```bash
# Modo de trading
TRADING_MODE=PAPER  # PAPER = Learning Mode, LIVE = Producción

# Learning Mode (solo aplica en PAPER)
MIN_COOLDOWN_BETWEEN_TRADES=5.0  # Segundos entre trades (default: 5)

# Límites (en LIVE son duros, en PAPER son soft)
MAX_DAILY_TRADES=200  # En PAPER: límite soft, puede superarse
MAX_DAILY_LOSS=200.0  # En PAPER: límite soft, puede superarse

# Riesgo por trade (muy bajo en Learning Mode)
RISK_PER_TRADE=0.01  # 1% del capital por trade

# ML
ENABLE_ML=true
ML_MIN_PROBABILITY=0.55
```

## 📈 Features Registradas para ML

### Features Relativas (Prioritarias)

- `ema_fast_diff_pct`: Diferencia relativa EMA rápida vs precio (%)
- `ema_slow_diff_pct`: Diferencia relativa EMA lenta vs precio (%)
- `ema_cross_diff_pct`: Diferencia entre EMAs (%)
- `atr_pct`: ATR como porcentaje del precio
- `rsi_normalized`: RSI normalizado (-1 a 1)
- `macd_pct`: MACD relativo al precio (%)
- `trend_direction`: Dirección de tendencia (-1 bajista, +1 alcista)
- `trend_strength`: Fuerza de la tendencia (0-1)

### Features de Contexto

- `regime`: Régimen de mercado (trending, ranging, volatile, etc.)
- `volatility_level`: Nivel de volatilidad
- `daily_pnl_normalized`: PnL diario normalizado
- `consecutive_signals`: Señales consecutivas
- `daily_trades_normalized`: Trades diarios normalizados

### Features Básicas (Compatibilidad)

- `risk_amount`: Cantidad de riesgo en USD
- `atr_value`: Valor absoluto de ATR
- `r_value`: Distancia de stop loss (R)
- `risk_multiplier`: Multiplicador de riesgo adaptativo

## 🎓 Resultado Esperado

1. **Bot que aprende estrategias en tiempo real**
   - Modelo entrenado con datos reales de mercado
   - Features normalizadas permiten generalización

2. **Dataset robusto y generalizable**
   - Cientos o miles de trades diarios (en modo PAPER)
   - Balanceo entre trades ejecutados, rechazados y sin señal
   - Contexto completo de cada decisión

3. **Capacidad de adaptación**
   - Operar hoy y adaptarse mañana a otros precios
   - Aplicable a otros activos con las mismas features relativas

## ⚠️ Notas Importantes

1. **Modo PAPER es para aprendizaje**: No usar estrategias no probadas en LIVE
2. **Features relativas son críticas**: El modelo debe generalizar, no memorizar precios
3. **Balanceo de dataset**: El sistema registra tanto trades ejecutados como rechazados/no-operados
4. **Cooldown configurable**: Ajustar según frecuencia deseada (más bajo = más trades)
5. **Riesgo adaptativo**: En PAPER, el riesgo se reduce progresivamente, no se bloquea completamente

## 📝 Logs y Monitoreo

En modo PAPER (Learning Mode), los logs muestran:
- `📚 [PAPER Learning Mode]`: Información sobre acumulación de datos
- `📉 [PAPER] Reducción adaptativa de riesgo`: Cuando se reduce el riesgo por pérdidas
- `💾 Trade ejecutado guardado ML`: Cada trade registrado
- `📚 Señal rechazada guardada ML`: Señales rechazadas (cada 10)
- `📚 Contexto sin señal guardado ML`: Contextos sin señal (cada 200)
