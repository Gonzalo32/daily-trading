"""
Colector Centralizado de Métricas
==================================

Este módulo centraliza TODAS las métricas del sistema para:
1. Evitar duplicación de lógica entre backtest, risk_manager y dashboards
2. Permitir comparación ML vs sin ML
3. Facilitar ajuste automático de riesgo
4. Registrar features faltantes para ML futuro
"""
# pylint: disable=import-error,logging-fstring-interpolation,broad-except,fixme
# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments
# pylint: disable=too-many-locals,consider-using-max-builtin,wrong-import-order

import os
import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from src.utils.logging_setup import setup_logging


@dataclass
class TradeMetrics:
    """Métricas de un trade individual"""
    # Identificación
    trade_id: Optional[str] = None
    timestamp: datetime = None
    symbol: str = ""
    side: str = ""
    entry_price: float = 0.0
    exit_price: float = 0.0
    size: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: Optional[float] = None
    r_multiple: Optional[float] = None
    duration_seconds: Optional[float] = None
    regime: Optional[str] = None
    ml_filtered: bool = False
    ml_probability: Optional[float] = None

    # ML tracking (CRÍTICO para comparación)
    ml_approved: Optional[bool] = None  # ¿ML aprobó?

    # Contexto de mercado
    rsi: Optional[float] = None
    atr: Optional[float] = None
    volatility: Optional[float] = None

    # Features para ML futuro (expandir según necesidad)
    consecutive_signals: Optional[int] = None
    daily_pnl_before_trade: Optional[float] = None
    daily_trades_before: Optional[int] = None
    time_of_day: Optional[int] = None  # hora del día
    day_of_week: Optional[int] = None  # día de la semana

    # Risk management
    risk_amount: Optional[float] = None
    r_value: Optional[float] = None  # Distancia al stop loss

    # Target para ML
    target: int = 0  # 1 si ganó >= 1R, 0 si no


@dataclass
class SystemMetrics:
    """Métricas agregadas del sistema"""
    # Identificación
    date: date
    timestamp: datetime

    # Métricas básicas
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # PnL
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    total_return_pct: float = 0.0

    # Expectancy (CRÍTICO para evaluación)
    expectancy: float = 0.0  # Expectativa por trade
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0

    # Drawdown
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    peak_equity: float = 0.0
    current_equity: float = 0.0

    # Sharpe y ratios
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0

    # Comparación ML vs sin ML (CRÍTICO)
    ml_trades_count: int = 0
    ml_win_rate: float = 0.0
    ml_expectancy: float = 0.0
    ml_profit_factor: float = 0.0

    no_ml_trades_count: int = 0
    no_ml_win_rate: float = 0.0
    no_ml_expectancy: float = 0.0
    no_ml_profit_factor: float = 0.0

    ml_improvement_pct: float = 0.0  # % mejora de expectancy con ML

    # Métricas para ajuste automático de riesgo
    recent_win_rate: float = 0.0  # Últimos N trades
    recent_expectancy: float = 0.0
    volatility_regime: Optional[str] = None
    consecutive_losses: int = 0
    consecutive_wins: int = 0

    # Equity curve
    equity_curve: List[float] = field(default_factory=list)


