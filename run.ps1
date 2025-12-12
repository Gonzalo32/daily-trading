# ===============================
# Bot de Trading - Comando RUN (PowerShell)
# ===============================

Write-Host ""
Write-Host "Ejecutando Bot de Trading..." -ForegroundColor Cyan
Write-Host ""

# Obtener la ruta del script actual de forma robusta
$scriptPath = $null

# Intentar diferentes métodos para obtener la ruta
if ($PSScriptRoot) {
    $scriptPath = $PSScriptRoot
} elseif ($MyInvocation.MyCommand.Path) {
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    # Si no se puede determinar, usar la ruta actual
    $scriptPath = Get-Location
}

# Cambiar al directorio del proyecto
$projectPath = Join-Path $scriptPath "daily-trading"

# Si el directorio daily-trading no existe, asumir que ya estamos en él
if (-not (Test-Path $projectPath)) {
    $currentPath = Get-Location
    if (Test-Path (Join-Path $currentPath "main.py")) {
        $projectPath = $currentPath
    } elseif (Test-Path (Join-Path $currentPath "daily-trading\main.py")) {
        $projectPath = Join-Path $currentPath "daily-trading"
    } else {
        Write-Host "Error: No se encontro el directorio daily-trading" -ForegroundColor Red
        Write-Host "Ruta esperada: $projectPath" -ForegroundColor Yellow
        Write-Host "Directorio actual: $currentPath" -ForegroundColor Yellow
        Read-Host "Presiona Enter para salir"
        exit 1
    }
}

# Cambiar al directorio del proyecto
Set-Location $projectPath
$projectPath = Get-Location

# Verificar que el archivo existe
if (-not (Test-Path "main.py")) {
    Write-Host "Error: No se encontro el archivo main.py" -ForegroundColor Red
    Write-Host "Directorio actual: $projectPath" -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Activar entorno virtual
$venvPath = Join-Path $projectPath "venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
    Write-Host "Entorno virtual activado" -ForegroundColor Green
} else {
    Write-Host "Error: No se encontro el entorno virtual." -ForegroundColor Red
    Write-Host "Ruta esperada: $venvPath" -ForegroundColor Yellow
    Write-Host "Por favor, crea el entorno virtual primero con: python -m venv venv" -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Ejecutar el bot principal
Write-Host ""
Write-Host "Ejecutando Bot de Trading..." -ForegroundColor Cyan
Write-Host ""

# Usar Python del entorno virtual
$pythonPath = Join-Path $projectPath "venv\Scripts\python.exe"
if (Test-Path $pythonPath) {
    & $pythonPath main.py
} else {
    Write-Host "Usando Python del sistema" -ForegroundColor Yellow
    python main.py
}

# Desactivar entorno virtual si estaba activado
if ($env:VIRTUAL_ENV) {
    deactivate
}

Write-Host ""
Write-Host "Programa finalizado" -ForegroundColor Green
Write-Host ""

Read-Host "Presiona Enter para salir"
