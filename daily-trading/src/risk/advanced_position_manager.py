"""
Gestor Avanzado de Posiciones
Maneja trailing stop, break-even, time-based stops y más
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.utils.logging_setup import setup_logging


class AdvancedPositionManager:
    """
    Gestión avanzada de posiciones abiertas con:
    - Trailing stop por ATR o por mínimo/máximo de vela
    - Break-even automático
    - Time-based stop (cerrar si no avanza en X tiempo)
    - Cierre por fin de día
    - Partial take profit (opcional)
    """

    def __init__(self, config):
        self.config = config
        self.logger = setup_logging(__name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)
        
        # Configuración de trailing stop
        self.trailing_enabled = True
        self.trailing_start_r = 1.5  # Activar trailing cuando alcance 1.5R
        self.trailing_atr_multiplier = 1.0  # 1 ATR de trailing
        
        # Configuración de break-even
        self.breakeven_enabled = True
        self.breakeven_trigger_r = 1.0  # Mover a BE cuando alcance 1R
        self.breakeven_buffer = 0.001  # 0.1% por encima de entrada
        
        # Configuración de time-based stop
        self.time_stop_enabled = True
        self.max_position_duration_minutes = 240  # 4 horas máximo
        self.stale_position_minutes = 60  # 1 hora sin movimiento = stale
        
        # Estado de posiciones (tracking adicional)
        self.position_tracking: Dict[str, Dict[str, Any]] = {}

    async def manage_position(
        self, 
        position: Dict[str, Any], 
        current_price: float,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Gestiona una posición abierta aplicando todas las reglas avanzadas
        
        Args:
            position: Diccionario con datos de la posición
            current_price: Precio actual del mercado
            market_data: Datos completos del mercado (para ATR, etc.)
            
        Returns:
            Dict con acción a tomar:
            {
                'action': 'hold' | 'close' | 'update_stops',
                'reason': str,
                'new_stop_loss': float (si action == 'update_stops'),
                'new_take_profit': float (opcional),
                'should_close': bool
            }
        """
        try:
            position_id = position.get('id', 'unknown')
            
            # Inicializar tracking si es nueva posición
            if position_id not in self.position_tracking:
                self._init_position_tracking(position)
            
            tracking = self.position_tracking[position_id]
            
            # Calcular métricas actuales
            metrics = self._calculate_position_metrics(position, current_price, market_data)
            
            # Actualizar tracking
            self._update_tracking(position_id, metrics)
            
            # 1. CHECK: ¿Se alcanzó el stop loss o take profit original?
            if self._check_original_stops(position, current_price):
                return self._create_close_decision(position, current_price, "Stop Loss/Take Profit alcanzado")
            
            # 2. CHECK: Time-based stops
            if self.time_stop_enabled:
                time_check = self._check_time_stops(position, tracking, metrics)
                if time_check['should_close']:
                    return time_check
            
            # 3. CHECK: Fin de día (evitar mantener posiciones overnight en intradía)
            if self._should_close_end_of_day():
                return self._create_close_decision(position, current_price, "Cierre por fin de día")
            
            # 4. APPLY: Break-even
            if self.breakeven_enabled and not tracking['breakeven_applied']:
                be_result = self._apply_breakeven(position, metrics)
                if be_result['should_update']:
                    tracking['breakeven_applied'] = True
                    self.logger.info(f"🎯 Break-even aplicado en posición {position_id}")
                    return be_result
            
            # 5. APPLY: Trailing stop
            if self.trailing_enabled and tracking['breakeven_applied']:
                trailing_result = self._apply_trailing_stop(position, metrics, market_data)
                if trailing_result['should_update']:
                    self.logger.info(f"📈 Trailing stop actualizado en posición {position_id}")
                    return trailing_result
            
            # Sin cambios necesarios
            return {
                'action': 'hold',
                'reason': 'Posición en progreso normal',
                'should_close': False
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error gestionando posición: {e}")
            return {'action': 'hold', 'should_close': False, 'reason': f'Error: {e}'}

    def _init_position_tracking(self, position: Dict[str, Any]):
        """Inicializa el tracking de una nueva posición"""
        position_id = position.get('id', 'unknown')
        
        self.position_tracking[position_id] = {
            'entry_time': position.get('entry_time', datetime.now()),
            'entry_price': position.get('entry_price'),
            'highest_price': position.get('entry_price'),  # Para trailing stop LONG
            'lowest_price': position.get('entry_price'),   # Para trailing stop SHORT
            'max_favorable_excursion': 0.0,  # MFE: mejor profit alcanzado
            'max_adverse_excursion': 0.0,    # MAE: peor drawdown
            'breakeven_applied': False,
            'trailing_active': False,
            'last_price_update': datetime.now(),
            'periods_without_movement': 0,
        }

    def _calculate_position_metrics(
        self, 
        position: Dict[str, Any], 
        current_price: float,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula métricas de la posición"""
        entry_price = position.get('entry_price', current_price)
        stop_loss = position.get('stop_loss', entry_price)
        take_profit = position.get('take_profit', entry_price)
        side = position.get('side', 'buy').lower()
        
        # Calcular riesgo (R)
        risk = abs(entry_price - stop_loss)
        
        # Calcular profit/loss actual
        if side == 'buy':
            pnl = current_price - entry_price
            pnl_pct = (pnl / entry_price) if entry_price > 0 else 0
            r_multiple = (pnl / risk) if risk > 0 else 0
        else:  # sell/short
            pnl = entry_price - current_price
            pnl_pct = (pnl / entry_price) if entry_price > 0 else 0
            r_multiple = (pnl / risk) if risk > 0 else 0
        
        # Duración
        entry_time = position.get('entry_time', datetime.now())
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)
        duration = datetime.now() - entry_time
        
        return {
            'current_price': current_price,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'side': side,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'r_multiple': r_multiple,
            'risk': risk,
            'duration_minutes': duration.total_seconds() / 60,
            'atr': market_data.get('indicators', {}).get('atr', risk),  # Usar ATR del mercado
        }

    def _update_tracking(self, position_id: str, metrics: Dict[str, Any]):
        """Actualiza el tracking de la posición"""
        tracking = self.position_tracking[position_id]
        current_price = metrics['current_price']
        side = metrics['side']
        
        # Actualizar highest/lowest
        if side == 'buy':
            tracking['highest_price'] = max(tracking['highest_price'], current_price)
            mfe = current_price - metrics['entry_price']
            mae = min(0, current_price - metrics['entry_price'])
        else:  # sell/short
            tracking['lowest_price'] = min(tracking['lowest_price'], current_price)
            mfe = metrics['entry_price'] - current_price
            mae = min(0, metrics['entry_price'] - current_price)
        
        # Actualizar MFE/MAE
        tracking['max_favorable_excursion'] = max(tracking['max_favorable_excursion'], mfe)
        tracking['max_adverse_excursion'] = min(tracking['max_adverse_excursion'], mae)
        
        # Detectar movimiento
        time_since_update = (datetime.now() - tracking['last_price_update']).total_seconds() / 60
        if time_since_update > 5:  # 5 minutos sin actualización significativa
            tracking['periods_without_movement'] += 1
        else:
            tracking['periods_without_movement'] = 0
        
        tracking['last_price_update'] = datetime.now()

    def _check_original_stops(self, position: Dict[str, Any], current_price: float) -> bool:
        """Verifica si se alcanzó el SL o TP original"""
        stop_loss = position.get('stop_loss')
        take_profit = position.get('take_profit')
        side = position.get('side', 'buy').lower()
        
        if side == 'buy':
            if stop_loss and current_price <= stop_loss:
                return True
            if take_profit and current_price >= take_profit:
                return True
        else:  # sell/short
            if stop_loss and current_price >= stop_loss:
                return True
            if take_profit and current_price <= take_profit:
                return True
        
        return False

    def _check_time_stops(
        self, 
        position: Dict[str, Any], 
        tracking: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verifica stops basados en tiempo"""
        duration_minutes = metrics['duration_minutes']
        
        # 1. Duración máxima excedida
        if duration_minutes > self.max_position_duration_minutes:
            return self._create_close_decision(
                position, 
                metrics['current_price'],
                f"Tiempo máximo excedido ({duration_minutes:.0f} min)"
            )
        
        # 2. Posición estancada (sin movimiento favorable por mucho tiempo)
        if tracking['periods_without_movement'] > 12:  # 1 hora (12 períodos de 5 min)
            if metrics['r_multiple'] < 0.5:  # Y no está ganando al menos 0.5R
                return self._create_close_decision(
                    position,
                    metrics['current_price'],
                    f"Posición estancada sin progreso"
                )
        
        return {'action': 'hold', 'should_close': False}

    def _should_close_end_of_day(self) -> bool:
        """Verifica si es hora de cerrar posiciones (fin de día)"""
        if self.config.MARKET == 'CRYPTO':
            return False  # Crypto opera 24/7
        
        # Para acciones: cerrar 30 minutos antes del cierre
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        
        close_hour = self.config.TRADING_END_HOUR
        close_minute = 0
        
        # Si estamos dentro de los últimos 30 minutos
        time_to_close = (close_hour * 60 + close_minute) - (current_hour * 60 + current_minute)
        
        return time_to_close <= 30

    def _apply_breakeven(self, position: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica break-even si se alcanzó el umbral"""
        r_multiple = metrics['r_multiple']
        
        # Solo aplicar si alcanzamos el umbral
        if r_multiple < self.breakeven_trigger_r:
            return {'should_update': False}
        
        entry_price = metrics['entry_price']
        side = metrics['side']
        
        # Calcular nuevo stop loss en break-even (con buffer pequeño)
        if side == 'buy':
            new_stop_loss = entry_price * (1 + self.breakeven_buffer)
        else:  # sell/short
            new_stop_loss = entry_price * (1 - self.breakeven_buffer)
        
        return {
            'action': 'update_stops',
            'reason': f'Break-even aplicado (alcanzó {r_multiple:.1f}R)',
            'new_stop_loss': new_stop_loss,
            'should_close': False,
            'should_update': True
        }

    def _apply_trailing_stop(
        self, 
        position: Dict[str, Any], 
        metrics: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aplica trailing stop si corresponde"""
        r_multiple = metrics['r_multiple']
        
        # Solo aplicar trailing si alcanzamos el umbral
        if r_multiple < self.trailing_start_r:
            return {'should_update': False}
        
        position_id = position.get('id', 'unknown')
        tracking = self.position_tracking.get(position_id, {})
        
        side = metrics['side']
        atr = metrics['atr']
        current_stop = metrics['stop_loss']
        
        # Calcular nuevo trailing stop
        if side == 'buy':
            # Para LONG: stop loss = highest_price - (ATR * multiplier)
            highest = tracking.get('highest_price', metrics['current_price'])
            new_stop_loss = highest - (atr * self.trailing_atr_multiplier)
            
            # Solo mover el stop si es mejor que el actual
            if new_stop_loss > current_stop:
                tracking['trailing_active'] = True
                return {
                    'action': 'update_stops',
                    'reason': f'Trailing stop actualizado (precio máximo: {highest:.2f})',
                    'new_stop_loss': new_stop_loss,
                    'should_close': False,
                    'should_update': True
                }
        
        else:  # sell/short
            # Para SHORT: stop loss = lowest_price + (ATR * multiplier)
            lowest = tracking.get('lowest_price', metrics['current_price'])
            new_stop_loss = lowest + (atr * self.trailing_atr_multiplier)
            
            # Solo mover el stop si es mejor que el actual
            if new_stop_loss < current_stop:
                tracking['trailing_active'] = True
                return {
                    'action': 'update_stops',
                    'reason': f'Trailing stop actualizado (precio mínimo: {lowest:.2f})',
                    'new_stop_loss': new_stop_loss,
                    'should_close': False,
                    'should_update': True
                }
        
        return {'should_update': False}

    def _create_close_decision(
        self, 
        position: Dict[str, Any], 
        close_price: float,
        reason: str
    ) -> Dict[str, Any]:
        """Crea una decisión de cierre"""
        return {
            'action': 'close',
            'reason': reason,
            'close_price': close_price,
            'should_close': True
        }

    def cleanup_position(self, position_id: str):
        """Limpia el tracking de una posición cerrada"""
        if position_id in self.position_tracking:
            del self.position_tracking[position_id]

    def get_position_stats(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Retorna estadísticas de una posición"""
        if position_id not in self.position_tracking:
            return None
        
        tracking = self.position_tracking[position_id]
        return {
            'max_favorable_excursion': tracking['max_favorable_excursion'],
            'max_adverse_excursion': tracking['max_adverse_excursion'],
            'breakeven_applied': tracking['breakeven_applied'],
            'trailing_active': tracking['trailing_active'],
            'duration_minutes': (datetime.now() - tracking['entry_time']).total_seconds() / 60
        }

    def configure(
        self,
        trailing_enabled: bool = None,
        trailing_start_r: float = None,
        breakeven_enabled: bool = None,
        breakeven_trigger_r: float = None
    ):
        """Configura los parámetros del gestor"""
        if trailing_enabled is not None:
            self.trailing_enabled = trailing_enabled
        if trailing_start_r is not None:
            self.trailing_start_r = trailing_start_r
        if breakeven_enabled is not None:
            self.breakeven_enabled = breakeven_enabled
        if breakeven_trigger_r is not None:
            self.breakeven_trigger_r = breakeven_trigger_r
        
        self.logger.info(
            f"🔧 AdvancedPositionManager configurado: "
            f"Trailing={self.trailing_enabled} (start={self.trailing_start_r}R), "
            f"BE={self.breakeven_enabled} (trigger={self.breakeven_trigger_r}R)"
        )

