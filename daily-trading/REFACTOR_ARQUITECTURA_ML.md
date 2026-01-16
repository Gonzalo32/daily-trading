# 🔄 Refactor de Arquitectura: Learning vs Production + Dataset ML sin Sesgo

## 📋 Resumen del Refactor

Se ha refactorizado completamente la arquitectura para separar claramente:
- **Decisiones** (qué acciones son posibles)
- **Ejecución** (qué acciones se ejecutan realmente)
- **Aprendizaje ML** (dataset completo sin sesgo)

## 🎯 Problemas Resueltos

### ✅ 1. Mezcla indebida de conceptos eliminada

**Antes:**
- `TradingStrategy` cambiaba comportamiento según `TRADING_MODE == PAPER`
- Esto contaminaba el dataset y rompía la separación de estrategias

**Ahora:**
- `ProductionStrategy` es 100% determinística e idéntica en PAPER y LIVE
- No hay lógica condicional basada en `TRADING_MODE` dentro de estrategias

### ✅ 2. Dataset rico con decisiones completas

**Antes:**
- Solo se registraban trades ejecutados
- Muchas decisiones no quedaban registradas
- Dataset sesgado hacia "operar siempre"

**Ahora:**
- Se registran TODAS las decisiones (BUY/SELL/HOLD)
- `DecisionSampler` crea `DecisionSample` en cada tick (PAPER)
- El ML aprende del espacio completo de decisiones

### ✅ 3. HOLD explícito y aprendible

**Antes:**
- HOLD era ausencia de señal (implícito)
- No se podía aprender cuándo HOLD es la mejor acción

**Ahora:**
- HOLD es una acción explícita en `decision_space`
- Se registra explícitamente en el dataset
- El ML puede aprender cuándo HOLD es apropiado

## 🏗️ Arquitectura Nueva

### 1. Decision Sampling Layer (NUEVO)

**Archivo:** `src/strategy/decision_sampler.py`

**Responsabilidades:**
- Extraer features relativas del mercado
- Determinar `decision_space` (qué acciones son posibles)
- Crear `DecisionSample` estructurado
- NO ejecuta trades
- NO modifica estrategia

**DecisionSample contiene:**
```python
{
    "timestamp": datetime,
    "symbol": str,
    "features": {
        "ema_diff_pct": float,      # Features relativas
        "rsi_normalized": float,
        "atr_pct": float,
        ...
    },
    "decision_space": {
        "buy": bool,
        "sell": bool,
        "hold": True  # Siempre disponible
    },
    "strategy_signal": "BUY|SELL|None",
    "executed_action": "BUY|SELL|HOLD|None",
    "reason": str,
    "market_context": {...}
}
```

### 2. LearningStrategy (Refactorizada)

**Cambios:**
- Agregado método `get_decision_space()` que retorna espacio completo
- Mantiene generación permisiva de señales
- Usa solo features relativas

### 3. ProductionStrategy (Limpiada)

**Cambios:**
- ❌ Eliminada toda lógica condicional `TRADING_MODE == "PAPER"`
- ✅ Condiciones estrictas idénticas en PAPER y LIVE
- ✅ 100% determinística

**Condiciones estrictas (producción):**
- BUY: `EMA rápida > EMA lenta` + `RSI < 35` + diferencia mínima
- SELL: `EMA rápida < EMA lenta` + `RSI > 65` + diferencia mínima

### 4. TradeRecorder (Extendido)

**Nuevas columnas en CSV:**
- `decision_buy_possible`: bool
- `decision_sell_possible`: bool
- `decision_hold_possible`: bool (siempre True)
- `strategy_signal`: "BUY"|"SELL"|"NONE"
- `executed_action`: "BUY"|"SELL"|"HOLD"
- `was_executed`: bool
- `exit_type`: str (para trades ejecutados)
- `r_multiple`: float (para trades ejecutados)
- `time_in_trade`: float (para trades ejecutados)

**Nuevo método:**
- `record_decision_sample(decision_sample)`: Registra DecisionSample completo

### 5. main.py (Integración)

