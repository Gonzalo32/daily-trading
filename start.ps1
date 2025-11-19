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

# Ejecutar el bot principal
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "📡 Ejecutando Bot de Trading..." -ForegroundColor White
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Usar Python del entorno virtual si existe, sino del sistema
$pythonPath = "python"
if (Test-Path "venv\Scripts\python.exe") {
    $pythonPath = "venv\Scripts\python.exe"
    Write-Host "✅ Usando Python del entorno virtual" -ForegroundColor Green
} else {
    Write-Host "⚠️  Usando Python del sistema" -ForegroundColor Yellow
}

& $pythonPath main.py

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

