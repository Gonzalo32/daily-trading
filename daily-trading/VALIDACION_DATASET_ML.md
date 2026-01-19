# Validación del Dataset ML

## Objetivo
Confirmar que el dataset es apto para aprender **ESTRATEGIA**, no condiciones específicas de mercado.

---

## 1. Esquema de `decisions.csv` (DecisionSamples)

### Columnas del CSV:

#### Identificadores
- `timestamp`: Fecha/hora de la decisión
- `symbol`: Símbolo del activo

#### Features Relativas (SOLO estas se usan para ML)
- `ema_cross_diff_pct`: Diferencia EMA fast vs slow (%)
- `atr_pct`: ATR relativo al precio (%)
- `rsi_normalized`: RSI normalizado (-1 a 1, donde 0 = 50)
- `price_to_fast_pct`: Distancia precio a EMA rápida (%)
- `price_to_slow_pct`: Distancia precio a EMA lenta (%)
- `trend_direction`: 1=alcista, -1=bajista, 0=neutral
- `trend_strength`: Fuerza de tendencia (magnitud normalizada)

#### Decision Space (de Strategy)
- `decision_buy_possible`: bool - BUY es posible según strategy
- `decision_sell_possible`: bool - SELL es posible según strategy
- `decision_hold_possible`: bool - HOLD siempre True

#### Señales y Acciones
- `strategy_signal`: "BUY" | "SELL" | "NONE" - Lo que propone la estrategia
- `executed_action`: "BUY" | "SELL" | "HOLD" - Lo que realmente se ejecutó
- `was_executed`: bool - True si executed_action es BUY o SELL

#### Contexto de Mercado (categórico, no absoluto)
- `regime`: "trending_bullish" | "trending_bearish" | "ranging" | "high_volatility" | etc.
- `volatility_level`: "low" | "medium" | "high"

#### Trazabilidad de Decisiones
- `decision_outcome`: Etiqueta semántica del resultado
  - `"accepted"` - Se ejecutó exitosamente
  - `"rejected_by_risk"` - Rechazado por RiskManager
  - `"rejected_by_limits"` - Rechazado por límites diarios
  - `"rejected_by_filters"` - Rechazado por ML filter
  - `"rejected_by_execution"` - Rechazado por error de ejecución
  - `"no_signal"` - No hubo señal de estrategia
- `reject_reason`: Razón legible del rechazo (si aplica)
- `reason`: Razón completa legible para humanos

### ✅ Validación de Features

**NO contiene:**
- ❌ Precio absoluto
- ❌ Capital
- ❌ PnL
- ❌ Balances
- ❌ Equity
- ❌ Valores absolutos de volumen

**Solo contiene:**
- ✅ Features relativas (porcentajes, normalizaciones)
- ✅ Decision space (qué acciones son posibles)
- ✅ Contexto categórico (regime, volatility_level)

---

## 2. Esquema de `trades.csv` (Trades Ejecutados)

### Columnas del CSV:

#### Identificadores y Trade Info
- `timestamp`: Fecha/hora de entrada
- `symbol`: Símbolo del activo
- `side`: "BUY" | "SELL"
- `entry_price`: Precio de entrada (necesario para outcome, NO para features)
- `exit_price`: Precio de salida (necesario para outcome, NO para features)
- `pnl`: P&L del trade (OUTCOME, NO feature)
- `size`: Tamaño de posición
- `stop_loss`: Stop loss
- `take_profit`: Take profit
- `duration_seconds`: Duración del trade

#### Risk Management (necesario para outcome)
- `risk_amount`: Cantidad arriesgada
- `atr_value`: Valor ATR (necesario para calcular R)
- `r_value`: Valor R (distancia a stop loss)
- `risk_multiplier`: Multiplicador de riesgo

#### Features Relativas (del contexto de ENTRADA)
- `ema_cross_diff_pct`: Diferencia EMA fast vs slow (%) al momento de entrada
- `atr_pct`: ATR relativo al precio (%) al momento de entrada
- `rsi_normalized`: RSI normalizado (-1 a 1) al momento de entrada
- `price_to_fast_pct`: Distancia precio a EMA rápida (%) al momento de entrada
- `price_to_slow_pct`: Distancia precio a EMA lenta (%) al momento de entrada
- `trend_direction`: 1=alcista, -1=bajista, 0=neutral al momento de entrada
- `trend_strength`: Fuerza de tendencia al momento de entrada

