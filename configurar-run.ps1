# Configurar comando RUN en PowerShell

Write-Host ""
Write-Host "Configurando comando RUN..." -ForegroundColor Cyan
Write-Host ""

# Obtener la ruta del directorio actual
$currentDir = Get-Location
$runScript = "$currentDir\run.ps1"

Write-Host "Directorio del proyecto: $currentDir" -ForegroundColor Yellow
Write-Host ""

# Verificar que existe el script run.ps1
if (-not (Test-Path $runScript)) {
    Write-Host "Error: No se encontro el archivo run.ps1" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Verificar si existe el perfil de PowerShell
$profilePath = $PROFILE.CurrentUserCurrentHost

if (-not (Test-Path $profilePath)) {
    Write-Host "Creando perfil de PowerShell..." -ForegroundColor Green
    $profileDir = Split-Path -Parent $profilePath
    if (-not (Test-Path $profileDir)) {
        New-Item -Path $profileDir -Type Directory -Force | Out-Null
    }
    New-Item -Path $profilePath -Type File -Force | Out-Null
}

# Crear la funcion en el perfil
$functionCode = @"

# Comando RUN para Bot de Trading
function Start-RunTradingBot {
    `$projectRoot = '$currentDir'
    `$runScript = Join-Path `$projectRoot 'run.ps1'
    if (Test-Path `$runScript) {
        Set-Location `$projectRoot
        & `$runScript
    } else {
        Write-Host "Error: No se encontro run.ps1 en `$projectRoot" -ForegroundColor Red
    }
}

Set-Alias -Name run -Value Start-RunTradingBot -Scope Global -Force

"@

# Agregar al perfil si no existe ya
$profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
$exists = $false

if ($null -ne $profileContent) {
    $exists = $profileContent.Contains("Start-RunTradingBot")
}

if (-not $exists) {
    Add-Content -Path $profilePath -Value $functionCode
    Write-Host "Comando 'run' agregado al perfil de PowerShell" -ForegroundColor Green
    Write-Host ""
    Write-Host "Configuracion completada!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ahora puedes usar el comando: run" -ForegroundColor White
    Write-Host "Desde CUALQUIER ubicacion en PowerShell" -ForegroundColor White
    Write-Host ""
    Write-Host "IMPORTANTE: Cierra y vuelve a abrir PowerShell" -ForegroundColor Yellow
    Write-Host "para que los cambios tengan efecto." -ForegroundColor Yellow
} else {
    Write-Host "El comando 'run' ya existe en el perfil" -ForegroundColor Cyan
}

Write-Host ""
Read-Host "Presiona Enter para salir"
