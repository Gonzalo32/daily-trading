# Archivos de registro de trades (continuidad entre PCs)

Estos archivos guardan el historial de decisiones, trades y estado del bot. **Deben estar trackeados en Git** para que al clonar o descargar el repo en otra PC el historial siga completo.

| Archivo | Descripción | Usado por |
|---------|-------------|-----------|
| `src/ml/decisions.csv` | Cada decisión (BUY/SELL/HOLD) con features y resultado | `TradeRecorder` |
| `src/ml/training_data.csv` | Trades cerrados y contextos (rechazos/sin señal) para entrenar ML | `TradeRecorder`, `MLProgressTracker` |
| `ml_progress.json` | Progreso ML (trades ejecutados, % listo para live) | `MLProgressTracker` |
| `data/state.json` | Estado del bot (posiciones, límites diarios, etc.) | `StateManager` |
| `models/training_metadata.json` | Metadata del último entrenamiento (si existe) | `auto_trainer` |
| `ml_v2_dataset.csv` | Dataset para ML v2 (si se genera) | pipeline ML v2 |

**Importante:** No agregues estos archivos ni sus carpetas a `.gitignore`. Si los ignoras, al cambiar de PC perderás el historial y el progreso.

Rutas relativas al directorio `daily-trading/` (desde donde se ejecuta el bot).
