import os
import subprocess
from src.utils.logging_setup import setup_logging

logger = setup_logging(__name__)


def run(cmd):
    logger.info(f"▶ Ejecutando: {cmd}")
    subprocess.run(cmd, shell=True)


def main():

    # 1. Generar sintético (opcional)
    if not os.path.exists("src/ml/training_data_synth.csv"):
        run("py -m src.ml.generate_synthetic_data")

    # 2. Validación del dataset
    run("py -m src.ml.validate_training_data")

    # 3. Limpieza básica
    run("py -m src.ml.clean_training_data")

    # 4. Entrenar modelo ML
    run("py -m src.ml.train_model")

    # 5. Dashboard (no bloquea porque reload=False)
    logger.info("🌐 Abrí http://127.0.0.1:8001 para ver el dashboard")
    run("py -m src.ml.stats_dashboard")


if __name__ == "__main__":
    main()
