# 🤖 Bot de Day Trading Automatizado

Bot de trading automatizado con Machine Learning, gestión avanzada de riesgo y persistencia de estado. Soporta crypto (Binance) y stocks (Alpaca) en modo PAPER y LIVE.

## 🎯 Características

- ✅ **Estrategia técnica:** EMA + RSI con filtros avanzados
- ✅ **Gestión de riesgo:** Position sizing basado en ATR, stop-loss/take-profit dinámicos
- ✅ **Machine Learning:** Filtro ML para mejorar señales (opcional)
- ✅ **Persistencia:** Estado guardado en `state.json` (equity, PnL, trades)
- ✅ **Modo MVP:** Acumula datos (hasta 500 trades) antes de activar ML completo
- ✅ **Dashboard:** Monitoreo web en tiempo real
- ✅ **Paper Trading:** Simula trading sin riesgo real
- ✅ **Multi-mercado:** Crypto (Binance) y Stocks (Alpaca)

---

## 🚀 Setup Rápido (Nueva Computadora)

### 1️⃣ Clonar el repositorio

```bash
git clone <tu-repo-url>
cd daily-trading
```

### 2️⃣ Crear entorno virtual

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Instalar dependencias

```bash
cd daily-trading
pip install -r requirements.txt
```

**Dependencias principales:**
- `ccxt` - Conexión con exchanges de crypto
- `pandas` - Análisis de datos
- `numpy` - Cálculos numéricos
- `scikit-learn` - Machine Learning
- `fastapi` - Dashboard web
- `joblib` - Persistencia de modelos

**Nota:** TensorFlow es opcional (solo para features ML avanzadas)

### 4️⃣ Configurar variables de entorno (opcional)

```bash
# Copiar ejemplo de configuración
cp env.example .env

# Editar .env con tus valores
# Para modo PAPER no necesitas API keys
```

### 5️⃣ Ejecutar el bot

**Windows:**
```cmd
start.bat
```

**O manualmente:**
```bash
cd daily-trading
python main.py
```

---

## 📁 Estructura del Proyecto

```
daily-trading/
├── daily-trading/           # Código principal del bot
│   ├── main.py             # 🔥 Entrypoint oficial
│   ├── config.py           # Configuración centralizada
│   ├── requirements.txt    # Dependencias Python
│   ├── src/                # Código fuente
│   │   ├── data/           # Market data provider
│   │   ├── strategy/       # Estrategia de trading
│   │   ├── risk/           # Gestión de riesgo
│   │   ├── execution/      # Ejecución de órdenes
│   │   ├── ml/             # Machine Learning
│   │   ├── monitoring/     # Dashboard web
│   │   ├── state/          # Persistencia de estado
│   │   └── utils/          # Utilidades (logging, etc.)
│   ├── logs/               # Logs del bot (gitignored)
│   ├── models/             # Modelos ML (gitignored)
│   ├── state.json          # Estado persistido (gitignored)
│   └── state.json.example  # Ejemplo de estado
├── tools/                  # Scripts de diagnóstico
├── start.bat               # Launcher Windows
├── env.example             # Ejemplo de configuración
├── .gitignore              # Archivos ignorados
└── README.md               # Este archivo
```

---

## ⚙️ Configuración

### Variables de Entorno (archivo `.env`)

```bash
# Modo de operación
TRADING_MODE=PAPER          # PAPER o LIVE
MARKET=CRYPTO               # CRYPTO o STOCK
SYMBOL=BTC/USDT             # Símbolo a operar

# Capital y riesgo
INITIAL_CAPITAL=10000       # Capital inicial
RISK_PER_TRADE=0.02         # 2% riesgo por trade
MAX_DAILY_LOSS=0.03         # 3% pérdida máxima diaria
MAX_DAILY_TRADES=20         # Límite de trades/día

# Binance (crypto)
BINANCE_TESTNET=true        # true=testnet, false=live
BINANCE_API_KEY=            # (vacío para PAPER)
BINANCE_SECRET_KEY=         # (vacío para PAPER)

# Machine Learning
ENABLE_ML=true              # Activar filtro ML
ML_MIN_PROBABILITY=0.55     # Probabilidad mínima

# Logging
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
ENABLE_DASHBOARD=true       # Dashboard en :8000
```

Ver `env.example` para configuración completa.

