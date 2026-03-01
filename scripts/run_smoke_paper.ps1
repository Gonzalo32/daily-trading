$envFile = Join-Path (Get-Location) ".env"
if (-not (Test-Path $envFile)) {
    $envExample = Join-Path (Get-Location) "env.example"
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile -Force
    }
}

python scripts/smoke_paper.py
exit $LASTEXITCODE
