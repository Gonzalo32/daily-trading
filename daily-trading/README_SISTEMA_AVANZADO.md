# 🤖 Bot de Trading Intradía Avanzado

Sistema completo de trading automatizado con **Machine Learning**, **análisis de régimen de mercado** y **gestión avanzada de posiciones**.

---

## 🎯 Características Principales

### 1. **Preparación Diaria Automática**
Antes de operar, el bot analiza el mercado:
- ✅ Descarga histórico reciente (30-90 días)
- ✅ Clasifica el régimen de mercado actual
- ✅ Adapta todos los parámetros según el régimen
- ✅ Carga modelos ML si están disponibles

### 2. **Clasificación de Régimen de Mercado**
El bot identifica automáticamente:
- 📈 **Tendencia Alcista**: Sigue la tendencia, prioriza compras
- 📉 **Tendencia Bajista**: Sigue la tendencia, prioriza ventas
- ↔️ **Rango Lateral**: Estrategia de reversión a la media
- 🔥 **Alta Volatilidad**: Parámetros conservadores, menos trades
- 😴 **Baja Volatilidad**: Filtra mercados sin movimiento
- 🌪️ **Caótico**: Muy conservador, evita operar

### 3. **Parámetros Dinámicos**
Se adaptan según el régimen:

| Régimen | Stop Loss | Take Profit | Riesgo/Trade | Max Trades/Día | Estilo |
|---------|-----------|-------------|--------------|----------------|--------|
| Tendencia Alcista | 1.0% | 3.0R | 2.2% | 5 | Follow Trend LONG |
| Tendencia Bajista | 1.0% | 3.0R | 2.2% | 5 | Follow Trend SHORT |
| Rango Lateral | 0.9% | 1.8R | 2.0% | 4 | Mean Reversion |
| Alta Volatilidad | 1.5-3.0% | 1.5R | 1.4% | 3 | Conservative |
| Baja Volatilidad | 0.5-1.5% | 1.5R | 2.0% | 6 | Patient |
| Caótico | 1.5-3.0% | 1.5R | 1.4% | 3 | Very Conservative |

### 4. **Filtro ML Inteligente**
Machine Learning como capa de decisión:
- ✅ Predice probabilidad de éxito (p_win) de cada señal
- ✅ Filtra señales con p_win < 55%
- ✅ Ajusta tamaño de posición según confianza
- ✅ Recomienda RR óptimo (1.5R - 3.0R)
- ✅ Aprende continuamente de cada operación

### 5. **Gestión Avanzada de Posiciones**

#### **Break-Even Automático**
- Cuando la posición alcanza **1R** de ganancia
- Mueve el stop loss a precio de entrada (+ pequeño buffer)
- Protege capital automáticamente

#### **Trailing Stop por ATR**
- Se activa al alcanzar **1.5R** de ganancia
- Sigue el precio con distancia de **1 ATR**
- Maximiza ganancias en tendencias fuertes

#### **Time-Based Stops**
- **Máximo 4 horas** por posición (configurable)
- Cierra posiciones estancadas (sin progreso en 1 hora)
- Evita mantener posiciones overnight

#### **Cierre por Fin de Día**
- Cierra todas las posiciones 30 min antes del cierre
- Solo para mercado de acciones
- Cripto opera 24/7

### 6. **Sistema de Aprendizaje Continuo**
Cada operación registra:
- ✅ **Features técnicas**: RSI, MACD, EMAs, ATR, VWAP
- ✅ **Contexto**: Volatilidad, volumen relativo, hora del día
- ✅ **Régimen**: Tipo y confianza
- ✅ **Estado del bot**: PnL diario, trades previos
- ✅ **Resultados**: PnL, MFE, MAE, duración, tipo de salida
- ✅ **ML**: Probabilidad predicha, aprobación

---

## 🚀 Instalación y Configuración

### 1. **Instalar Dependencias**
```bash
pip install -r requirements.txt
```

### 2. **Configurar Variables de Entorno**
Edita el archivo `.env`:

```env
# Configuración general
TRADING_MODE=PAPER
MARKET=CRYPTO
SYMBOL=BTC/USDT
TIMEFRAME=5m

# Capital y riesgo
INITIAL_CAPITAL=10000
RISK_PER_TRADE=0.02        # 2% por trade
MAX_DAILY_LOSS=0.03         # 3% pérdida máxima diaria
MAX_DAILY_GAIN=0.05         # 5% ganancia máxima diaria

# Binance (Crypto)
BINANCE_API_KEY=tu_api_key
BINANCE_SECRET_KEY=tu_secret_key
BINANCE_TESTNET=true

# Machine Learning
ENABLE_ML=true
ML_MODEL_PATH=models/

# Dashboard
ENABLE_DASHBOARD=true
DASHBOARD_PORT=8000
```

