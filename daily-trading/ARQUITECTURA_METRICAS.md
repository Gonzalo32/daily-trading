# 📊 Arquitectura Centralizada de Métricas

## Respuestas a las Preguntas Clave

### 1. ¿Dónde centralizar todas las métricas?

**SOLUCIÓN IMPLEMENTADA:** `src/metrics/metrics_collector.py`

**Ubicación:** `daily-trading/src/metrics/metrics_collector.py`

**Ventajas:**
- ✅ **Fuente única de verdad**: Todas las métricas se calculan en un solo lugar
- ✅ **Sin duplicación**: Backtest, risk_manager y dashboards consumen del mismo módulo
- ✅ **Persistencia**: Base de datos SQLite para histórico completo
- ✅ **Tiempo real**: Cache en memoria para acceso rápido

**Cómo usar:**
```python
from src.metrics import MetricsCollector

collector = MetricsCollector(db_path="data/metrics.db", initial_capital=10000)

# Registrar trade
collector.record_trade(
    position=position_dict,
    exit_price=exit_price,
    pnl=pnl,
    ml_decision=ml_decision,  # CRÍTICO para comparación ML vs sin ML
    market_data=market_data,
    regime_info=regime_info,
    bot_state=bot_state
)

# Obtener métricas del sistema
metrics = collector.get_system_metrics(days=30)
print(f"Expectancy: {metrics.expectancy}")
print(f"ML mejora: {metrics.ml_improvement_pct}%")
```

---

### 2. ¿Cómo medir si el filtro ML mejora el expectancy?

**SOLUCIÓN:** Comparación automática ML vs sin ML

**Métricas clave:**
- `ml_expectancy` vs `no_ml_expectancy`
- `ml_win_rate` vs `no_ml_win_rate`
- `ml_profit_factor` vs `no_ml_profit_factor`
- `ml_improvement_pct` (% de mejora)

**Cómo usar:**
```python
# Reporte comparativo
report = collector.get_ml_vs_no_ml_report(days=30)

print(f"ML Expectancy: {report['ml_metrics']['expectancy']:.2f}")
print(f"Sin ML Expectancy: {report['no_ml_metrics']['expectancy']:.2f}")
print(f"Mejora: {report['improvement_pct']:.1f}%")
print(f"Recomendación: {report['recommendation']}")

# Resultado:
# - 'USE_ML' si ML mejora expectancy
# - 'NO_ML' si ML empeora expectancy
# - 'confidence': 'HIGH' o 'LOW' según diferencia
```

**Requisito CRÍTICO:** 
- Cada trade DEBE registrar si fue filtrado por ML (`ml_filtered=True/False`)
- Se debe pasar `ml_decision` al registrar el trade

**Implementación en main.py:**
```python
# Al cerrar posición
ml_decision = None  # Se obtiene antes de abrir la posición
if use_ml_filter:
    ml_decision = await self.ml_filter.filter_signal(...)

# Al registrar trade
collector.record_trade(
    position=position,
    exit_price=exit_price,
    pnl=pnl,
    ml_decision=ml_decision  # ← CRÍTICO
)
```

---

### 3. ¿Qué métricas usar para ajuste automático de riesgo?

**MÉTRICAS RECOMENDADAS (sin sobreajuste):**

#### ✅ Métricas Robustas (usar):
1. **Expectancy reciente** (últimos 20-30 trades)
   - Si < -0.5 → Reducir riesgo 50%
   - Si > 1.0 → Aumentar riesgo 20%

2. **Pérdidas consecutivas**
   - Si >= 3 → Reducir riesgo 30%

3. **Drawdown actual**
   - Si > 10% → Reducir riesgo 40%
   - Si > 20% → Parar trading

4. **Win rate reciente** (últimos 20 trades)
   - Si < 40% → Reducir riesgo
   - Si > 60% → Mantener/aumentar riesgo

#### ❌ Métricas a EVITAR (sobreajuste):
- Win rate de últimos 5 trades (muy volátil)
- PnL del último trade (ruido)
- Métricas de un solo día
- Métricas sin contexto de mercado

