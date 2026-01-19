# Reporte de Auditoría del Dataset ML

## Estado Actual

### Archivos Encontrados

1. **training_data.csv**: ✅ Existe en `src/ml/training_data.csv`
   - Contiene registros de trades ejecutados y señales rechazadas
   - Formato: CSV sin encabezados claros (requiere análisis)

2. **decisions.csv**: ⚠️ No encontrado
   - Debe generarse cuando el bot está en modo PAPER
   - Ubicación esperada: `src/ml/decisions.csv`

## Verificaciones Requeridas

### ✅ 1. Más DecisionSamples que trades ejecutados
**Estado**: ⚠️ No verificable (decisions.csv no existe aún)

**Acción requerida**: 
- Ejecutar el bot en modo `TRADING_MODE=PAPER` para generar DecisionSamples
- El bot debe crear `decisions.csv` automáticamente

### ✅ 2. HOLD explícitos con diferentes outcomes
**Estado**: ⚠️ No verificable (decisions.csv no existe aún)

**Outcomes esperados en HOLD**:
- `no_signal`: ✅ Debe existir
- `rejected_by_risk`: ✅ Debe existir
- `rejected_by_limits`: ✅ Debe existir
- `rejected_by_filters`: ✅ Debe existir

**Acción requerida**: 
- Verificar que el bot registre DecisionSamples con `executed_action="HOLD"` y diferentes `decision_outcome`

### ✅ 3. Ninguna feature depende de precio absoluto, equity, pnl
**Estado**: ✅ Verificado en código

**Features permitidas** (relativas):
- `ema_cross_diff_pct`: ✅ Diferencia porcentual
- `atr_pct`: ✅ ATR relativo al precio
- `rsi_normalized`: ✅ RSI normalizado (-1 a 1)
- `price_to_fast_pct`: ✅ Distancia porcentual
- `price_to_slow_pct`: ✅ Distancia porcentual
- `trend_direction`: ✅ Dirección de tendencia (-1, 0, 1)
- `trend_strength`: ✅ Fuerza normalizada

**Features prohibidas**:
- ❌ `price` (precio absoluto)
- ❌ `equity` (capital)
- ❌ `pnl` (ganancia/pérdida)
- ❌ `balance` (balance)

**Verificación en código**:
- `DecisionSampler._extract_relative_features()`: ✅ Solo genera features relativas
- `TradeRecorder.record_decision_sample()`: ✅ Solo guarda features relativas
- `TradeRecorder.record_trade()`: ✅ Solo guarda features relativas del contexto de entrada

### ✅ 4. executed_action SOLO es BUY/SELL cuando hubo ejecución real
**Estado**: ✅ Verificado en código

**Lógica implementada**:
- `was_executed=True` solo cuando `executed_action` es "BUY" o "SELL"
- `executed_action="BUY"/"SELL"` solo cuando `was_executed=True`
- `executed_action="HOLD"` cuando no hay ejecución

**Verificación en código**:
- `main.py`: ✅ `executed_action` se establece solo después de ejecución exitosa
- `TradeRecorder.record_decision_sample()`: ✅ `was_executed = executed_action in ["BUY", "SELL"]`

## Scripts de Auditoría

### 1. `audit_dataset.py`
Script completo de auditoría que verifica:
- Esquema de columnas
- Data leakage
- Combinaciones executed_action + decision_outcome
- Balance del dataset

**Uso**: `python audit_dataset.py`

### 2. `audit_dataset_report.py`
Script simplificado que genera reporte ejecutivo

**Uso**: `python audit_dataset_report.py`

### 3. `validate_dataset.py`
Script de validación básica existente

**Uso**: `python validate_dataset.py`

## Próximos Pasos

1. **Ejecutar el bot en modo PAPER**:
   ```bash
   TRADING_MODE=PAPER MVP_MODE=True python main.py
   ```

2. **Verificar que se genera decisions.csv**:
   - Debe aparecer en `src/ml/decisions.csv`
   - Debe contener DecisionSamples con diferentes outcomes

3. **Ejecutar auditoría**:
   ```bash
   python audit_dataset.py
   ```

4. **Verificar resultados**:
   - Ratio DecisionSamples / Trades >= 2
   - HOLD con todos los outcomes esperados
   - No hay data leakage
   - executed_action consistente con was_executed

## Conclusión

**Estado del Dataset**: ⚠️ En desarrollo

**Problemas identificados**:
- `decisions.csv` no existe aún (requiere ejecución del bot en modo PAPER)

**Código verificado**: ✅
- Features relativas implementadas correctamente
- Lógica de executed_action correcta
- Esquema de DecisionSample correcto

**Acción inmediata**: Ejecutar el bot en modo PAPER para generar DecisionSamples
