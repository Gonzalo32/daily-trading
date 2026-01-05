"""
Ejemplo de Integración del Sistema Centralizado de Métricas
===========================================================

Este archivo muestra cómo integrar MetricsCollector en el sistema existente
"""

import asyncio
from datetime import datetime
from src.metrics import MetricsCollector
from config import Config


# ============================================================
# EJEMPLO 1: Integración en main.py (TradingBot)
# ============================================================

class TradingBotExample:
    """Ejemplo de cómo integrar MetricsCollector en TradingBot"""
    
    def __init__(self):
        self.config = Config()
        
        # ✅ INICIALIZAR COLECTOR DE MÉTRICAS
        self.metrics_collector = MetricsCollector(
            db_path="data/metrics.db",
            initial_capital=self.config.INITIAL_CAPITAL
        )
        
        # Estado del bot
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.current_positions = []
        self.ml_filter = None  # Tu filtro ML
        self.current_regime_info = {}
    
    async def process_signal(self, signal, market_data):
        """Procesar señal de trading"""
        
        # 1. Evaluar con ML (si está disponible)
        ml_decision = None
        if self.ml_filter and self.ml_filter.is_model_available():
            bot_state = {
                'daily_pnl': self.daily_pnl,
                'daily_trades': self.daily_trades,
                'consecutive_signals': 0  # Obtener de strategy
            }
            
            ml_decision = await self.ml_filter.filter_signal(
                signal,
                market_data,
                self.current_regime_info,
                bot_state
            )
            
            # Si ML rechaza, no operar
            if not ml_decision['approved']:
                return
        
        # 2. Abrir posición (código existente)
        position = await self._open_position(signal, market_data)
        
        # 3. Guardar ml_decision en la posición para registro posterior
        position['ml_decision'] = ml_decision
        position['market_data_at_entry'] = market_data
        position['regime_info_at_entry'] = self.current_regime_info
        position['bot_state_at_entry'] = bot_state
        
        self.current_positions.append(position)
    
    async def close_position(self, position, exit_price, reason="TP/SL"):
        """Cerrar posición y registrar en métricas"""
        
        # Calcular PnL (código existente)
        pnl = self._calculate_pnl(position, exit_price)
        self.daily_pnl += pnl
        self.daily_trades += 1
        
        # ✅ REGISTRAR EN COLECTOR DE MÉTRICAS
        self.metrics_collector.record_trade(
            position=position,
            exit_price=exit_price,
            pnl=pnl,
            ml_decision=position.get('ml_decision'),  # CRÍTICO para comparación
            market_data=position.get('market_data_at_entry'),
            regime_info=position.get('regime_info_at_entry'),
            bot_state=position.get('bot_state_at_entry')
        )
        
        # Remover de posiciones abiertas
        self.current_positions.remove(position)
    
    def get_performance_report(self):
        """Obtener reporte de rendimiento"""
        
        # ✅ OBTENER MÉTRICAS CENTRALIZADAS
        metrics = self.metrics_collector.get_system_metrics(days=30)
        
        print("=" * 60)
        print("📊 REPORTE DE RENDIMIENTO")
        print("=" * 60)
        print(f"Total Trades: {metrics.total_trades}")
        print(f"Win Rate: {metrics.win_rate:.1%}")
        print(f"Expectancy: ${metrics.expectancy:.2f}")
        print(f"Profit Factor: {metrics.profit_factor:.2f}")
        print(f"Max Drawdown: {metrics.max_drawdown:.1%}")
        print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        
        # Comparación ML vs sin ML
        print("\n" + "=" * 60)
        print("🤖 COMPARACIÓN ML vs SIN ML")
        print("=" * 60)
        print(f"Trades con ML: {metrics.ml_trades_count}")
        print(f"  - Win Rate: {metrics.ml_win_rate:.1%}")
        print(f"  - Expectancy: ${metrics.ml_expectancy:.2f}")
        print(f"  - Profit Factor: {metrics.ml_profit_factor:.2f}")
        
        print(f"\nTrades sin ML: {metrics.no_ml_trades_count}")
        print(f"  - Win Rate: {metrics.no_ml_win_rate:.1%}")
        print(f"  - Expectancy: ${metrics.no_ml_expectancy:.2f}")
        print(f"  - Profit Factor: {metrics.no_ml_profit_factor:.2f}")
        
        print(f"\n💡 Mejora con ML: {metrics.ml_improvement_pct:+.1f}%")
        
        # Reporte detallado ML vs sin ML
        report = self.metrics_collector.get_ml_vs_no_ml_report(days=30)
        print(f"\n🎯 Recomendación: {report['recommendation']}")
        print(f"   Confianza: {report['confidence']}")
    
    def get_risk_adjustment(self):
        """Obtener sugerencias de ajuste de riesgo"""
        
        # ✅ OBTENER SUGERENCIAS AUTOMÁTICAS
        suggestions = self.metrics_collector.get_risk_adjustment_suggestions()
        
        print("=" * 60)
        print("⚖️ AJUSTE AUTOMÁTICO DE RIESGO")
        print("=" * 60)
        print(f"Multiplicador de tamaño: {suggestions['position_size_multiplier']:.2f}x")
        print(f"Razón: {suggestions['reason']}")
        print(f"Nivel de riesgo: {suggestions['risk_level']}")
        
        return suggestions['position_size_multiplier']
    
    def _calculate_pnl(self, position, exit_price):
        """Calcular PnL (ejemplo simplificado)"""
        entry_price = position.get('entry_price', 0)
        size = position.get('size', 0)
        side = position.get('side', 'BUY').upper()
        
        if side == 'BUY':
            return (exit_price - entry_price) * size
        else:
            return (entry_price - exit_price) * size
    
    async def _open_position(self, signal, market_data):
        """Abrir posición (ejemplo simplificado)"""
        return {
            'entry_price': market_data.get('price', 0),
            'size': signal.get('position_size', 0),
            'stop_loss': signal.get('stop_loss'),
            'take_profit': signal.get('take_profit'),
            'symbol': signal.get('symbol'),
            'side': signal.get('action'),
            'entry_time': datetime.now(),
            'risk_amount': signal.get('risk_amount'),
            'r_value': signal.get('r_value')
        }


