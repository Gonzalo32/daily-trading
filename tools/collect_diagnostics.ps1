# tools/collect_diagnostics.ps1
# Genera un reporte reproducible del estado del proyecto (runtime, imports, entrypoints, lint, data ML).
# Output: diagnostics\REPORT.md + logs auxiliares.

$ErrorActionPreference = "Continue"

# Detectar root del repo (donde está requirements.txt o .git)
$root = Get-Location
if (!(Test-Path ".\requirements.txt") -and !(Test-Path ".\.git")) {
  Write-Host "⚠️ Ejecutá este script desde la raíz del repo (donde está requirements.txt o .git)."
}

# Crear carpeta diagnostics
New-Item -ItemType Directory -Force -Path ".\diagnostics" | Out-Null

$reportPath = ".\diagnostics\REPORT.md"
$cmdlogPath = ".\diagnostics\COMMANDS.log"

"## Reporte de Diagnóstico - daily-trading" | Out-File $reportPath -Encoding utf8
("Fecha: " + (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")) | Out-File $reportPath -Append -Encoding utf8
"" | Out-File $reportPath -Append -Encoding utf8

function Add-Section($title) {
  "" | Out-File $reportPath -Append -Encoding utf8
  ("### " + $title) | Out-File $reportPath -Append -Encoding utf8
  "" | Out-File $reportPath -Append -Encoding utf8
}

function Run-Cmd($label, $command) {
  Add-Section $label
  ("```") | Out-File $reportPath -Append -Encoding utf8
  ("> " + $command) | Out-File $reportPath -Append -Encoding utf8
  ("```") | Out-File $reportPath -Append -Encoding utf8

  ("==== " + $label + " ====") | Out-File $cmdlogPath -Append -Encoding utf8
  ("> " + $command) | Out-File $cmdlogPath -Append -Encoding utf8

  try {
    $output = Invoke-Expression $command 2>&1
    "```" | Out-File $reportPath -Append -Encoding utf8
    $output | Out-File $reportPath -Append -Encoding utf8
    "```" | Out-File $reportPath -Append -Encoding utf8

    $output | Out-File $cmdlogPath -Append -Encoding utf8
  } catch {
    "```" | Out-File $reportPath -Append -Encoding utf8
    $_ | Out-File $reportPath -Append -Encoding utf8
    "```" | Out-File $reportPath -Append -Encoding utf8
  }
}

# 1) Info del entorno
Run-Cmd "Python y pip (rutas)" "where python; python --version; python -m pip --version; where pip"
Run-Cmd "Virtualenv activo" "`$env:VIRTUAL_ENV; `$env:Path.Split(';')[0..3]"

# 2) Estado repo
Run-Cmd "Git status" "git status"
Run-Cmd "Estructura (top)" "dir"
Run-Cmd "Tree (2 niveles)" "tree /F /A | Select-Object -First 250"

# 3) Dependencias
Run-Cmd "requirements.txt" "type .\requirements.txt"
Run-Cmd "pip check" "python -m pip check"
Run-Cmd "pip freeze (top 80)" "python -m pip freeze | Select-Object -First 80"

# 4) Import sanity (lo más útil para runtime)
Run-Cmd "Import smoke: main" "python -c `"import main; print('OK import main')`""
Run-Cmd "Import smoke: src.main" "python -c `"import src.main; print('OK import src.main')`""
Run-Cmd "Import smoke: MLSignalFilter" "python -c `"from src.ml.ml_signal_filter import MLSignalFilter; print('OK MLSignalFilter')`""
Run-Cmd "Import smoke: TradeRecorder" "python -c `"from src.ml.trade_recorder import TradeRecorder; print('OK TradeRecorder')`""

# 5) Entry points: detectar posibles mains
Run-Cmd "Buscar entrypoints" "python -c `"import os, re; 
cands=[]; 
for p in ['main.py','src/main.py','daily-trading/main.py','daily_trading/main.py']: 
  if os.path.exists(p): cands.append(p);
print('Candidatos:', cands);
`""

# 6) Dataset ML
Run-Cmd "ML folder listing" "dir .\src\ml"
Run-Cmd "training_data.csv exists?" "python -c `"import os; p='src/ml/training_data.csv'; print(p, 'exists=', os.path.exists(p));`""
Run-Cmd "training_data.csv head" "python -c `"import pandas as pd; 
p='src/ml/training_data.csv';
print('NO FILE' if not __import__('os').path.exists(p) else pd.read_csv(p).head(10).to_string(index=False));
`""

# 7) Lint (si está instalado)
Run-Cmd "pylint version" "python -m pylint --version"
Run-Cmd "pylint: main + src (solo errores)" "python -m pylint main.py src --errors-only"

Add-Section "Fin"
"✅ Reporte generado en diagnostics\REPORT.md" | Out-File $reportPath -Append -Encoding utf8

Write-Host "✅ Listo: diagnostics\REPORT.md"
