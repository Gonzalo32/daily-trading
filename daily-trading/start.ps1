# ===============================
# Bot de Trading - Inicio Rápido (PowerShell)
# ===============================
# Desde: C:\Users\Administrador\Desktop\daily-trading
# Ejecutar: .\start
# ===============================

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   🚀 Bot de Trading - Iniciando...        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "daily-trading\main.py")) {
    Write-Host "❌ Error: No se encontró daily-trading\main.py" -ForegroundColor Red
    Write-Host ""
    Write-Host "Estructura esperada:"
    Write-Host "  daily-trading\"
    Write-Host "  ├── main.py"
    Write-Host "  └── venv\"
    Write-Host ""
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Verificar que existe el entorno virtual
if (-not (Test-Path "daily-trading\venv\Scripts\python.exe")) {
    Write-Host "❌ Error: No se encontró el entorno virtual" -ForegroundColor Red
    Write-Host ""
    Write-Host "Por favor ejecuta primero: .\setup_windows.bat" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Presiona Enter para salir"
    exit 1
}

Write-Host "✅ Directorio verificado" -ForegroundColor Green
Write-Host "✅ Entorno virtual encontrado" -ForegroundColor Green
Write-Host ""

# Cambiar al directorio del bot
Set-Location "daily-trading"

Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "📡 Iniciando bot de trading..." -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Ejecutar usando Python del venv directamente
& ".\venv\Scripts\python.exe" main.py

# Verificar el código de salida
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════" -ForegroundColor Red
    Write-Host "❌ El bot terminó con un error" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════════" -ForegroundColor Red
} else {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════" -ForegroundColor Green
    Write-Host "✅ Bot finalizado correctamente" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════" -ForegroundColor Green
}

Write-Host ""
Read-Host "Presiona Enter para salir"