# ============================================================
# EJEMPLO 2: Integración en risk_manager.py
# ============================================================

class RiskManagerExample:
    """Ejemplo de cómo simplificar RiskManager usando MetricsCollector"""
    
    def __init__(self, config, metrics_collector):
        self.config = config
        self.metrics_collector = metrics_collector
    
    def get_risk_metrics(self):
        """
        Obtener métricas de riesgo
        ANTES: Calculaba aquí mismo (duplicación)
        AHORA: Usa MetricsCollector centralizado
        """
        # ✅ USAR MÉTRICAS CENTRALIZADAS
        metrics = self.metrics_collector.get_system_metrics(days=1)
        
        return {
            "daily_pnl": metrics.daily_pnl,
            "total_pnl": metrics.total_pnl,
            "win_rate": metrics.win_rate,
            "sharpe_ratio": metrics.sharpe_ratio,
            "drawdown": metrics.current_drawdown,
            "equity": metrics.current_equity,
            "trades_today": metrics.total_trades
        }
    
    def get_dynamic_position_size(self, base_size: float) -> float:
        """
        Obtener tamaño de posición dinámico basado en métricas
        """
        # ✅ OBTENER SUGERENCIAS AUTOMÁTICAS
        suggestions = self.metrics_collector.get_risk_adjustment_suggestions()
        
        multiplier = suggestions['position_size_multiplier']
        adjusted_size = base_size * multiplier
        
        return adjusted_size


# ============================================================
# EJEMPLO 3: Integración en dashboard.py
# ============================================================

class DashboardExample:
    """Ejemplo de cómo actualizar dashboard para usar MetricsCollector"""
    
    def __init__(self, metrics_collector):
        self.metrics_collector = metrics_collector
    
    def get_dashboard_data(self):
        """
        Obtener datos para dashboard
        ANTES: Calculaba métricas aquí mismo
        AHORA: Usa MetricsCollector centralizado
        """
        # ✅ OBTENER MÉTRICAS CENTRALIZADAS
        metrics = self.metrics_collector.get_system_metrics(days=1)
        
        return {
            "metrics": {
                "daily_pnl": metrics.daily_pnl,
                "daily_trades": metrics.total_trades,
                "win_rate": metrics.win_rate,
                "max_drawdown": metrics.max_drawdown,
                "expectancy": metrics.expectancy,
                "profit_factor": metrics.profit_factor,
                "sharpe_ratio": metrics.sharpe_ratio
            },
            "ml_comparison": {
                "ml_trades": metrics.ml_trades_count,
                "ml_win_rate": metrics.ml_win_rate,
                "ml_expectancy": metrics.ml_expectancy,
                "no_ml_trades": metrics.no_ml_trades_count,
                "no_ml_win_rate": metrics.no_ml_win_rate,
                "no_ml_expectancy": metrics.no_ml_expectancy,
                "improvement_pct": metrics.ml_improvement_pct
            },
            "risk_adjustment": self.metrics_collector.get_risk_adjustment_suggestions()
        }