---

## 🧪 Verificación Post-Setup

Ejecuta estos tests para confirmar que todo funciona:

### Test 1: Import básico
```bash
cd daily-trading
python -c "import main; print('✅ OK')"
```

### Test 2: Dependencias
```bash
python -m pip check
```

### Test 3: Configuración
```bash
python -c "from config import Config; c = Config(); print(f'✅ Config OK: {c.TRADING_MODE}')"
```

Si todos pasan ✅, estás listo para ejecutar el bot.

---

## 📊 Modo MVP (Acumulación de Datos)

El bot inicia en **Modo MVP** hasta acumular 500 trades:

- ✅ Genera señales básicas (EMA + RSI)
- ✅ Guarda todos los trades en `training_data.csv`
- ❌ ML desactivado temporalmente (insuficientes datos)
- ⚠️ Límites más permisivos (20 trades/día)

**Progreso:** Se muestra al iniciar
```
📊 Trades históricos: 203 / 500
🎯 OBJETIVO: Acumular 500+ trades para entrenar ML
```

Una vez alcanzados 500 trades, el modo MVP se desactiva automáticamente y el filtro ML se activa.

---

## 🛡️ Seguridad y Riesgos

### ⚠️ IMPORTANTE

1. **Modo PAPER primero:** Siempre prueba en PAPER durante semanas
2. **Testnet antes de LIVE:** Si vas a usar crypto LIVE, prueba en testnet primero
3. **Capital pequeño:** Empieza con capital mínimo en LIVE
4. **Monitorea 24/7:** Nunca dejes el bot sin supervisión en LIVE
5. **API Keys:** NUNCA compartas tus API keys ni las subas a git

### Archivos sensibles (en `.gitignore`)

- `.env` - API keys y configuración
- `state.json` - Estado del bot
- `logs/` - Logs con detalles de operaciones
- `models/` - Modelos ML entrenados
- `training_data.csv` - Datos de trades

---

## 📈 Dashboard

El dashboard web se ejecuta automáticamente en:

```
http://localhost:8000
```

Muestra en tiempo real:
- Posiciones abiertas
- PnL diario y total
- Trades ejecutados
- Estado del sistema

---

## 🔧 Troubleshooting

### Error: `ModuleNotFoundError`
```bash
# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: `'charmap' codec can't encode`
✅ Ya está solucionado en `start.bat` (UTF-8 encoding)

### Error: `MLSignalFilter has no attribute 'is_model_available'`
✅ Ya está solucionado (verificación robusta de ML)

### Error: Size inflado (0.011 → 10.646 BTC)
✅ Ya está solucionado (fórmula de sizing corregida)

### Bot no guarda estado entre reinicios
✅ Verificar que existe `state.json` y `StateManager` está activo

---

## 📚 Documentación Adicional

- `CAMBIOS_UNIFICACION_PNL.md` - Cambios de estabilización recientes
- `ENTRYPOINT.md` - Documentación del entrypoint oficial
- `INSTRUCCIONES_EJECUCION.md` - Instrucciones detalladas de ejecución
- `PERSISTENCIA_IMPLEMENTADA.md` - Detalles de persistencia de estado
- `daily-trading/README.md` - README del módulo principal
- `daily-trading/README_ANALISIS.md` - Análisis técnico del sistema

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama: `git checkout -b feature/nueva-feature`
3. Commit: `git commit -m 'Add nueva feature'`
4. Push: `git push origin feature/nueva-feature`
5. Abre un Pull Request

---

## ⚖️ Licencia

Este proyecto es de uso personal/educativo. **NO garantiza ganancias.** El trading conlleva riesgos.

---

## 📞 Soporte

- Issues: [GitHub Issues]
- Documentación: Ver `/docs` y archivos `.md`
- Logs: Revisar `daily-trading/logs/trading_bot.log`

---

## 🎯 Roadmap

- [x] Estrategia EMA + RSI
- [x] Gestión de riesgo avanzada
- [x] Persistencia de estado
- [x] Filtro ML básico
- [x] Dashboard web
- [x] Modo MVP
- [ ] Backtest automático
- [ ] Multi-símbolo
- [ ] Notificaciones avanzadas
- [ ] ML avanzado (deep learning)

---

**🟢 Versión actual: Estable y operativa**

Última actualización: 2026-01-12
