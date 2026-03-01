# ML Audit & Export

## Export ML Decisions
Este exportador toma la tabla `ml_decisions` de `data/ml_decisions.db` y la vuelca a CSV.

Requisitos:
- La DB `ml_decisions.db` debe existir y ser accesible.

Ejemplos:
- `python scripts/export_ml_decisions.py --since-hours 24 --symbol BTC/USDT --out data/ml_decisions_export.csv`
- `python scripts/export_ml_decisions.py --limit 1000 --append`

Notas:
- `created_at` esta en UTC.
- `--append` no repite header si el archivo ya tiene contenido.
- Filtros disponibles: `--since-hours`, `--symbol`, `--limit`.

## Smoke test PAPER (manual)
1) Copiar `env.example` a `.env`
2) Setear `TRADING_MODE=PAPER`
3) Setear `ML_ENABLED=true` y `ML_MODE=shadow`
4) Correr: `python daily-trading/main.py`
5) Verificar archivos:
   - `data/ml_decisions.db` existe y crece
   - `daily-trading/src/ml/training_data.csv` existe y crece
6) Exportar:
   - `python scripts/export_ml_decisions.py --limit 100 --out data/ml_decisions_export.csv`

## Smoke test automatico (PAPER)
- `python scripts/smoke_paper.py`

## Runbook de verificacion (PAPER)
1) Crear `.env` desde `env.example`
2) Instalar deps: `pip install -r daily-trading/requirements.txt`
3) Ejecutar smoke automatico:
   - `python scripts/smoke_paper.py`
4) Validar outputs esperados:
   - `data/ml_decisions.db` existe y tiene filas
   - `data/ml_decisions_export_smoke.csv` existe y tiene header
   - logs muestran auditoria cada `ML_AUDIT_EVERY_N_DECISIONS`
5) Troubleshooting rapido:
   - Si falta `pandas`: `pip install pandas`
   - Si falta `joblib`: `pip install joblib`
   - Si falta `python-dotenv`: `pip install python-dotenv`
   - Si falla por paths: ejecutar desde el root del repo (`daily-trading`)