### 3. **Entrenar Modelo ML (Opcional al inicio)**
El bot puede operar sin ML al principio. Después de acumular datos:

```bash
python train_ml_model.py
```

**Recomendación**: Re-entrenar cada 1-2 semanas con nuevos datos.

---

## 📊 Uso del Sistema

### **Iniciar el Bot**

#### Opción 1: Python directo
```bash
python main.py
```

#### Opción 2: Con menú
```bash
python quick_start.py
```

### **Flujo de Operación**

```
1️⃣ PREPARACIÓN DIARIA (Automática cada día)
   ├─ Descargar histórico (90 días)
   ├─ Analizar régimen de mercado
   ├─ Adaptar parámetros
   └─ Cargar modelo ML

2️⃣ BUCLE DE TRADING (Cada vela/tick)
   ├─ Actualizar datos de mercado
   ├─ Verificar filtros básicos (horario, volumen, volatilidad)
   ├─ Generar señal técnica (MA + RSI + MACD + VWAP)
   ├─ Filtrar con ML (si disponible)
   ├─ Calcular tamaño de posición
   ├─ Ejecutar orden
   └─ Gestionar posiciones activas
       ├─ Break-even (1R)
       ├─ Trailing stop (1.5R+)
       ├─ Time-based stops
       └─ Cierre por fin de día

3️⃣ AL CERRAR POSICIÓN
   ├─ Calcular PnL, MFE, MAE
   ├─ Registrar en CSV con todas las features
   └─ Datos listos para re-entrenar modelo
```

---

## 📈 Monitoreo

### **Dashboard Web**
Accede a: `http://localhost:8000`

Muestra:
- ✅ Posiciones abiertas en tiempo real
- ✅ Gráfico de precios con indicadores
- ✅ PnL diario y acumulado
- ✅ Régimen de mercado actual
- ✅ Parámetros adaptados
- ✅ Historial de trades

### **Logs**
```bash
tail -f logs/trading_bot.log
```

---

## 🧠 Machine Learning

### **¿Cómo Funciona?**

1. **Recolección de Datos**
   - El bot registra CADA señal que genera
   - Guarda contexto completo (indicadores, régimen, hora, etc.)
   - Etiqueta resultado: 1 = exitoso (≥1R), 0 = no exitoso

2. **Entrenamiento**
   - Modelo: Random Forest Classifier
   - Input: 24 features (técnicas + contexto + estado)
   - Output: Probabilidad de éxito (0-100%)

3. **Filtrado en Vivo**
   - Cada señal pasa por el modelo
   - Si p_win < 55% → Rechazada
   - Si p_win ≥ 55% → Aprobada
   - Si p_win ≥ 70% → Tamaño aumentado +30%

### **Entrenar el Modelo**

Después de al menos **50 operaciones** registradas:

```bash
python train_ml_model.py
```

El script mostrará:
- ✅ Accuracy del modelo
- ✅ ROC AUC Score
- ✅ Features más importantes
- ✅ Confusion Matrix
- ✅ Cross-validation scores

### **Interpretación de Resultados**

| Métrica | Bueno | Excelente |
|---------|-------|-----------|
| Accuracy | >60% | >70% |
| ROC AUC | >0.65 | >0.75 |
| Precision (clase 1) | >0.60 | >0.70 |
| Recall (clase 1) | >0.50 | >0.65 |

---

## 🔧 Configuración Avanzada

### **Ajustar Trailing Stop**
Edita `src/risk/advanced_position_manager.py`:

```python
self.trailing_start_r = 1.5      # Activar en 1.5R (puedes poner 1.0, 2.0, etc.)
self.trailing_atr_multiplier = 1.0  # Distancia de 1 ATR (puedes aumentar a 1.5)
```

### **Ajustar Break-Even**
```python
self.breakeven_trigger_r = 1.0   # Activar en 1R (puedes poner 0.5, 1.5, etc.)
self.breakeven_buffer = 0.001    # 0.1% por encima de entrada
```

### **Ajustar Umbrales ML**
Edita `src/ml/ml_signal_filter.py`:

```python
self.min_probability = 0.55  # Mínimo 55% (puedes subir a 0.60 para ser más selectivo)
self.high_probability = 0.70 # 70%+ = señal muy fuerte
```

### **Personalizar Parámetros por Régimen**
Edita `src/strategy/dynamic_parameters.py`:

Cada método `_adapt_X` define los parámetros para ese régimen.

---

## 📋 Indicadores Técnicos Usados

| Indicador | Período | Uso |
|-----------|---------|-----|
| EMA Rápida | 9 | Detección de tendencia |
| EMA Lenta | 21 | Detección de tendencia |
| RSI | 14 | Sobrecompra/sobreventa |
| MACD | 12/26/9 | Confirmación de momentum |
| ATR | 14 | Volatilidad y stops dinámicos |
| VWAP | Intradiario | Confirmación de dirección |
| EMA 50/200 | 50/200 | Clasificación de régimen |

