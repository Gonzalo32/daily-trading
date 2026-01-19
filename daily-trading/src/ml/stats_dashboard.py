import os
from datetime import datetime

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.utils.logging_setup import setup_logging

DATA_FILE = "src/ml/training_data.csv"
SYNTH_FILE = "src/ml/training_data_synth.csv"

logger = setup_logging(__name__)
app = FastAPI(title="Trading ML Dataset Dashboard")

                                        
PLOTS_DIR = "ml_plots"
os.makedirs(PLOTS_DIR, exist_ok=True)

                                     
if os.path.exists(PLOTS_DIR):
    app.mount("/plots", StaticFiles(directory=PLOTS_DIR), name="plots")


def _load_data() -> pd.DataFrame:
    """Intenta cargar el dataset principal o el sintético como fallback."""
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        logger.info(f"📥 Cargado {DATA_FILE} con {len(df)} filas")
        return df
    elif os.path.exists(SYNTH_FILE):
        df = pd.read_csv(SYNTH_FILE)
        logger.info(f"📥 Cargado {SYNTH_FILE} con {len(df)} filas (sintético)")
        return df
    else:
        logger.warning("⚠️ No se encontró ningún dataset en src/ml/")
        return pd.DataFrame()


def compute_basic_stats(df: pd.DataFrame) -> dict:
    stats = {}
    if df.empty:
        return {
            "rows": 0,
            "cols": 0,
            "has_target": False,
            "target_distribution": {},
        }

    stats["rows"] = int(len(df))
    stats["cols"] = int(len(df.columns))
    stats["columns"] = list(df.columns)
    stats["has_target"] = "target" in df.columns

                         
    if "target" in df.columns:
        value_counts = df["target"].value_counts(normalize=True).to_dict()
        stats["target_distribution"] = {
            str(int(k)): float(v) for k, v in value_counts.items()
        }
    else:
        stats["target_distribution"] = {}

               
    if "pnl" in df.columns:
        stats["pnl_mean"] = float(df["pnl"].mean())
        stats["pnl_std"] = float(df["pnl"].std() or 0.0)
        stats["pnl_min"] = float(df["pnl"].min())
        stats["pnl_max"] = float(df["pnl"].max())
    else:
        stats["pnl_mean"] = stats["pnl_std"] = stats["pnl_min"] = stats["pnl_max"] = None

                              
    if "target" in df.columns and len(df) > 0:
        stats["winrate_target"] = float(df["target"].mean())
    else:
        stats["winrate_target"] = None

    return stats


@app.get("/metrics", response_class=JSONResponse)
def get_metrics():
    df = _load_data()
    stats = compute_basic_stats(df)
    return stats


@app.get("/", response_class=HTMLResponse)
def root():
    df = _load_data()
    stats = compute_basic_stats(df)

    if df.empty:
        body = """
        <h1>⚠️ No se encontró dataset</h1>
        <p>Creá o llena <code>src/ml/training_data.csv</code> o ejecutá el generador sintético.</p>
        """
    else:
        body = f"""
        <h1>📊 Trading ML Dataset Dashboard</h1>
        <p><b>Filas:</b> {stats['rows']}</p>
        <p><b>Columnas:</b> {stats['cols']}</p>
        <p><b>Tiene target:</b> {stats['has_target']}</p>
        <p><b>Winrate (target=1):</b> {stats['winrate_target']:.2% if stats['winrate_target'] is not None else 'N/A'}</p>
        <h2>Distribución de target</h2>
        <pre>{stats['target_distribution']}</pre>
        <h2>Estadísticas de PnL</h2>
        <pre>
        media: {stats['pnl_mean']}
        std  : {stats['pnl_std']}
        min  : {stats['pnl_min']}
        max  : {stats['pnl_max']}
        </pre>
        <h3>Columnas</h3>
        <pre>{stats['columns']}</pre>
        <p>Última actualización: {datetime.utcnow().isoformat()} UTC</p>
        """

    html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Trading ML Dataset Dashboard</title>
      </head>
      <body>
        {body}
      </body>
    </html>
    """
    return HTMLResponse(content=html)


def main():
    logger.info("🚀 Iniciando Stats Dashboard en http://127.0.0.1:8001")
    uvicorn.run("src.ml.stats_dashboard:app", host="127.0.0.1", port=8001, reload=False)


if __name__ == "__main__":
    main()