**Cómo usar:**
```python
suggestions = collector.get_risk_adjustment_suggestions()

print(f"Multiplicador de tamaño: {suggestions['position_size_multiplier']}")
print(f"Razón: {suggestions['reason']}")
print(f"Nivel de riesgo: {suggestions['risk_level']}")

# Aplicar en risk_manager
adjusted_size = base_size * suggestions['position_size_multiplier']
```

**Implementación sugerida:**
```python
# En risk_manager.py
def get_dynamic_risk_multiplier(self) -> float:
    """Obtiene multiplicador dinámico basado en métricas"""
    suggestions = self.metrics_collector.get_risk_adjustment_suggestions()
    return suggestions['position_size_multiplier']
```

---

### 4. ¿Qué features faltan para ML futuro?

**FEATURES ACTUALES (ya registradas):**
- ✅ Precio, RSI, ATR, volatilidad
- ✅ Regime (trending/ranging/etc)
- ✅ Consecutive signals
- ✅ Daily PnL antes del trade
- ✅ Time of day, day of week
- ✅ Risk amount, R value

**FEATURES FALTANTES (agregar):**

#### 🔴 CRÍTICAS:
1. **Volumen relativo** (volumen actual vs promedio)
2. **Spread bid-ask** (si disponible)
3. **Orden book imbalance** (si disponible)
4. **Correlación con mercado** (correlación con BTC/SPY)
5. **Momentum multi-timeframe** (tendencia en 1h, 4h, 1d)

#### 🟡 IMPORTANTES:
6. **Distancia a soporte/resistencia** más cercano
7. **Número de toques** de soporte/resistencia
8. **Volatilidad implícita** (si trading opciones)
9. **Sentimiento** (si hay API disponible)
10. **Noticias recientes** (si hay API disponible)

#### 🟢 OPCIONALES:
11. **Estacionalidad** (mes del año, trimestre)
12. **Horario de mercado** (pre-market, regular, after-hours)
13. **Día del mes** (efecto calendario)
14. **Distancia a eventos** (earnings, FOMC, etc)

**Cómo agregar:**
```python
# En metrics_collector.py, TradeMetrics dataclass:
volume_ratio: Optional[float] = None  # volumen_actual / volumen_promedio
spread_pct: Optional[float] = None
support_distance_pct: Optional[float] = None
resistance_distance_pct: Optional[float] = None
correlation_btc: Optional[float] = None
momentum_1h: Optional[float] = None
momentum_4h: Optional[float] = None
momentum_1d: Optional[float] = None
```

---

### 5. ¿Qué métricas están duplicadas?

**DUPLICACIONES IDENTIFICADAS:**

#### ❌ DUPLICADAS (eliminar de otros lugares):

1. **daily_pnl**
   - ❌ `main.py`: `self.daily_pnl`
   - ❌ `risk_manager.py`: `self.state.daily_pnl`
   - ✅ **CENTRALIZAR EN:** `MetricsCollector`

2. **win_rate**
   - ❌ `backtest.py`: `_calculate_metrics()` línea 332
   - ❌ `risk_manager.py`: `get_risk_metrics()` línea 287
   - ✅ **CENTRALIZAR EN:** `MetricsCollector.get_system_metrics()`

3. **max_drawdown**
   - ❌ `backtest.py`: `_calculate_metrics()` línea 342
   - ❌ `risk_manager.py`: `update_equity()` línea 321
   - ✅ **CENTRALIZAR EN:** `MetricsCollector._calculate_max_drawdown()`

4. **sharpe_ratio**
   - ❌ `backtest.py`: `_calculate_metrics()` línea 347
   - ❌ `risk_manager.py`: `get_risk_metrics()` línea 289
   - ✅ **CENTRALIZAR EN:** `MetricsCollector._calculate_sharpe_ratio()`

5. **profit_factor**
   - ❌ `backtest.py`: `_calculate_metrics()` línea 354
   - ✅ **CENTRALIZAR EN:** `MetricsCollector.get_system_metrics()`

**PLAN DE MIGRACIÓN:**

1. **Fase 1:** Integrar `MetricsCollector` en `main.py`
   ```python
   # En TradingBot.__init__
   self.metrics_collector = MetricsCollector(
       db_path="data/metrics.db",
       initial_capital=self.config.INITIAL_CAPITAL
   )
   ```