---

## 🎓 Mejores Prácticas

### **1. Empezar en Paper Trading**
```env
TRADING_MODE=PAPER
BINANCE_TESTNET=true
```

### **2. Acumular Datos Primero**
- Ejecuta el bot por **1-2 semanas** sin ML
- Acumula al menos **100 operaciones**
- Luego entrena el modelo

### **3. Re-entrenar Periódicamente**
- Cada **1-2 semanas** con nuevos datos
- Verifica que el accuracy no baje
- Si baja, revisa si cambió el régimen de mercado

### **4. Monitorear Métricas Clave**
- **Win Rate**: Idealmente >50%
- **Expectativa**: (Avg Win × Win Rate) - (Avg Loss × Loss Rate) > 0
- **Max Drawdown**: <10% del capital
- **Profit Factor**: >1.5

### **5. Adaptar al Mercado**
- Usa **timeframes más largos** (15m, 1h) en mercados volátiles
- Usa **timeframes más cortos** (1m, 5m) en mercados tranquilos
- Ajusta `RISK_PER_TRADE` según tu tolerancia al riesgo

---

## 🐛 Troubleshooting

### **"Datos históricos insuficientes"**
- Verifica tu conexión con Binance
- Verifica que el símbolo sea correcto (ej: BTC/USDT)
- Verifica que el timeframe sea válido (1m, 5m, 15m, 1h, 4h, 1d)

### **"Modelo ML no encontrado"**
- Normal al inicio. El bot operará sin ML
- Ejecuta `python train_ml_model.py` cuando tengas suficientes datos

### **"No se generan señales"**
- Mercado puede estar en condiciones no operables
- Verifica logs para ver qué filtros están bloqueando
- Ajusta `min_signal_strength` en los parámetros dinámicos

### **"Posiciones no se cierran"**
- Verifica que el `order_executor` esté funcionando
- Verifica logs del `advanced_position_manager`
- Asegúrate que el precio esté actualizándose

---

## 📊 Estructura de Archivos

```
daily-trading/
├── main.py                          # 🚀 Archivo principal (START HERE)
├── config.py                        # ⚙️ Configuración
├── train_ml_model.py               # 🧠 Entrenamiento ML
├── src/
│   ├── strategy/
│   │   ├── trading_strategy.py     # 📈 Estrategia técnica
│   │   ├── market_regime.py        # 🔍 Clasificador de régimen
│   │   └── dynamic_parameters.py   # 🔧 Parámetros adaptativos
│   ├── risk/
│   │   ├── risk_manager.py         # 🛡️ Gestión de riesgo básica
│   │   └── advanced_position_manager.py  # 🎯 Trailing, BE, etc.
│   ├── ml/
│   │   ├── ml_signal_filter.py     # 🧠 Filtro ML
│   │   ├── trade_recorder.py       # 📝 Logging completo
│   │   ├── ml_model.py             # 🤖 Modelo base
│   │   └── trading_history.csv     # 📊 Datos de entrenamiento
│   ├── data/
│   │   └── market_data.py          # 📥 Proveedor de datos
│   ├── execution/
│   │   └── order_executor.py       # 💼 Ejecución de órdenes
│   └── monitoring/
│       └── dashboard.py            # 📊 Dashboard web
├── models/
│   └── signal_filter_model.pkl     # 🧠 Modelo entrenado
└── logs/
    └── trading_bot.log             # 📝 Logs del sistema
```

---

## 🎯 Roadmap Futuro

- [ ] Multi-símbolo (operar varios pares simultáneamente)
- [ ] Más modelos ML (LSTM, XGBoost)
- [ ] Optimización de hiperparámetros automática
- [ ] Backtesting con régimen de mercado
- [ ] Integración con más exchanges
- [ ] Señales de Telegram en tiempo real
- [ ] Análisis de correlación entre activos

---

## 📞 Soporte

Para preguntas o problemas:
1. Revisa los logs: `logs/trading_bot.log`
2. Verifica la configuración en `.env`
3. Consulta este README

---

## ⚠️ Disclaimer

Este bot es una herramienta educativa y de investigación. El trading automatizado conlleva riesgos significativos. **NUNCA** arriesgues más de lo que puedes permitirte perder.

- ✅ Empieza con paper trading
- ✅ Testea extensivamente
- ✅ Monitorea constantemente
- ✅ Ajusta según resultados

**El rendimiento pasado no garantiza resultados futuros.**

---

## 📜 Licencia

MIT License - Uso libre bajo tu propio riesgo.

---

**¡Happy Trading! 🚀📈**

