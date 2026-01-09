# ✅ CHECKLIST DE MEJORAS
## Trading Bot - Plan de Acción Priorizado

**Fecha:** 6 de enero de 2025  
**Objetivo:** Guía práctica para estabilizar el sistema

---

## 🎯 FASE 1: ESTABILIZACIÓN (Semana 1)

### Día 1-2: Centralizar Métricas

- [ ] **Integrar MetricsCollector en TradingBot**
  - [ ] Instanciar `MetricsCollector` en `__init__`
  - [ ] Reemplazar `self.daily_pnl` por `metrics_collector.get_system_metrics().daily_pnl`
  - [ ] Reemplazar `self.daily_trades` por `metrics_collector.get_system_metrics().total_trades`
  - [ ] Eliminar atributos duplicados de `TradingBot`

- [ ] **Eliminar cálculo de métricas de RiskManager**
  - [ ] Mantener solo validaciones de riesgo
  - [ ] Delegar cálculo de métricas a `MetricsCollector`
  - [ ] Actualizar tests unitarios

- [ ] **Registrar trades en MetricsCollector**
  - [ ] Llamar a `metrics_collector.record_trade()` en cada cierre
  - [ ] Pasar contexto completo (market_data, regime_info, ml_decision, bot_state)
  - [ ] Verificar que se guardan en SQLite

### Día 3-4: Persistencia de Estado

- [ ] **Implementar guardado de equity curve**
  - [ ] Crear tabla `equity_history` en SQLite
  - [ ] Guardar equity cada N trades (ej: cada 10)
  - [ ] Método `save_equity_snapshot()`

- [ ] **Implementar recuperación de estado**
  - [ ] Método `load_last_state()` en `TradingBot.__init__`
  - [ ] Recuperar equity, peak_equity, max_drawdown
  - [ ] Recuperar contador de trades diarios
  - [ ] Log de estado recuperado

- [ ] **Checkpoints automáticos**
  - [ ] Guardar estado cada 50 trades
  - [ ] Guardar estado al cerrar el bot
  - [ ] Guardar estado cada 1 hora (backup)

### Día 5: Testing y Validación

- [ ] **Tests de integración**
  - [ ] Test: Métricas consistentes entre módulos
  - [ ] Test: Estado se recupera correctamente
  - [ ] Test: No hay duplicación de cálculos
  - [ ] Test: SQLite guarda correctamente

- [ ] **Validación manual**
  - [ ] Correr bot en paper 1 hora
  - [ ] Reiniciar y verificar recuperación
  - [ ] Comparar métricas antes/después
  - [ ] Verificar logs de estado

- [ ] **Documentación**
  - [ ] Actualizar README con cambios
  - [ ] Documentar estructura de SQLite
  - [ ] Documentar proceso de recuperación

---

## 🎯 FASE 2: ACUMULACIÓN DE DATOS (Semana 2-3)

### Semana 2: Setup y Monitoreo

- [ ] **Configurar bot para correr 24/7**
  - [ ] Verificar que `TRADING_MODE = "PAPER"`
  - [ ] Verificar que `ENABLE_ML = True` (para guardar datos)
  - [ ] Configurar `MVP_MODE_ENABLED = True`
  - [ ] Configurar `MAX_DAILY_TRADES = 200`

- [ ] **Sistema de monitoreo**
  - [ ] Script para verificar que el bot está vivo
  - [ ] Script para contar trades en CSV
  - [ ] Script para calcular métricas diarias
  - [ ] Notificación si el bot se detiene

- [ ] **Iniciar bot**
  - [ ] Correr en modo PAPER
  - [ ] Verificar que genera señales
  - [ ] Verificar que guarda trades en CSV
  - [ ] Verificar que no hay errores en logs

### Semana 3: Monitoreo y Ajustes

- [ ] **Monitoreo diario**
  - [ ] Verificar trades generados (objetivo: 50-100/día)
  - [ ] Verificar calidad de datos en CSV
  - [ ] Verificar que no hay NaN o valores inválidos
  - [ ] Verificar que features se guardan correctamente

- [ ] **Análisis semanal**
  - [ ] Calcular win rate actual
  - [ ] Calcular expectancy actual
  - [ ] Calcular max drawdown
  - [ ] Identificar patrones en trades perdedores

- [ ] **Ajustes si es necesario**
  - [ ] Si win rate < 40% → revisar condiciones de entrada
  - [ ] Si muy pocas señales → aflojar filtros
  - [ ] Si muchas señales → endurecer filtros
  - [ ] Si drawdown > 30% → reducir riesgo

### Checkpoint: 5,000 Trades