#### Contexto de Mercado (al momento de entrada)
- `regime`: Régimen de mercado
- `volatility_level`: Nivel de volatilidad

#### Outcomes (TARGETS para entrenar)
- `target`: 1 si pnl >= r_value, 0 si no
- `trade_type`: Siempre "executed" para este archivo
- `exit_type`: "stop_loss" | "take_profit" | "trailing_stop" | "time_stop" | etc.
- `r_multiple`: pnl / r_value (métrica de performance)
- `time_in_trade`: Duración en segundos

### ✅ Validación de Features

**Features de entrada (para ML):**
- ✅ Solo features relativas del contexto de ENTRADA
- ✅ NO incluyen información de salida (exit_price, pnl, etc.)

**Outcomes (targets):**
- ✅ `target`, `r_multiple`, `exit_type` son OUTCOMES, no features
- ✅ Se usan para entrenar el modelo, no como input

---

## 3. Validación de Combinaciones Esperadas

### DecisionSamples que DEBEN existir:

1. **HOLD + no_signal**
   - `strategy_signal = "NONE"`
   - `executed_action = "HOLD"`
   - `decision_outcome = "no_signal"`
   - ✅ Representa: Mercado no cumplió condiciones de estrategia

2. **HOLD + rejected_by_risk**
   - `strategy_signal = "BUY" | "SELL"`
   - `executed_action = "HOLD"`
   - `decision_outcome = "rejected_by_risk"`
   - ✅ Representa: Señal generada pero rechazada por RiskManager

3. **HOLD + rejected_by_limits**
   - `strategy_signal = "BUY" | "SELL"`
   - `executed_action = "HOLD"`
   - `decision_outcome = "rejected_by_limits"`
   - ✅ Representa: Señal generada pero rechazada por límites diarios

4. **HOLD + rejected_by_filters**
   - `strategy_signal = "BUY" | "SELL"`
   - `executed_action = "HOLD"`
   - `decision_outcome = "rejected_by_filters"`
   - ✅ Representa: Señal generada pero rechazada por ML filter

5. **BUY/SELL + accepted**
   - `strategy_signal = "BUY" | "SELL"`
   - `executed_action = "BUY" | "SELL"`
   - `decision_outcome = "accepted"`
   - ✅ Representa: Señal ejecutada exitosamente

### ⚠️ NOTA sobre "HOLD + accepted"
- No debería existir esta combinación
- Si `executed_action = "HOLD"`, el outcome debería ser `"no_signal"` o `"rejected_*"`
- Si existe, es un error de lógica

---

## 4. Balance del Dataset

### Ratio esperado:
- **DecisionSamples** >> **Trades ejecutados**
  - DecisionSamples incluyen: HOLDs, rechazos, y ejecuciones
  - Trades ejecutados solo incluyen: BUY/SELL aceptados

### Downsampling de HOLD:
- HOLD samples sin señal se downsampléan (1 de cada N, configurable)
- BUY/SELL samples SIEMPRE se guardan (sin downsampling)

---

## 5. Verificación de Leakage

### ❌ NO debe haber leakage de:
- Precio absoluto en features
- Capital/equity en features
- PnL en features (solo en outcomes)
- Balances en features
- Información futura (exit_price, exit_time) en features de entrada

### ✅ Solo debe haber:
- Features relativas (porcentajes, normalizaciones)
- Contexto categórico (regime, volatility)
- Decision space (qué acciones son posibles)
- Outcomes separados de features

---

## 6. Conclusión

El dataset está diseñado para aprender **ESTRATEGIA** (cuándo BUY/SELL/HOLD es apropiado) basándose en:
- Features relativas (robustas a cambios de precio)
- Decision space (qué acciones son posibles)
- Contexto de mercado (regime, volatility)

**NO** aprende:
- Precios específicos
- Condiciones de mercado absolutas
- Capital disponible
- Balances

Esto permite que el modelo sea **generalizable** y funcione en diferentes condiciones de mercado y niveles de precio.
