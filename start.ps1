# ===============================
# Bot de Trading - Inicio Rápido (PowerShell)
# ===============================

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   🚀 Iniciando Bot de Trading...           ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Cambiar al directorio del proyecto
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptPath\daily-trading"

# Verificar que el archivo existe
if (-not (Test-Path "main.py")) {
    Write-Host "❌ Error: No se encontró el archivo main.py" -ForegroundColor Red
    Write-Host "Verifica que estás en el directorio correcto" -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Activar entorno virtual
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "✅ Activando entorno virtual..." -ForegroundColor Green
    & "venv\Scripts\Activate.ps1"
    Write-Host ""
} else {
    Write-Host "⚠️  Advertencia: No se encontró el entorno virtual" -ForegroundColor Yellow
    Write-Host "Intentando ejecutar con Python del sistema..." -ForegroundColor Yellow
    Write-Host ""
}

# Ejecutar el bot principal
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "📡 Ejecutando Bot de Trading..." -ForegroundColor White
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

python main.py

# Desactivar entorno virtual si estaba activado
if ($env:VIRTUAL_ENV) {
    deactivate
}

Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ Programa finalizado" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Read-Host "Presiona Enter para salir"