- [ ] **Validar datos**
  - [ ] Contar trades en CSV (debe ser >= 5,000)
  - [ ] Verificar distribución de wins/losses
  - [ ] Verificar que todas las features están completas
  - [ ] Verificar que no hay duplicados

- [ ] **Análisis de performance**
  - [ ] Win rate final
  - [ ] Expectancy final
  - [ ] Max drawdown
  - [ ] Sharpe ratio
  - [ ] Profit factor

- [ ] **Decisión GO/NO-GO para ML**
  - [ ] Si win rate > 45% → continuar a Fase 3
  - [ ] Si expectancy > 0 → continuar a Fase 3
  - [ ] Si max drawdown < 30% → continuar a Fase 3
  - [ ] Si NO cumple → revisar estrategia

---

## 🎯 FASE 3: MACHINE LEARNING (Semana 4)

### Día 1-2: Preparación de Datos

- [ ] **Limpiar datos**
  - [ ] Eliminar trades con NaN
  - [ ] Eliminar duplicados
  - [ ] Verificar distribución de target (idealmente 40-60%)
  - [ ] Separar train/validation/test (60/20/20)

- [ ] **Feature engineering**
  - [ ] Verificar que todas las features están presentes
  - [ ] Normalizar features numéricas
  - [ ] Codificar features categóricas (side, regime)
  - [ ] Crear features derivadas si es necesario

### Día 3-4: Entrenamiento

- [ ] **Entrenar modelo base**
  - [ ] Correr `auto_trainer.py`
  - [ ] Verificar que el modelo se guarda en `models/model.pkl`
  - [ ] Revisar métricas de entrenamiento (accuracy, precision, recall)
  - [ ] Verificar que no hay overfitting (train vs test)

- [ ] **Optimización de hiperparámetros**
  - [ ] Probar diferentes valores de `n_estimators`
  - [ ] Probar diferentes valores de `max_depth`
  - [ ] Probar diferentes valores de `min_samples_split`
  - [ ] Seleccionar mejor modelo según validation accuracy

- [ ] **Validación**
  - [ ] Accuracy en test set > 55%
  - [ ] Precision en test set > 55%
  - [ ] Recall balanceado (no predecir siempre la misma clase)
  - [ ] Feature importance (verificar que tiene sentido)

### Día 5: Comparación ML vs Sin ML

- [ ] **Backtest sin ML**
  - [ ] Correr backtest con todos los trades
  - [ ] Calcular expectancy, win rate, profit factor
  - [ ] Calcular max drawdown
  - [ ] Guardar resultados

- [ ] **Backtest con ML**
  - [ ] Filtrar trades con P(win) < 55%
  - [ ] Calcular expectancy, win rate, profit factor
  - [ ] Calcular max drawdown
  - [ ] Guardar resultados

- [ ] **Comparación cuantitativa**
  - [ ] Expectancy ML vs sin ML (debe mejorar > 10%)
  - [ ] Win rate ML vs sin ML
  - [ ] Profit factor ML vs sin ML
  - [ ] Número de trades (ML debe reducir)

- [ ] **Decisión GO/NO-GO para activar ML**
  - [ ] Si ML mejora expectancy > 10% → activar
  - [ ] Si ML reduce drawdown > 20% → activar
  - [ ] Si NO mejora → NO activar (seguir sin ML)

---

## 🎯 FASE 4: PREPARACIÓN PARA LIVE (Semana 5)

### Día 1-2: Testing Final

- [ ] **Paper trading con ML activo**
  - [ ] Activar `ENABLE_ML = True`
  - [ ] Verificar que el modelo carga correctamente
  - [ ] Verificar que filtra señales (rechaza algunas)
  - [ ] Correr 2-3 días en paper

- [ ] **Validación de performance**
  - [ ] Win rate con ML > win rate sin ML
  - [ ] Expectancy con ML > expectancy sin ML
  - [ ] Max drawdown con ML < max drawdown sin ML
  - [ ] Número de trades reducido (calidad > cantidad)

### Día 3-4: Sistema de Alertas

- [ ] **Implementar alertas críticas**
  - [ ] Alerta si bot se detiene
  - [ ] Alerta si drawdown > 10%
  - [ ] Alerta si pérdida diaria > 3%
  - [ ] Alerta si no hay trades en 2 horas (posible problema)

- [ ] **Configurar notificaciones**
  - [ ] Telegram bot (si está habilitado)
  - [ ] Email (alternativa)
  - [ ] Logs detallados

### Día 5: Go Live

- [ ] **Configuración LIVE**
  - [ ] Cambiar `TRADING_MODE = "LIVE"`
  - [ ] Verificar API keys de exchange
  - [ ] Configurar capital limitado (< 5% del total)
  - [ ] Configurar stop loss de cuenta (10% pérdida)

