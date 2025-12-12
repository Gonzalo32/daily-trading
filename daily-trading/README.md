# 🤖 Bot de Day Trading Automatizado

Un bot de trading automatizado completamente funcional que opera en mercados de criptomonedas y acciones, implementando estrategias de trading algorítmico con gestión de riesgo avanzada.

## 🚀 Características Principales

- **Trading Automatizado**: Operaciones 24/7 sin supervisión constante
- **Múltiples Mercados**: Soporte para criptomonedas (Binance) y acciones (Alpaca)
- **Estrategia Inteligente**: Basada en cruce de medias móviles con confirmación RSI y MACD
- **Gestión de Riesgo**: Stop loss, take profit, límites diarios y control de exposición
- **Dashboard en Tiempo Real**: Interfaz web para monitoreo del bot
- **Notificaciones**: Alertas por Telegram y consola
- **Backtesting**: Pruebas con datos históricos antes del trading real
- **Machine Learning**: Capacidad de aprendizaje y adaptación (opcional)

## 📋 Requisitos del Sistema

- Python 3.8 o superior
- Windows 10/11, macOS o Linux
- Conexión a internet estable
- Mínimo 4GB RAM
- 1GB espacio en disco

## 🛠️ Instalación

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/daily-trading.git
cd daily-trading
```

### 2. Crear Entorno Virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

```bash
cp env.example .env
```

Edita el archivo `.env` con tus configuraciones:

```env
# Modo de Trading
TRADING_MODE=PAPER  # PAPER para simulación, LIVE para trading real

# Configuración de Mercado
MARKET=CRYPTO
SYMBOL=BTC/USDT

# API Keys (obtén las tuyas)
BINANCE_API_KEY=tu_api_key_aqui
BINANCE_SECRET_KEY=tu_secret_key_aqui
BINANCE_TESTNET=True

# Notificaciones
TELEGRAM_BOT_TOKEN=tu_bot_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

## 🚀 Uso Rápido

### 1. Modo Simulación (Paper Trading)

```bash
python main.py
```

El bot comenzará a operar en modo simulación usando datos reales pero sin dinero real.

### 2. Modo Real (Trading con Dinero Real)

⚠️ **ADVERTENCIA**: Solo usa dinero que puedas permitirte perder.

```bash
# Cambiar en .env
TRADING_MODE=LIVE
BINANCE_TESTNET=False

# Ejecutar
python main.py
```

### 3. Dashboard Web

Accede a `http://localhost:8000` para ver el dashboard en tiempo real.

## 📊 Estrategia de Trading

### Indicadores Técnicos

- **Medias Móviles**: Cruce de MA rápida (5) y MA lenta (20)
- **RSI**: Confirmación de momentum (14 períodos)
- **MACD**: Divergencia de convergencia de medias móviles
- **ATR**: Volatilidad para ajustar stops dinámicos

### Reglas de Entrada

**Compra (BUY)**:
- MA rápida cruza por encima de MA lenta
- RSI < 70 (no sobrecomprado)
- MACD > 0 y MACD > Señal

**Venta (SELL)**:
- MA rápida cruza por debajo de MA lenta
- RSI > 30 (no sobrevendido)
- MACD < 0 y MACD < Señal

### Gestión de Riesgo

- **Stop Loss**: 1% del precio de entrada
- **Take Profit**: 2:1 ratio (2% ganancia por 1% riesgo)
- **Riesgo por Trade**: 2% del capital
- **Límite Diario**: 3% pérdida máxima por día
- **Posiciones Máximas**: 3 simultáneas

## 🔧 Configuración Avanzada

### Parámetros de Estrategia

```env
# Medias Móviles
FAST_MA_PERIOD=5
SLOW_MA_PERIOD=20

# RSI
RSI_PERIOD=14
RSI_OVERBOUGHT=70
RSI_OVERSOLD=30

# Stop Loss y Take Profit
STOP_LOSS_PCT=0.01
TAKE_PROFIT_RATIO=2.0
```

### Gestión de Riesgo

```env
# Límites de Riesgo
MAX_POSITIONS=3
MAX_DAILY_LOSS=0.03
MAX_DAILY_GAIN=0.05
RISK_PER_TRADE=0.02
```

### Notificaciones

```env
# Telegram
ENABLE_NOTIFICATIONS=True
TELEGRAM_BOT_TOKEN=tu_bot_token
TELEGRAM_CHAT_ID=tu_chat_id
```