class MetricsCollector:
    """
    Colector centralizado de métricas

    RESPONSABILIDADES:
    1. Registrar todos los trades con contexto completo
    2. Calcular métricas agregadas sin duplicación
    3. Comparar ML vs sin ML
    4. Proporcionar métricas para ajuste automático de riesgo
    5. Almacenar features para ML futuro
    """

    def __init__(self, db_path: str = "data/metrics.db", initial_capital: float = 10000.0):
        self.db_path = db_path
        self.initial_capital = initial_capital
        self.logger = setup_logging(__name__)

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Inicializar base de datos
        self._init_database()

        # Cache en memoria para acceso rápido
        self._daily_trades: List[TradeMetrics] = []
        self._system_metrics_cache: Optional[SystemMetrics] = None

    def _init_database(self):
        """Inicializar esquema de base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabla de trades
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                size REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                pnl REAL NOT NULL,
                pnl_pct REAL NOT NULL,
                r_multiple REAL NOT NULL,
                duration_seconds REAL,
                
                -- ML tracking
                ml_filtered INTEGER NOT NULL,
                ml_probability REAL,
                ml_approved INTEGER,
                
                -- Contexto
                regime TEXT,
                rsi REAL,
                atr REAL,
                volatility REAL,
                consecutive_signals INTEGER,
                daily_pnl_before_trade REAL,
                daily_trades_before INTEGER,
                time_of_day INTEGER,
                day_of_week INTEGER,
                risk_amount REAL,
                r_value REAL,
                target INTEGER
            )
        """)

        # Tabla de métricas diarias
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                date TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                daily_pnl REAL,
                total_pnl REAL,
                total_return_pct REAL,
                expectancy REAL,
                avg_win REAL,
                avg_loss REAL,
                profit_factor REAL,
                max_drawdown REAL,
                current_drawdown REAL,
                peak_equity REAL,
                current_equity REAL,
                sharpe_ratio REAL,
                sortino_ratio REAL,
                ml_trades_count INTEGER,
                ml_win_rate REAL,
                ml_expectancy REAL,
                ml_profit_factor REAL,
                no_ml_trades_count INTEGER,
                no_ml_win_rate REAL,
                no_ml_expectancy REAL,
                no_ml_profit_factor REAL,
                ml_improvement_pct REAL,
                recent_win_rate REAL,
                recent_expectancy REAL,
                volatility_regime TEXT,
                consecutive_losses INTEGER,
                consecutive_wins INTEGER
            )
        """)

        # Índices para consultas rápidas
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_ml_filtered ON trades(ml_filtered)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")

        conn.commit()
        conn.close()

        self.logger.info(
            f"📊 Base de datos de métricas inicializada: {self.db_path}")

    def record_trade(
        self,
        position: Dict[str, Any],
        exit_price: float,
        pnl: float,
        ml_decision: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict[str, Any]] = None,
        regime_info: Optional[Dict[str, Any]] = None,
        bot_state: Optional[Dict[str, Any]] = None
    ) -> TradeMetrics:
        """
        Registra un trade con TODO el contexto necesario

        Args:
            position: Datos de la posición (entry_price, size, stop_loss, etc)
            exit_price: Precio de salida
            pnl: PnL del trade
            ml_decision: Decisión del filtro ML (si aplica)
            market_data: Datos de mercado al momento del trade
            regime_info: Información del régimen de mercado
            bot_state: Estado del bot (daily_pnl, daily_trades, etc)
        """
        try:
            # Calcular métricas básicas
            entry_price = position.get('entry_price', exit_price)
            stop_loss = position.get('stop_loss', entry_price)
            r_value = abs(
                entry_price - stop_loss) if stop_loss else abs(entry_price * 0.01)
            r_multiple = pnl / r_value if r_value > 0 else 0.0
            pnl_pct = (pnl / entry_price) * 100 if entry_price > 0 else 0.0

            # Duración
            entry_time = position.get('entry_time')
            exit_time = position.get('exit_time', datetime.now())
            if isinstance(entry_time, str):
                entry_time = datetime.fromisoformat(
                    entry_time.replace('Z', '+00:00'))
            if isinstance(exit_time, str):
                exit_time = datetime.fromisoformat(
                    exit_time.replace('Z', '+00:00'))
            duration = (
                exit_time - entry_time).total_seconds() if entry_time else 0.0

            # ML tracking (CRÍTICO)
            ml_filtered = ml_decision is not None
            ml_probability = ml_decision.get(
                'probability') if ml_decision else None
            ml_approved = ml_decision.get('approved') if ml_decision else None

            # Contexto de mercado
            indicators = market_data.get(
                'indicators', {}) if market_data else {}
            regime = regime_info.get('regime') if regime_info else None

            # Features para ML futuro
            daily_pnl_before = bot_state.get(
                'daily_pnl', 0) if bot_state else None
            daily_trades_before = bot_state.get(
                'daily_trades', 0) if bot_state else None
            consecutive_signals = (bot_state.get('consecutive_signals', 0)
                                  if bot_state else None)

            # Crear métrica de trade
            symbol = position.get('symbol', 'UNK')
            side = position.get('side', 'UNK')
            trade_id = f"{entry_time.isoformat()}_{symbol}_{side}"
            trade_metric = TradeMetrics(
                trade_id=trade_id,
                timestamp=entry_time or datetime.now(),
                symbol=position.get('symbol', 'UNKNOWN'),
                side=position.get('side', 'BUY').upper(),
                entry_price=entry_price,
                exit_price=exit_price,
                size=position.get('size', 0.0),
                stop_loss=stop_loss,
                take_profit=position.get('take_profit', entry_price),
                pnl=pnl,
                pnl_pct=pnl_pct,
                r_multiple=r_multiple,
                duration_seconds=duration,
                ml_filtered=ml_filtered,
                ml_probability=ml_probability,
                ml_approved=ml_approved,
                regime=regime,
                rsi=indicators.get('rsi'),
                atr=indicators.get('atr'),
                volatility=indicators.get('volatility'),
                consecutive_signals=consecutive_signals,
                daily_pnl_before_trade=daily_pnl_before,
                daily_trades_before=daily_trades_before,
                time_of_day=entry_time.hour if entry_time else None,
                day_of_week=entry_time.weekday() if entry_time else None,
                risk_amount=position.get('risk_amount'),
                r_value=r_value,
                target=1 if r_multiple >= 1.0 else 0
            )

            # Guardar en base de datos
            self._save_trade_to_db(trade_metric)

            # Agregar a cache diario
            self._daily_trades.append(trade_metric)

            # Invalidar cache de métricas
            self._system_metrics_cache = None

            self.logger.debug(
                f"📊 Trade registrado: {trade_metric.symbol} | "
                f"PnL={pnl:.2f} | R={r_multiple:.2f} | "
                f"ML={'✅' if ml_filtered else '❌'}"
            )

            return trade_metric

        except Exception as e:
            self.logger.exception(f"❌ Error registrando trade: {e}")
            raise

    def _save_trade_to_db(self, trade: TradeMetrics):
        """Guardar trade en base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO trades VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            trade.trade_id,
            trade.timestamp.isoformat(),
            trade.symbol,
            trade.side,
            trade.entry_price,
            trade.exit_price,
            trade.size,
            trade.stop_loss,
            trade.take_profit,
            trade.pnl,
            trade.pnl_pct,
            trade.r_multiple,
            trade.duration_seconds,
            int(trade.ml_filtered),
            trade.ml_probability,
            int(trade.ml_approved) if trade.ml_approved is not None else None,
            trade.regime,
            trade.rsi,
            trade.atr,
            trade.volatility,
            trade.consecutive_signals,
            trade.daily_pnl_before_trade,
            trade.daily_trades_before,
            trade.time_of_day,
            trade.day_of_week,
            trade.risk_amount,
            trade.r_value,
            trade.target
        ))

        conn.commit()
        conn.close()

    def get_system_metrics(
        self,
        days: int = 1,
        include_ml_comparison: bool = True
    ) -> SystemMetrics:
        """
        Obtiene métricas agregadas del sistema

        Args:
            days: Número de días hacia atrás a considerar
            include_ml_comparison: Si incluir comparación ML vs sin ML
        """
        try:
            # Cargar trades del período
            cutoff_date = datetime.now() - timedelta(days=days)
            trades = self._load_trades_since(cutoff_date)

            if not trades:
                return SystemMetrics(
                    date=date.today(),
                    timestamp=datetime.now(),
                    current_equity=self.initial_capital,
                    peak_equity=self.initial_capital
                )

            # Calcular métricas básicas
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.pnl > 0])
            losing_trades = len([t for t in trades if t.pnl < 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

            # PnL
            daily_pnl = sum(t.pnl for t in trades)
            total_pnl = daily_pnl  # TODO: cargar histórico completo
            total_return_pct = (total_pnl / self.initial_capital) * 100

            # Expectancy (CRÍTICO)
            wins = [t.pnl for t in trades if t.pnl > 0]
            losses = [t.pnl for t in trades if t.pnl < 0]
            avg_win = np.mean(wins) if wins else 0.0
            avg_loss = np.mean(losses) if losses else 0.0
            expectancy = (win_rate * avg_win) - \
                ((1 - win_rate) * abs(avg_loss))

            # Profit factor
            gross_profit = sum(wins) if wins else 0.0
            gross_loss = abs(sum(losses)) if losses else 0.0
            profit_factor = gross_profit / \
                gross_loss if gross_loss > 0 else float('inf')

            # Drawdown
            equity_curve = self._calculate_equity_curve(trades)
            peak_equity = max(
                equity_curve) if equity_curve else self.initial_capital
            current_equity = equity_curve[-1] if equity_curve else self.initial_capital
            max_drawdown = self._calculate_max_drawdown(equity_curve)
            current_drawdown = (peak_equity - current_equity) / \
                peak_equity if peak_equity > 0 else 0.0

            # Sharpe ratio
            returns = [t.pnl for t in trades]
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            sortino_ratio = self._calculate_sortino_ratio(returns)

            # Comparación ML vs sin ML (CRÍTICO)
            ml_metrics = self._calculate_ml_comparison(
                trades) if include_ml_comparison else {}

            # Métricas para ajuste automático
            recent_metrics = self._calculate_recent_metrics(trades)

            # Construir métricas del sistema
            metrics = SystemMetrics(
                date=date.today(),
                timestamp=datetime.now(),
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                daily_pnl=daily_pnl,
                total_pnl=total_pnl,
                total_return_pct=total_return_pct,
                expectancy=expectancy,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                peak_equity=peak_equity,
                current_equity=current_equity,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                equity_curve=equity_curve,
                **ml_metrics,
                **recent_metrics
            )

            # Cache
            self._system_metrics_cache = metrics

            return metrics

        except Exception as e:
            self.logger.exception(
                f"❌ Error calculando métricas del sistema: {e}")
            return SystemMetrics(date=date.today(), timestamp=datetime.now())

    def _calculate_ml_comparison(self, trades: List[TradeMetrics]) -> Dict[str, Any]:
        """Calcula comparación ML vs sin ML"""
        ml_trades = [t for t in trades if t.ml_filtered]
        no_ml_trades = [t for t in trades if not t.ml_filtered]

        def calc_metrics(trade_list):
            if not trade_list:
                return {
                    'count': 0,
                    'win_rate': 0.0,
                    'expectancy': 0.0,
                    'profit_factor': 0.0
                }

            wins = [t.pnl for t in trade_list if t.pnl > 0]
            losses = [t.pnl for t in trade_list if t.pnl < 0]
            win_rate = len(wins) / len(trade_list) if trade_list else 0.0
            avg_win = np.mean(wins) if wins else 0.0
            avg_loss = np.mean(losses) if losses else 0.0
            expectancy = (win_rate * avg_win) - \
                ((1 - win_rate) * abs(avg_loss))

            gross_profit = sum(wins) if wins else 0.0
            gross_loss = abs(sum(losses)) if losses else 0.0
            profit_factor = gross_profit / \
                gross_loss if gross_loss > 0 else float('inf')

            return {
                'count': len(trade_list),
                'win_rate': win_rate,
                'expectancy': expectancy,
                'profit_factor': profit_factor
            }

        ml_metrics = calc_metrics(ml_trades)
        no_ml_metrics = calc_metrics(no_ml_trades)

        # Calcular mejora
        ml_improvement = 0.0
        if no_ml_metrics['expectancy'] != 0:
            ml_improvement = ((ml_metrics['expectancy'] - no_ml_metrics['expectancy']) /
                              abs(no_ml_metrics['expectancy'])) * 100

        return {
            'ml_trades_count': ml_metrics['count'],
            'ml_win_rate': ml_metrics['win_rate'],
            'ml_expectancy': ml_metrics['expectancy'],
            'ml_profit_factor': ml_metrics['profit_factor'],
            'no_ml_trades_count': no_ml_metrics['count'],
            'no_ml_win_rate': no_ml_metrics['win_rate'],
            'no_ml_expectancy': no_ml_metrics['expectancy'],
            'no_ml_profit_factor': no_ml_metrics['profit_factor'],
            'ml_improvement_pct': ml_improvement
        }

    def _calculate_recent_metrics(self, trades: List[TradeMetrics], n: int = 20) -> Dict[str, Any]:
        """Calcula métricas recientes para ajuste automático"""
        recent_trades = trades[-n:] if len(trades) >= n else trades

        if not recent_trades:
            return {
                'recent_win_rate': 0.0,
                'recent_expectancy': 0.0,
                'consecutive_losses': 0,
                'consecutive_wins': 0,
                'volatility_regime': None
            }

        # Win rate reciente
        recent_wins = len([t for t in recent_trades if t.pnl > 0])
        recent_win_rate = recent_wins / \
            len(recent_trades) if recent_trades else 0.0

        # Expectancy reciente
        wins = [t.pnl for t in recent_trades if t.pnl > 0]
        losses = [t.pnl for t in recent_trades if t.pnl < 0]
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        recent_expectancy = (recent_win_rate * avg_win) - \
            ((1 - recent_win_rate) * abs(avg_loss))

        # Consecutivos
        consecutive_losses = 0
        consecutive_wins = 0
        for t in reversed(recent_trades):
            if t.pnl > 0:
                consecutive_wins += 1
                if consecutive_losses > 0:
                    break
            else:
                consecutive_losses += 1
                if consecutive_wins > 0:
                    break

        # Volatilidad (simplificado)
        volatilities = [
            t.volatility for t in recent_trades if t.volatility is not None]
        avg_volatility = np.mean(volatilities) if volatilities else None
        volatility_regime = None
        if avg_volatility:
            if avg_volatility > 0.02:
                volatility_regime = 'high'
            elif avg_volatility < 0.01:
                volatility_regime = 'low'
            else:
                volatility_regime = 'normal'

        return {
            'recent_win_rate': recent_win_rate,
            'recent_expectancy': recent_expectancy,
            'consecutive_losses': consecutive_losses,
            'consecutive_wins': consecutive_wins,
            'volatility_regime': volatility_regime
        }

    def _calculate_equity_curve(self, trades: List[TradeMetrics]) -> List[float]:
        """Calcula curva de equity"""
        equity = self.initial_capital
        curve = [equity]

        for trade in sorted(trades, key=lambda t: t.timestamp):
            equity += trade.pnl
            curve.append(equity)

        return curve

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calcula drawdown máximo"""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        peak = equity_curve[0]
        max_dd = 0.0

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

        return max_dd

    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calcula Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)
        excess_returns = returns_array - risk_free_rate
        std_dev = np.std(excess_returns)

        return (np.mean(excess_returns) / std_dev) if std_dev > 0 else 0.0

    def _calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calcula Sortino ratio (solo considera downside deviation)"""
        if not returns or len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)
        excess_returns = returns_array - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]
        downside_std = (np.std(downside_returns)
                       if len(downside_returns) > 0 else 0.0)

        return ((np.mean(excess_returns) / downside_std)
                if downside_std > 0 else 0.0)

    def _load_trades_since(self, cutoff_date):
        """
        Carga trades desde la base de datos desde una fecha dada
        y los convierte a TradeMetrics.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                timestamp,
                symbol,
                side,
                entry_price,
                exit_price,
                pnl,
                r_multiple,
                duration_seconds,
                regime,
                ml_filtered,
                ml_probability
            FROM trades
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (cutoff_date.isoformat(),))

        rows = cursor.fetchall()
        conn.close()

        trades = []

        for row in rows:
            try:
                trade = TradeMetrics(
                    timestamp=datetime.fromisoformat(row[0]),
                    symbol=row[1],
                    side=row[2],
                    entry_price=row[3],
                    exit_price=row[4],
                    pnl=row[5],
                    r_multiple=row[6],
                    duration_seconds=row[7],
                    regime=row[8],
                    ml_filtered=bool(row[9]),
                    ml_probability=row[10]
                )
                trades.append(trade)
            except Exception as e:
                self.logger.warning(f"Trade inválido ignorado: {e}")

        return trades

    def get_ml_vs_no_ml_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Genera reporte comparativo ML vs sin ML

        RETORNA:
        - Expectancy de cada grupo
        - Win rate de cada grupo
        - Profit factor de cada grupo
        - % de mejora con ML
        - Recomendación (usar ML o no)
        """
        trades = self._load_trades_since(datetime.now() - timedelta(days=days))

        ml_comparison = self._calculate_ml_comparison(trades)

        # Determinar si ML mejora
        ml_better = ml_comparison['ml_expectancy'] > ml_comparison['no_ml_expectancy']

        return {
            'period_days': days,
            'ml_metrics': {
                'trades': ml_comparison['ml_trades_count'],
                'win_rate': ml_comparison['ml_win_rate'],
                'expectancy': ml_comparison['ml_expectancy'],
                'profit_factor': ml_comparison['ml_profit_factor']
            },
            'no_ml_metrics': {
                'trades': ml_comparison['no_ml_trades_count'],
                'win_rate': ml_comparison['no_ml_win_rate'],
                'expectancy': ml_comparison['no_ml_expectancy'],
                'profit_factor': ml_comparison['no_ml_profit_factor']
            },
            'improvement_pct': ml_comparison['ml_improvement_pct'],
            'recommendation': 'USE_ML' if ml_better else 'NO_ML',
            'confidence': 'HIGH' if abs(ml_comparison['ml_improvement_pct']) > 10 else 'LOW'
        }

    def get_risk_adjustment_suggestions(self) -> Dict[str, Any]:
        """
        Sugiere ajustes de riesgo basados en métricas recientes

        RETORNA:
        - Factor de ajuste de tamaño de posición
        - Razón del ajuste
        - Nivel de riesgo recomendado
        """
        metrics = self.get_system_metrics(days=7)

        suggestions = {
            'position_size_multiplier': 1.0,
            'reason': 'Normal conditions',
            'risk_level': 'NORMAL'
        }

        # Ajustar basado en expectancy reciente
        if metrics.recent_expectancy < -0.5:
            suggestions['position_size_multiplier'] = 0.5
            suggestions['reason'] = 'Negative recent expectancy'
            suggestions['risk_level'] = 'REDUCED'
        elif metrics.recent_expectancy > 1.0:
            suggestions['position_size_multiplier'] = 1.2
            suggestions['reason'] = 'Strong recent expectancy'
            suggestions['risk_level'] = 'INCREASED'

        # Ajustar basado en pérdidas consecutivas
        if metrics.consecutive_losses >= 3:
            suggestions['position_size_multiplier'] = min(
                suggestions['position_size_multiplier'], 0.7)
            suggestions['reason'] = f'{metrics.consecutive_losses} consecutive losses'
            suggestions['risk_level'] = 'REDUCED'

        # Ajustar basado en drawdown
        if metrics.current_drawdown > 0.10:  # >10% drawdown
            suggestions['position_size_multiplier'] = min(
                suggestions['position_size_multiplier'], 0.6)
            suggestions['reason'] = f'High drawdown: {metrics.current_drawdown:.1%}'
            suggestions['risk_level'] = 'REDUCED'

        return suggestions

    def export_training_data(self, output_path: str = "src/ml/training_data.csv") -> pd.DataFrame:
        """
        Exporta datos para entrenamiento ML con TODAS las features

        INCLUYE:
        - Todas las features actuales
        - Features de contexto (regime, time, etc)
        - ML tracking (para análisis)
        """
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM trades", conn)
        conn.close()

        # Guardar
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)

        self.logger.info(
            f"📊 Datos exportados para ML: {output_path} ({len(df)} trades)")

        return df