- [ ] **Checklist pre-live**
  - [ ] Modelo ML cargado y validado
  - [ ] Métricas centralizadas funcionando
  - [ ] Persistencia de estado funcionando
  - [ ] Sistema de alertas activo
  - [ ] Logs configurados correctamente

- [ ] **Iniciar en LIVE**
  - [ ] Correr con supervisión constante (primeras 24h)
  - [ ] Verificar ejecución de órdenes reales
  - [ ] Verificar cálculo de PnL real
  - [ ] Verificar que alertas funcionan

- [ ] **Monitoreo intensivo (primera semana)**
  - [ ] Revisar trades diariamente
  - [ ] Verificar que no hay errores
  - [ ] Verificar que performance es similar a paper
  - [ ] Ajustar si es necesario

---

## 🚨 CRITERIOS DE PARADA

### Detener inmediatamente si:

- [ ] Pérdida diaria > 5% del capital
- [ ] Drawdown > 15%
- [ ] 5 trades perdedores consecutivos
- [ ] Error crítico en logs (exception no manejada)
- [ ] Desconexión del exchange > 5 minutos
- [ ] Métricas inconsistentes entre módulos

### Pausar y revisar si:

- [ ] Win rate < 40% después de 100 trades
- [ ] Expectancy negativa después de 100 trades
- [ ] Drawdown > 10%
- [ ] Modelo ML empeora performance vs sin ML
- [ ] Trades ejecutados no coinciden con señales esperadas

---

## 📊 MÉTRICAS DE SEGUIMIENTO

### Diarias

- [ ] Trades ejecutados
- [ ] Win rate
- [ ] PnL diario
- [ ] Drawdown actual
- [ ] Señales generadas vs ejecutadas

### Semanales

- [ ] Win rate acumulado
- [ ] Expectancy
- [ ] Profit factor
- [ ] Max drawdown
- [ ] Sharpe ratio

### Mensuales

- [ ] Retorno mensual
- [ ] Comparación ML vs sin ML
- [ ] Análisis de trades perdedores
- [ ] Optimización de parámetros
- [ ] Re-entrenamiento de ML (si es necesario)

---

## 🎯 INDICADORES DE ÉXITO

### Fase 1 (Estabilización)
- ✅ Métricas consistentes en todos los módulos
- ✅ Estado persiste entre reinicios
- ✅ Sin duplicación de código

### Fase 2 (Acumulación)
- ✅ 5,000+ trades reales
- ✅ Win rate > 45%
- ✅ Expectancy > 0
- ✅ Max drawdown < 30%

### Fase 3 (ML)
- ✅ Modelo con accuracy > 55%
- ✅ ML mejora expectancy > 10%
- ✅ ML reduce drawdown > 20%

### Fase 4 (LIVE)
- ✅ Performance similar a paper
- ✅ Sin errores críticos
- ✅ Alertas funcionando
- ✅ Retorno positivo primera semana

---

## 📝 NOTAS IMPORTANTES

### Antes de empezar

1. **Hacer backup del código actual**
   ```bash
   git commit -m "Estado pre-mejoras"
   git tag v1.0-pre-mejoras
   ```

2. **Crear rama de desarrollo**
   ```bash
   git checkout -b mejoras-estabilizacion
   ```

3. **Documentar cambios**
   - Mantener CHANGELOG.md actualizado
   - Documentar decisiones técnicas
   - Guardar resultados de tests

### Durante el proceso

1. **Commits frecuentes**
   - Commit después de cada tarea completada
   - Mensajes descriptivos
   - No mezclar cambios no relacionados

2. **Testing continuo**
   - Correr tests después de cada cambio
   - Verificar que no se rompe funcionalidad existente
   - Agregar tests para nuevo código

3. **Monitoreo constante**
   - Revisar logs diariamente
   - Verificar métricas semanalmente
   - Ajustar si es necesario

### Después de cada fase

1. **Revisión de código**
   - Verificar que cumple estándares
   - Eliminar código comentado
   - Actualizar documentación

2. **Merge a main**
   ```bash
   git checkout main
   git merge mejoras-estabilizacion
   git tag v1.1-estabilizado
   ```

3. **Retrospectiva**
   - ¿Qué funcionó bien?
   - ¿Qué se puede mejorar?
   - ¿Qué aprendimos?

---

**Documentos relacionados:**
- `INFORME_ESTADO_SISTEMA.md` - Análisis técnico completo
- `DIAGNOSTICO_VISUAL.md` - Diagramas y visualizaciones
- `RESUMEN_EJECUTIVO.md` - Decisión y recomendaciones

**Fin del checklist**

