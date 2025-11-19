# ===============================
# Configurar alias en PowerShell
# ===============================

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   🔧 Configurando PowerShell...            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Obtener la ruta del directorio actual
$currentDir = Get-Location
$startScript = "$currentDir\start.ps1"

Write-Host "📂 Directorio actual: $currentDir" -ForegroundColor Yellow
Write-Host ""

# Verificar si existe el perfil de PowerShell
$profilePath = $PROFILE.CurrentUserCurrentHost

if (-not (Test-Path $profilePath)) {
    Write-Host "📝 Creando perfil de PowerShell..." -ForegroundColor Green
    New-Item -Path $profilePath -Type File -Force | Out-Null
}

# Crear la función en el perfil
$functionCode = @"

# ═══════════════════════════════════════════════════════
# Alias para Bot de Trading
# ═══════════════════════════════════════════════════════
function Start-TradingBot {
    Set-Location '$currentDir'
    & '$startScript'
}

Set-Alias -Name bot -Value Start-TradingBot -Scope Global -Force

"@

# Agregar al perfil si no existe ya
$profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue

if ($profileContent -notlike "*Start-TradingBot*") {
    Add-Content -Path $profilePath -Value $functionCode
    Write-Host "✅ Alias 'bot' agregado al perfil de PowerShell" -ForegroundColor Green
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "🎉 ¡Configuración completada!" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Ahora puedes usar el comando:" -ForegroundColor White
    Write-Host "  bot" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Desde CUALQUIER ubicación en PowerShell" -ForegroundColor White
    Write-Host ""
    Write-Host "⚠️  IMPORTANTE: Cierra y vuelve a abrir PowerShell" -ForegroundColor Yellow
    Write-Host "    para que los cambios tengan efecto." -ForegroundColor Yellow
} else {
    Write-Host "ℹ️  El alias ya existe en el perfil" -ForegroundColor Cyan
}

Write-Host ""
Read-Host "Presiona Enter para salir"