# ============================================================
# EJEMPLO 4: Uso en backtest.py
# ============================================================

class BacktesterExample:
    """Ejemplo de cómo usar MetricsCollector en backtesting"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector(
            db_path="data/backtest_metrics.db",
            initial_capital=10000
        )
        self.trades = []
    
    async def run_backtest(self, data):
        """Ejecutar backtest"""
        # ... código de simulación ...
        
        # Por cada trade simulado:
        for trade in self.trades:
            # ✅ REGISTRAR EN COLECTOR
            self.metrics_collector.record_trade(
                position=trade['position'],
                exit_price=trade['exit_price'],
                pnl=trade['pnl'],
                ml_decision=trade.get('ml_decision'),
                market_data=trade.get('market_data'),
                regime_info=trade.get('regime_info'),
                bot_state=trade.get('bot_state')
            )
        
        # ✅ OBTENER MÉTRICAS CENTRALIZADAS
        metrics = self.metrics_collector.get_system_metrics()
        
        print(f"Win Rate: {metrics.win_rate:.1%}")
        print(f"Expectancy: ${metrics.expectancy:.2f}")
        print(f"Max Drawdown: {metrics.max_drawdown:.1%}")
        print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        
        return metrics


# ============================================================
# EJEMPLO 5: Análisis ML vs Sin ML
# ============================================================

async def analyze_ml_performance():
    """Analizar si ML mejora el rendimiento"""
    
    collector = MetricsCollector(db_path="data/metrics.db")
    
    # Obtener reporte comparativo
    report = collector.get_ml_vs_no_ml_report(days=30)
    
    print("=" * 60)
    print("📊 ANÁLISIS ML vs SIN ML")
    print("=" * 60)
    
    print(f"\n🤖 CON ML:")
    print(f"  Trades: {report['ml_metrics']['trades']}")
    print(f"  Win Rate: {report['ml_metrics']['win_rate']:.1%}")
    print(f"  Expectancy: ${report['ml_metrics']['expectancy']:.2f}")
    print(f"  Profit Factor: {report['ml_metrics']['profit_factor']:.2f}")
    
    print(f"\n❌ SIN ML:")
    print(f"  Trades: {report['no_ml_metrics']['trades']}")
    print(f"  Win Rate: {report['no_ml_metrics']['win_rate']:.1%}")
    print(f"  Expectancy: ${report['no_ml_metrics']['expectancy']:.2f}")
    print(f"  Profit Factor: {report['no_ml_metrics']['profit_factor']:.2f}")
    
    print(f"\n💡 RESULTADO:")
    print(f"  Mejora: {report['improvement_pct']:+.1f}%")
    print(f"  Recomendación: {report['recommendation']}")
    print(f"  Confianza: {report['confidence']}")
    
    # Decisión automática
    if report['recommendation'] == 'USE_ML' and report['confidence'] == 'HIGH':
        print("\n✅ CONCLUSIÓN: Usar filtro ML mejora significativamente el rendimiento")
    elif report['recommendation'] == 'NO_ML' and report['confidence'] == 'HIGH':
        print("\n❌ CONCLUSIÓN: El filtro ML NO mejora el rendimiento")
    else:
        print("\n⚠️ CONCLUSIÓN: Se necesitan más datos para una conclusión definitiva")


# ============================================================
# EJEMPLO 6: Exportar datos para ML
# ============================================================

def export_for_ml_training():
    """Exportar datos completos para entrenamiento ML"""
    
    collector = MetricsCollector(db_path="data/metrics.db")
    
    # ✅ EXPORTAR CON TODAS LAS FEATURES
    df = collector.export_training_data("src/ml/training_data.csv")
    
    print(f"✅ Datos exportados: {len(df)} trades")
    print(f"✅ Columnas: {list(df.columns)}")
    print(f"\n📊 Estadísticas:")
    print(f"  - Trades con ML: {df['ml_filtered'].sum()}")
    print(f"  - Trades sin ML: {(~df['ml_filtered']).sum()}")
    print(f"  - Win Rate general: {(df['target'] == 1).mean():.1%}")
    print(f"  - Win Rate con ML: {df[df['ml_filtered']]['target'].mean():.1%}")
    print(f"  - Win Rate sin ML: {df[~df['ml_filtered']]['target'].mean():.1%}")
    
    return df


if __name__ == "__main__":
    # Ejecutar ejemplos
    print("Ejecutando ejemplos de integración...")
    
    # Ejemplo de análisis ML
    asyncio.run(analyze_ml_performance())
    
    # Exportar datos
    export_for_ml_training()