2. **Fase 2:** Reemplazar cálculos en `risk_manager.py`
   ```python
   # En lugar de calcular win_rate aquí:
   def get_risk_metrics(self):
       return self.metrics_collector.get_system_metrics(days=1)
   ```

3. **Fase 3:** Actualizar `backtest.py` para usar `MetricsCollector`
   ```python
   # En Backtester
   def _calculate_metrics(self, initial_capital):
       # Registrar todos los trades
       for trade in self.trades:
           self.metrics_collector.record_trade(...)
       
       # Obtener métricas centralizadas
       return self.metrics_collector.get_system_metrics()
   ```

4. **Fase 4:** Dashboards consumen de `MetricsCollector`
   ```python
   # En dashboard.py
   @app.get("/api/metrics")
   async def get_metrics():
       collector = MetricsCollector()
       return collector.get_system_metrics(days=1).__dict__
   ```

---

## Estructura de Archivos

```
daily-trading/
├── src/
│   ├── metrics/                    # ← NUEVO MÓDULO CENTRALIZADO
│   │   ├── __init__.py
│   │   └── metrics_collector.py   # Colector principal
│   │
│   ├── risk/
│   │   └── risk_manager.py        # ← Simplificar (usar MetricsCollector)
│   │
│   ├── monitoring/
│   │   └── dashboard.py            # ← Consumir de MetricsCollector
│   │
│   └── ml/
│       └── stats_dashboard.py      # ← Consumir de MetricsCollector
│
├── backtest.py                     # ← Usar MetricsCollector
├── main.py                         # ← Integrar MetricsCollector
└── data/
    └── metrics.db                  # Base de datos SQLite
```

---

## Próximos Pasos

1. ✅ **Crear módulo centralizado** (`metrics_collector.py`)
2. ⏳ **Integrar en `main.py`** (registrar trades con ML tracking)
3. ⏳ **Migrar `risk_manager.py`** (usar MetricsCollector)
4. ⏳ **Actualizar `backtest.py`** (usar MetricsCollector)
5. ⏳ **Actualizar dashboards** (consumir de MetricsCollector)
6. ⏳ **Agregar features faltantes** (volumen, spread, etc)

---

## Ejemplo de Uso Completo

```python
from src.metrics import MetricsCollector

# Inicializar
collector = MetricsCollector(initial_capital=10000)

# Registrar trade con TODO el contexto
collector.record_trade(
    position={
        'entry_price': 50000,
        'size': 0.1,
        'stop_loss': 49500,
        'take_profit': 51000,
        'symbol': 'BTC/USDT',
        'side': 'BUY',
        'entry_time': datetime.now(),
        'risk_amount': 50,
        'r_value': 500
    },
    exit_price=51000,
    pnl=100,
    ml_decision={
        'approved': True,
        'probability': 0.65,
        'reason': 'ML approved'
    },
    market_data={
        'indicators': {'rsi': 55, 'atr': 500}
    },
    regime_info={'regime': 'trending'},
    bot_state={
        'daily_pnl': 200,
        'daily_trades': 5
    }
)

# Obtener métricas del sistema
metrics = collector.get_system_metrics(days=30)
print(f"Expectancy: {metrics.expectancy:.2f}")
print(f"ML mejora: {metrics.ml_improvement_pct:.1f}%")

# Comparar ML vs sin ML
report = collector.get_ml_vs_no_ml_report(days=30)
print(f"Recomendación: {report['recommendation']}")

# Ajuste automático de riesgo
suggestions = collector.get_risk_adjustment_suggestions()
print(f"Multiplicador: {suggestions['position_size_multiplier']}")

# Exportar para ML
df = collector.export_training_data("src/ml/training_data.csv")
```

---

## Beneficios de la Centralización

1. ✅ **Sin duplicación**: Una sola fuente de verdad
2. ✅ **Comparación ML**: Tracking automático ML vs sin ML
3. ✅ **Ajuste automático**: Métricas robustas para riesgo dinámico
4. ✅ **Features completas**: Registro de todo para ML futuro
5. ✅ **Histórico completo**: Base de datos SQLite para análisis
6. ✅ **Tiempo real**: Cache en memoria para dashboards
7. ✅ **Escalable**: Fácil agregar nuevas métricas