## 📈 Backtesting

Prueba tu estrategia con datos históricos:

```bash
python backtest.py --start-date 2023-01-01 --end-date 2023-12-31
```

## 🤖 Machine Learning (Opcional)

Habilita el aprendizaje automático:

```env
ENABLE_ML=True
ML_MODEL_PATH=models/
RETRAIN_FREQUENCY=7
```

## 📱 Notificaciones

### Telegram

1. Crea un bot con [@BotFather](https://t.me/botfather)
2. Obtén tu `TELEGRAM_BOT_TOKEN`
3. Obtén tu `TELEGRAM_CHAT_ID` con [@userinfobot](https://t.me/userinfobot)
4. Configura en `.env`

### Tipos de Notificaciones

- ✅ Operaciones ejecutadas
- 💰 Posiciones cerradas
- ⚠️ Alertas de riesgo
- 📊 Resumen diario
- 🚨 Emergencias

## 🛡️ Seguridad

### Mejores Prácticas

1. **Nunca compartas tus API keys**
2. **Usa modo PAPER primero**
3. **Comienza con capital pequeño**
4. **Monitorea regularmente**
5. **Mantén backups del código**

### Configuración de API

- **Binance**: Usa testnet para pruebas
- **Alpaca**: Usa paper trading para pruebas
- **Permisos**: Solo trading, no retiros

## 📊 Monitoreo

### Dashboard Web

- Estado del bot en tiempo real
- Posiciones abiertas
- Métricas de rendimiento
- Gráficos de precios
- Alertas y notificaciones

### Logs

```bash
tail -f logs/trading_bot.log
```

### Métricas Clave

- **PnL Diario**: Ganancia/pérdida del día
- **Win Rate**: Porcentaje de operaciones ganadoras
- **Sharpe Ratio**: Rendimiento ajustado por riesgo
- **Max Drawdown**: Pérdida máxima desde picos
- **Exposición**: Porcentaje del capital en riesgo

## 🔄 Mantenimiento

### Actualizaciones Regulares

```bash
git pull origin main
pip install -r requirements.txt
```

### Limpieza de Logs

```bash
# Limpiar logs antiguos
find logs/ -name "*.log" -mtime +30 -delete
```

### Backup de Configuración

```bash
cp .env .env.backup
```

## 🐛 Solución de Problemas

### Errores Comunes

1. **Error de API Key**: Verifica las credenciales en `.env`
2. **Conexión perdida**: Verifica tu conexión a internet
3. **Error de balance**: Verifica que tengas fondos suficientes
4. **Error de símbolo**: Verifica que el símbolo sea válido

### Logs de Debug

```env
LOG_LEVEL=DEBUG
```

### Reinicio del Bot

```bash
# Detener
Ctrl+C

# Reiniciar
python main.py
```

## 📚 Documentación

### Estructura del Proyecto

```
daily-trading/
├── main.py                 # Archivo principal
├── config.py              # Configuración
├── requirements.txt       # Dependencias
├── env.example           # Variables de entorno ejemplo
├── src/
│   ├── data/            # Datos de mercado
│   ├── strategy/        # Estrategias de trading
│   ├── risk/           # Gestión de riesgo
│   ├── execution/      # Ejecución de órdenes
│   ├── monitoring/     # Dashboard y monitoreo
│   ├── utils/          # Utilidades
│   └── ml/             # Machine learning
├── models/             # Modelos ML
└── logs/              # Archivos de log
```

### API Reference

- [Documentación de Binance API](https://binance-docs.github.io/apidocs/)
- [Documentación de Alpaca API](https://alpaca.markets/docs/)
- [Documentación de CCXT](https://ccxt.readthedocs.io/)

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## ⚠️ Disclaimer

Este software es solo para fines educativos y de investigación. El trading conlleva riesgos significativos y puede resultar en pérdidas. Nunca inviertas dinero que no puedas permitirte perder. Los desarrolladores no se hacen responsables de ninguna pérdida financiera.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🆘 Soporte

- 📧 Email: soporte@tradingbot.com
- 💬 Telegram: [@TradingBotSupport](https://t.me/TradingBotSupport)
- 🐛 Issues: [GitHub Issues](https://github.com/tu-usuario/daily-trading/issues)

---

**¡Buena suerte con tu trading automatizado! 🚀📈**
