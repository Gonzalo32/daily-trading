# 🔄 Reiniciar el Bot de Trading

## ⚠️ IMPORTANTE: Cambios Aplicados

Se han realizado mejoras críticas para obtener **datos reales de Binance**:

1. ✅ **Conexión a Binance para datos públicos** (sin necesidad de API keys en modo PAPER)
2. ✅ **Inicialización correcta de MarketDataProvider** al arrancar el bot
3. ✅ **Manejo mejorado de errores** con reintentos automáticos
4. ✅ **Datos completos del mercado** (precio, OHLCV, volumen, cambios)

## 🛑 Detener el Bot Actual

### Opción 1: PowerShell (Recomendado)
```powershell
# Detener procesos de Python relacionados con el bot
Get-Process python* | Where-Object {$_.Path -like "*daily-trading*"} | Stop-Process -Force

# O detener por puerto (si el dashboard está corriendo)
$port = 8000
$process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($process) {
    Stop-Process -Id $process -Force
    Write-Host "✅ Proceso en puerto $port detenido" -ForegroundColor Green
}
```

### Opción 2: Desde el Terminal donde corre el bot
Presiona `Ctrl+C` para detener el bot de forma segura.

## 🚀 Reiniciar el Bot

### Opción 1: Script de Inicio (Recomendado)
```powershell
Set-Location "C:\Users\Administrador\Desktop\daily-trading\daily-trading"
.\start.bat
```

### Opción 2: PowerShell Directo
```powershell
Set-Location "C:\Users\Administrador\Desktop\daily-trading\daily-trading"
Write-Host "`n🚀 Reiniciando el bot...`n" -ForegroundColor Green
.\venv\Scripts\python.exe main.py
```

### Opción 3: Desde el directorio del bot
```powershell
cd "C:\Users\Administrador\Desktop\daily-trading\daily-trading"
.\venv\Scripts\python.exe main.py
```

## ✅ Verificar que Funciona Correctamente

Después de reiniciar, verifica en los logs:

1. **Conexión a Binance:**
   ```
   ✅ MarketData: Conexión con Binance establecida | Modo: PAPER (datos públicos)
   🔧 Usando Binance Real (datos públicos)
   ✅ Test de conexión OK | Precio actual BTC/USDT: [precio real]
   ```

2. **Inicialización de componentes:**
   ```
   🔧 Inicializando componentes...
   📊 Inicializando MarketDataProvider...
   ✅ MarketDataProvider inicializado con conexión a Binance
   ```

3. **Precios reales en el dashboard:**
   - Abre `http://localhost:8000`
   - El precio de BTC/USDT debe actualizarse constantemente (no quedarse en 50000)
   - Los indicadores (RSI, EMA) deben cambiar con el tiempo

4. **Logs de precio real:**
   ```
   📊 Precio real obtenido: BTC/USDT @ [precio actual]
   ```

## 🔍 Si Aún Ves Precio Simulado (50000)

Si después de reiniciar sigues viendo el precio fijo de 50000:

1. **Verifica los logs** para ver si hay errores de conexión:
   ```powershell
   Get-Content "C:\Users\Administrador\Desktop\daily-trading\daily-trading\logs\trading_bot.log" | Select-String -Pattern "Binance|exchange|Error|precio" | Select-Object -Last 20
   ```

2. **Verifica tu conexión a Internet** - El bot necesita conectarse a Binance

3. **Verifica el símbolo** en tu `.env`:
   ```
   SYMBOL=BTC/USDT
   ```

4. **Revisa si hay firewall bloqueando** la conexión a Binance

## 📊 Verificar Transacciones

El bot debería:
- ✅ Obtener precios reales de Binance cada ciclo
- ✅ Calcular indicadores técnicos basados en precios reales
- ✅ Mostrar datos actualizados en el dashboard
- ✅ Generar señales de trading basadas en datos reales

**Nota:** En modo PAPER, las transacciones son simuladas pero usan datos reales del mercado.
