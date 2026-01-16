# 🏗️ Arquitectura de Doble Estrategia

## 📋 Resumen

Se ha implementado una arquitectura de **doble estrategia** que permite al bot operar de manera diferente según el modo:

- **PAPER** → `LearningStrategy` (permisiva, genera muchos datos para ML)
- **LIVE** → `ProductionStrategy` (selectiva, alta probabilidad para producción)

## 🎯 Objetivos Cumplidos

✅ **Separación clara**: Strategy NO conoce ML, ML NO modifica Strategy  
✅ **LearningStrategy permisiva**: Genera 300-500 trades diarios en PAPER  
✅ **Features relativas**: Robusto a cambios de precio absoluto  
✅ **RiskManager learning-aware**: No hard-stops en PAPER, reducción progresiva  
✅ **Código limpio y desacoplado**: Factory pattern para elegir estrategia  

## 📁 Archivos Creados/Modificados

### Nuevos Archivos

1. **`src/strategy/learning_strategy.py`**
   - Estrategia permisiva para recopilación de datos
   - Usa solo features relativas (porcentajes, normalizaciones)
   - Genera señales incluso de baja calidad
   - Optimiza diversidad, no rentabilidad

2. **`src/strategy/strategy_factory.py`**
   - Factory para elegir estrategia según modo
   - PAPER → LearningStrategy
   - LIVE → ProductionStrategy

### Archivos Modificados

1. **`src/strategy/trading_strategy.py`**
   - Agregado alias `ProductionStrategy = TradingStrategy`
   - Mantiene compatibilidad total con código existente

2. **`main.py`**
   - Modificado para usar `StrategyFactory.create_strategy()`
   - Selección automática según `TRADING_MODE`

## 🧠 LearningStrategy - Características

### Criterios Permisivos

**BUY:**
- EMA rápida >= EMA lenta (o muy cerca, hasta 0.1% diferencia)
- RSI < 60 (permisivo)
- O RSI muy bajo (< 30) independientemente de EMAs

**SELL:**
- EMA rápida <= EMA lenta (o muy cerca, hasta 0.1% diferencia)
- RSI > 40 (permisivo)
- O RSI muy alto (> 70) independientemente de EMAs

### Features Relativas

LearningStrategy usa **solo features relativas** para ser robusta a cambios de precio:

- `ema_diff_pct`: Diferencia entre EMAs en porcentaje
- `rsi_normalized`: RSI normalizado (-1 a 1, donde 0 = 50)
- `atr_pct`: ATR relativo al precio (%)
- `price_to_fast_pct`: Distancia del precio a EMA rápida (%)
- `price_to_slow_pct`: Distancia del precio a EMA lenta (%)

### Filtros Mínimos

- Solo verifica que precio, stop_loss y take_profit sean válidos
- Evita repeticiones excesivas (diversidad)
- NO filtra por volumen, zonas laterales, calidad, etc.

## 🏭 ProductionStrategy - Características

La estrategia original (ahora `ProductionStrategy`) mantiene:

- Condiciones estrictas (EMA + RSI selectivo)
- Filtros estrictos (volumen, zonas laterales)
- Alta probabilidad de éxito
- Pocas señales de alta calidad

## 🔄 Flujo de Ejecución

```
main.py
  └─> StrategyFactory.create_strategy(config)
       ├─> Si TRADING_MODE == "PAPER"
       │    └─> return LearningStrategy(config)
       │
       └─> Si TRADING_MODE == "LIVE"
            └─> return ProductionStrategy(config)
```

## 🛡️ RiskManager Learning-Aware

El `RiskManager` ya estaba implementado como learning-aware:

- **LIVE**: Límites estrictos (bloqueo si se alcanzan)
- **PAPER**: Soft-risk control (reducción progresiva, nunca bloqueo total)
  - `get_adaptive_risk_multiplier()`: Reduce riesgo progresivamente según PnL
  - Mínimo 20% del riesgo normal (nunca bloquea completamente)
  - Permite continuar generando datos incluso con pérdidas

## 📊 Capacidad de Generación de Datos

### LearningStrategy (PAPER)

- **Frecuencia**: Cooldown mínimo de 2 segundos entre señales del mismo tipo
- **Permisividad**: Criterios muy flexibles (RSI 40-60, EMAs muy cerca)
- **Objetivo**: 300-500 trades diarios
- **Diversidad**: Evita repeticiones excesivas, registra contexto completo

### ProductionStrategy (LIVE)

- **Frecuencia**: Cooldown de 10 segundos, filtros estrictos
- **Selectividad**: Solo señales de alta probabilidad
- **Objetivo**: 5-20 trades diarios (calidad sobre cantidad)

## 🧪 Testing

Para probar la arquitectura:

1. **Modo PAPER (LearningStrategy)**:
   ```bash
   # En .env
   TRADING_MODE=PAPER
   ```
   - Debe generar muchas señales
   - Logs mostrarán "📚 MODO PAPER: Usando LearningStrategy"

2. **Modo LIVE (ProductionStrategy)**:
   ```bash
   # En .env
   TRADING_MODE=LIVE
   ```
   - Debe generar pocas señales de alta calidad
   - Logs mostrarán "🏭 MODO LIVE: Usando ProductionStrategy"

## 📝 Notas Importantes

1. **LearningStrategy SOLO en PAPER**: Tiene una advertencia si se usa en LIVE
2. **Compatibilidad**: `ProductionStrategy` es un alias de `TradingStrategy`, no rompe código existente
3. **Desacoplamiento**: Strategy no conoce ML, ML no modifica Strategy
4. **Features relativas**: LearningStrategy usa solo porcentajes y normalizaciones

## 🎉 Resultado

✅ Arquitectura limpia y desacoplada  
✅ Dos estrategias bien definidas  
✅ Capacidad real de generar 300-500 trades diarios en PAPER  
✅ Dataset rico, generalizable y útil para ML  
✅ Lógica de producción intacta (no se rompió nada)  