**Flujo nuevo:**
```
1. Obtener market_data
2. Generar señal de estrategia
3. Crear DecisionSample (SIEMPRE en PAPER)
4. Si hay señal → validar riesgo → ejecutar o rechazar
5. Actualizar DecisionSample con executed_action
6. Registrar DecisionSample en TradeRecorder
```

**Validación de arquitectura:**
- Método `_validate_architecture()` verifica:
  - Estrategia correcta según modo
  - DecisionSampler solo en PAPER
  - TradeRecorder tiene método `record_decision_sample`

## 📁 Archivos Modificados

### Archivos Nuevos
1. **`src/strategy/decision_sampler.py`** (NUEVO)
   - Decision Sampling Layer
   - Genera DecisionSamples con features relativas

### Archivos Modificados
1. **`src/strategy/learning_strategy.py`**
   - Agregado método `get_decision_space()`

2. **`src/strategy/trading_strategy.py`**
   - ❌ Eliminada lógica condicional `TRADING_MODE == "PAPER"`
   - ✅ Condiciones estrictas idénticas en PAPER y LIVE

3. **`src/ml/trade_recorder.py`**
   - Agregadas nuevas columnas al CSV
   - Agregado método `record_decision_sample()`

4. **`main.py`**
   - Integración de DecisionSampler
   - Registro de DecisionSamples en cada tick (PAPER)
   - Validación de arquitectura

## 🧪 Validación

El método `_validate_architecture()` verifica al inicio:

✅ **PAPER mode:**
- Usa LearningStrategy
- DecisionSampler activado
- TradeRecorder activado con `record_decision_sample`

✅ **LIVE mode:**
- Usa ProductionStrategy
- DecisionSampler desactivado
- TradeRecorder opcional (solo si ENABLE_ML)

✅ **ProductionStrategy:**
- No contiene lógica condicional PAPER/LIVE
- Es idéntica en ambos modos

## 📊 Resultado del Dataset

### Antes del Refactor
- Solo trades ejecutados
- ~100-500 samples diarios (solo trades)
- Sesgo hacia "operar siempre"
- HOLD implícito (ausencia de señal)

### Después del Refactor
- Decisiones completas (BUY/SELL/HOLD)
- Miles de samples diarios (cada tick genera DecisionSample)
- Sin sesgo (aprende cuándo NO operar)
- HOLD explícito y aprendible

## 🔄 Flujo Completo

```
┌─────────────────┐
│  Market Data    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Strategy      │───► Genera señal (BUY/SELL/None)
│ (Learning/Prod)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DecisionSampler │───► Crea DecisionSample
│  (Solo PAPER)   │     - Features relativas
└────────┬────────┘     - Decision space
         │              - Strategy signal
         ▼
┌─────────────────┐
│  RiskManager    │───► Valida si se puede ejecutar
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ OrderExecutor   │───► Ejecuta o rechaza
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TradeRecorder   │───► Registra DecisionSample
│                 │     con executed_action
└─────────────────┘     (BUY/SELL/HOLD)
```

## ✅ Reglas de Diseño Cumplidas

- ✅ Strategy NO conoce ML
- ✅ ML NO modifica Strategy
- ✅ LearningStrategy NO optimiza rentabilidad
- ✅ ProductionStrategy NO se adapta a PAPER
- ✅ HOLD es una acción explícita
- ✅ Solo features relativas (robustas a cambios de precio)

## 🎉 Beneficios

1. **Dataset sin sesgo**: Aprende de decisiones, no solo trades
2. **HOLD aprendible**: El ML puede aprender cuándo NO operar
3. **Miles de samples**: Cada tick genera un DecisionSample
4. **Producción intacta**: ProductionStrategy idéntica en PAPER y LIVE
5. **Arquitectura limpia**: Separación clara de responsabilidades

## 🚀 Próximos Pasos

1. Ejecutar bot en PAPER para generar DecisionSamples
2. Verificar que `training_data.csv` tiene las nuevas columnas
3. Confirmar que hay más DecisionSamples que trades ejecutados
4. Entrenar modelo ML con dataset completo (decisiones + trades)
