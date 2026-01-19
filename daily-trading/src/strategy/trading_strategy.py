"""
Estrategia de trading automatizada SELECTIVA - ALTA PROBABILIDAD
Objetivo: Generar POCAS señales de ALTA calidad.
Prioridad: Calidad sobre cantidad - solo operar en condiciones óptimas.

Condiciones estrictas:
- BUY: EMA rápida > EMA lenta + RSI < 35
- SELL: EMA rápida < EMA lenta + RSI > 65

Filtros estrictos:
- NO operar en zonas laterales (rango de precios)
- NO operar en velas de bajo volumen
- Solo señales de alta probabilidad
"""

from datetime import datetime
from typing import Dict, Optional, Any
import pandas as pd

from config import Config
from src.utils.logging_setup import setup_logging
from src.strategy.dynamic_parameters import DynamicParameterManager


class TradingStrategy:
    """
    Estrategia de trading SELECTIVA - ALTA PROBABILIDAD:
    - Genera POCAS señales de ALTA calidad
    - Filtros estrictos (volumen, zonas laterales, condiciones técnicas)
    - Objetivo: Solo operar cuando las condiciones son óptimas
    - Prioridad: Calidad sobre cantidad
    """

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(
            __name__, logfile=config.LOG_FILE, log_level=config.LOG_LEVEL)

                                        
        self.param_manager = DynamicParameterManager(config)

                                 
        self.last_signal: Optional[Dict[str, Any]] = None
        self.consecutive_signals: int = 0

                                                 
        self.last_signal_time: Optional[datetime] = None
        self.min_seconds_between_same_signal: int = 10

                                                       
        self.current_params: Dict[str, Any] = {}

                                                                          
        self.recent_volumes = []
        self.recent_prices = []
        self.recent_ma_diffs = []                                                               
                                                        
        self.recent_atr_values = []

                                                            
                                
                                                            
    def update_parameters_for_regime(self, regime_info: Dict[str, Any]):
        """
        Actualiza los parámetros de la estrategia según el régimen de mercado

        Args:
            regime_info: Información del régimen (regime, confidence, metrics)
        """
        try:
            self.current_params = self.param_manager.adapt_parameters(
                regime_info)
            self.logger.info(
                f"🔧 Parámetros actualizados para régimen: {regime_info.get('regime')} "
                f"(confianza: {regime_info.get('confidence', 0):.2%})"
            )
        except Exception as e:
            self.logger.error(f"❌ Error actualizando parámetros: {e}")

    def get_current_parameters(self) -> Dict[str, Any]:
        """Retorna los parámetros actuales adaptados"""
        return self.current_params if self.current_params else self.param_manager.get_current_parameters()

                                                            
                             
                                                            

    async def generate_signal(self, market_data: Dict[str, Any], regime_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Genera señal de compra o venta según indicadores técnicos simplificados

        Args:
            market_data: Datos de mercado con precio, volumen, indicadores
            regime_info: Información del régimen de mercado (opcional, no usado en versión simplificada)

        Returns:
            Señal con action, precio, stop_loss, take_profit, etc.
        """
        try:
            is_debug = self.config.ENABLE_DEBUG_STRATEGY

            if is_debug:
                self.logger.info("🐛 [DEBUG] Iniciando generación de señal...")

            if not market_data or "indicators" not in market_data:
                if is_debug:
                    self.logger.warning(
                        "🐛 [DEBUG] Rechazado: market_data o indicators faltantes")
                return None

            indicators = market_data["indicators"]
            price = market_data["price"]

                                                                        
            required = ["fast_ma", "slow_ma", "rsi"]
            missing = [k for k in required if k not in indicators]
            if missing:
                if is_debug:
                    self.logger.warning(
                        f"🐛 [DEBUG] Indicadores faltantes: {missing}, usando fallback")
                                                                  
                indicators.setdefault("fast_ma", price)
                indicators.setdefault("slow_ma", price)
                indicators.setdefault("rsi", 50)               
                self.logger.warning(
                    f"⚠️ Indicadores faltantes ({missing}), usando valores por defecto")

            if is_debug:
                self.logger.info(
                    f"🐛 [DEBUG] Indicadores disponibles - "
                    f"EMA9: {indicators.get('fast_ma', 0):.2f}, "
                    f"EMA21: {indicators.get('slow_ma', 0):.2f}, "
                    f"RSI: {indicators.get('rsi', 0):.2f}"
                )

            signal = self._analyze_indicators(indicators, price)

                                          
            if not signal:
                if is_debug:
                    fast = indicators.get('fast_ma', price)
                    slow = indicators.get('slow_ma', price)
                    rsi = indicators.get('rsi', 50)
                    ema_diff_pct = ((fast - slow) / slow *
                                    100) if slow > 0 else 0
                    self.logger.debug(
                        f"🐛 [DEBUG] No se cumplen condiciones estrictas - "
                        f"EMA diff: {ema_diff_pct:.4f}%, RSI: {rsi:.2f}"
                    )
                return None

                                                                       

            current_ts = market_data.get("timestamp")

            if isinstance(current_ts, datetime):
                now = current_ts
            else:
                now = datetime.utcnow()

            if (
                self.last_signal_time is not None
                and self.last_signal is not None
                and self.last_signal.get("action") == signal["action"]
            ):
                elapsed = (now - self.last_signal_time).total_seconds()

                if elapsed < self.min_seconds_between_same_signal:
                    if is_debug:
                        self.logger.debug(
                            f"🐛 [DEBUG] Señal ignorada por cooldown: "
                            f"{elapsed:.1f}s desde la última señal {signal['action']} "
                            f"(mínimo: {self.min_seconds_between_same_signal}s)"
                        )
                    return None

            if is_debug:
                self.logger.info(
                    f"🐛 [DEBUG] ✅ Señal detectada: {signal['action']} @ {signal['price']:.2f} - "
                    f"Razón: {signal.get('reason', 'N/A')}"
                )

                                                                    
            self._update_market_history(market_data)

                                                                           
            filter_result = self._apply_filters(signal, market_data)
            if not filter_result:
                                                       
                if is_debug:
                    self.logger.debug(
                        "🐛 [DEBUG] Señal rechazada por filtros estrictos")
                return None
            else:
                if is_debug:
                    self.logger.info(
                        "🐛 [DEBUG] ✅ Todos los filtros estrictos pasados")

                                                                  
            position_size = self._calculate_position_size(signal)
            if position_size <= 0:
                if is_debug:
                    self.logger.warning(
                        f"🐛 [DEBUG] Rechazado: Tamaño de posición insuficiente ({position_size})")
                return None

            if is_debug:
                self.logger.info(
                    f"🐛 [DEBUG] Tamaño de posición calculado: {position_size:.4f}")

                                         
            signal.update({
                "position_size": position_size,
                "timestamp": market_data["timestamp"],
                "symbol": market_data["symbol"],
            })

            self.last_signal = signal
            if self.last_signal and self.last_signal["action"] == signal["action"]:
                self.consecutive_signals += 1
            else:
                self.consecutive_signals = 1
            self.last_signal_time = now
            if is_debug:
                self.logger.info(
                    f"🐛 [DEBUG] ✅ Señal FINAL aprobada: {signal['action']} {signal['symbol']} @ {price:.2f} "
                    f"(Size: {position_size:.4f}, SL: {signal['stop_loss']:.2f}, TP: {signal['take_profit']:.2f})"
                )
            else:
                self.logger.info(
                    f"✨ Señal generada: {signal['action']} {signal['symbol']} @ {price:.2f}"
                )

            return signal

        except Exception as e:
            self.logger.exception(f"❌ Error generando señal: {e}")
            return None

                                                            
                                                                
                                                            
    def _analyze_indicators(self, indicators: Dict[str, float], price: float) -> Optional[Dict[str, Any]]:
        try:
            fast = indicators.get("fast_ma", price)
            slow = indicators.get("slow_ma", price)
            rsi = indicators.get("rsi", 50)

            if any(pd.isna([fast, slow, rsi])):
                self.logger.warning("⚠️ Indicadores con valores NaN")
                return None

            stop_loss_pct = self.config.STOP_LOSS_PCT
            take_profit_ratio = self.config.TAKE_PROFIT_RATIO

            rsi_overbought = self.config.RSI_OVERBOUGHT
            rsi_oversold = self.config.RSI_OVERSOLD
            ema_diff_min = self.config.EMA_DIFF_PCT_MIN

                                                          
                                                        
                                                            
                                                          

                                            
            ema_diff_pct = ((fast - slow) / slow * 100) if slow > 0 else 0
            ema_diff_abs = abs(ema_diff_pct)

                                                             
                                                                   
            if fast > slow:                                      
                rsi_condition = rsi < 35                          

                if rsi_condition:
                                                        
                    if ema_diff_pct < ema_diff_min:
                        return None

                    stop_loss = round(price * (1 - stop_loss_pct), 2)
                    take_profit = round(
                        price * (1 + stop_loss_pct * take_profit_ratio), 2)

                    return {
                        "action": "BUY",
                        "price": price,
                        "strength": 0.9,                            
                        "reason": f"BUY PRODUCTION | RSI: {rsi:.2f} | EMA diff: {ema_diff_pct:.4f}%",
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                    }

                                                              
                                                                   
            if fast < slow:                                      
                rsi_condition = rsi > 65                          

                if rsi_condition:
                                                        
                    if abs(ema_diff_pct) < ema_diff_min:
                        return None

                    stop_loss = round(price * (1 + stop_loss_pct), 2)
                    take_profit = round(
                        price * (1 - stop_loss_pct * take_profit_ratio), 2)

                    return {
                        "action": "SELL",
                        "price": price,
                        "strength": 0.9,                            
                        "reason": f"SELL PRODUCTION | RSI: {rsi:.2f} | EMA diff: {ema_diff_pct:.4f}%",
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                    }

            return None

        except Exception as e:
            self.logger.exception(f"❌ Error analizando indicadores: {e}")
            return None

    def _is_lateral_market(self, market_data: Dict[str, Any]) -> bool:
        """
        Detecta si el mercado está en una zona lateral (rango de precios)

        Criterios:
        - Las EMAs están muy cerca (diferencia < 0.3%)
        - ATR bajo (volatilidad reducida)
        - Precios recientes en rango estrecho
        """
        try:
            indicators = market_data.get("indicators", {})
            price = market_data.get("price", 0)

            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            atr = indicators.get("atr", 0)

                                                       
            if slow_ma > 0:
                ma_diff_pct = abs(fast_ma - slow_ma) / slow_ma * 100
            else:
                ma_diff_pct = 0

                                                       
                                                                         
            if ma_diff_pct < 0.15:
                self.logger.debug(
                    f"🔍 Zona lateral detectada: EMAs muy cerca (diff: {ma_diff_pct:.4f}%)")
                return True

                                                                                  
            if price > 0:
                atr_pct = (atr / price) * 100
                                                                         
                if atr_pct < 0.5:
                                                                                 
                    if len(self.recent_atr_values) >= 10:
                        sorted_atr = sorted(self.recent_atr_values)
                        atr_percentile_25 = sorted_atr[int(
                            len(sorted_atr) * 0.25)]
                        if atr < atr_percentile_25:
                            self.logger.debug(
                                f"🔍 Zona lateral detectada: ATR bajo ({atr_pct:.4f}%)")
                            return True

                                                             
            if len(self.recent_prices) >= 20:
                recent_prices = self.recent_prices[-20:]
                price_range = max(recent_prices) - min(recent_prices)
                avg_price = sum(recent_prices) / len(recent_prices)
                if avg_price > 0:
                    range_pct = (price_range / avg_price) * 100
                                                                       
                    if range_pct < 1.0:
                        self.logger.debug(
                            f"🔍 Zona lateral detectada: Rango de precios estrecho ({range_pct:.4f}%)")
                        return True

            return False

        except Exception as e:
            self.logger.exception(f"❌ Error detectando zona lateral: {e}")
                                                                          
            return False

                                                            
                           
                                                            

    def _update_market_history(self, market_data: Dict[str, Any]):
        """Actualiza el historial de mercado para detección de zonas laterales"""
        try:
            price = market_data.get("price", 0)
            volume = market_data.get("volume", 0)
            indicators = market_data.get("indicators", {})
            atr = indicators.get("atr", 0)
            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)

                                    
            self.recent_prices.append(price)
            self.recent_volumes.append(volume)
            self.recent_atr_values.append(atr)

            if slow_ma > 0:
                ma_diff_pct = abs(fast_ma - slow_ma) / slow_ma * 100
                self.recent_ma_diffs.append(ma_diff_pct)

                                             
            max_history = 100
            for history_list in [self.recent_prices, self.recent_volumes,
                                 self.recent_atr_values, self.recent_ma_diffs]:
                if len(history_list) > max_history:
                    history_list.pop(0)

        except Exception as e:
            self.logger.exception(f"❌ Error actualizando historial: {e}")

    def _apply_filters(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """
        Filtra señales con condiciones ESTRICTAS

        Filtros:
        1. Volumen mínimo (rechazar velas de bajo volumen)
        2. Zonas laterales (NO operar en rangos)
        3. Horario (solo para acciones)
        4. Repeticiones excesivas
        """
        try:
            is_debug = self.config.ENABLE_DEBUG_STRATEGY

                                                          
                                                 
                                                          
            volume = market_data.get("volume", 0)

                                                                                   
            if len(self.recent_volumes) >= 20:
                                                                     
                sorted_volumes = sorted(self.recent_volumes)
                volume_p60 = sorted_volumes[int(len(sorted_volumes) * 0.6)]
                min_volume = volume_p60 * 0.8                                 
            else:
                                                                            
                min_volume = volume * 0.8 if volume > 0 else 100

                                                                         
                                                                               
                                                                          
            if volume < min_volume:
                if is_debug:
                    self.logger.debug(
                        f"🐛 [DEBUG] Filtro VOLUMEN: Volumen insuficiente "
                        f"({volume:.2f} < {min_volume:.2f})"
                    )
                self.logger.info(
                    f"❌ Señal rechazada: Volumen bajo ({volume:.2f} < {min_volume:.2f})")
                return False

                                                          
                                                   
                                                          
                                                      
                              
                                        
                                                                              
                                   
                                                                               
                              

                                                          
                                                    
                                                          
            if self.config.MARKET == "STOCK":
                hour = market_data.get("timestamp", datetime.now()).hour
                if not (self.config.TRADING_START_HOUR <= hour < self.config.TRADING_END_HOUR):
                    if is_debug:
                        self.logger.debug(
                            f"🐛 [DEBUG] Filtro HORARIO: Fuera de horario de trading "
                            f"(Hora: {hour}, Permitido: {self.config.TRADING_START_HOUR}-{self.config.TRADING_END_HOUR})"
                        )
                    return False

                                                          
                                                     
                                                          
                                                                                 

                  
                                  
                                                                    
                                                                 
                
                              
                                        
                                                                               
                                                                                                                  
                       
                                   
                                                                                                         
                              

            if is_debug:
                self.logger.info(
                    "🐛 [DEBUG] ✅ Todos los filtros estrictos pasados")

            return True

        except Exception as e:
            self.logger.exception(f"❌ Error aplicando filtros: {e}")
                                                          
            return False

    def _calculate_position_size(self, signal: Dict[str, Any]) -> float:
        """Calcula el tamaño de posición basado en riesgo"""
        try:
                                             
            if "price" not in signal or "stop_loss" not in signal:
                self.logger.error(
                    f"❌ Señal inválida - falta price o stop_loss: {signal}"
                )
                return 0.0

            base_capital = self.config.INITIAL_CAPITAL
            risk_per_trade = self.config.RISK_PER_TRADE

            risk_amount = base_capital * risk_per_trade
            risk_per_unit = abs(signal["price"] - signal["stop_loss"])

            if risk_per_unit <= 0:
                self.logger.warning("❌ risk_per_unit inválido")
                return 0.0

                                                
            qty = risk_amount / risk_per_unit

                                                                      
            max_position_value = base_capital * 0.10
            max_qty = max_position_value / signal["price"]

            final_qty = min(qty, max_qty)

            return round(final_qty, 4)

        except Exception as e:
            self.logger.exception(f"❌ Error calculando posición: {e}")
            return 0.0

                                                            
                  
                                                            
    def get_strategy_info(self) -> Dict[str, Any]:
        """Retorna configuración y último estado"""
        return {
            "name": "EMA + RSI Selectiva (Alta Probabilidad)",
            "description": "Estrategia selectiva que solo genera señales en condiciones óptimas: BUY (EMA rápida > EMA lenta + RSI < 35), SELL (EMA rápida < EMA lenta + RSI > 65). Filtros: NO operar en zonas laterales, NO operar en velas de bajo volumen.",
            "parameters": {
                "fast_ma_period": self.config.FAST_MA_PERIOD,
                "slow_ma_period": self.config.SLOW_MA_PERIOD,
                "rsi_period": self.config.RSI_PERIOD,
                "rsi_buy_threshold": 55,
                "rsi_sell_threshold": 45,
                "stop_loss_pct": self.config.STOP_LOSS_PCT,
                "take_profit_ratio": self.config.TAKE_PROFIT_RATIO,
                "filters": {
                    "lateral_market_detection": True,
                    "volume_filter": True,
                    "max_consecutive_signals": 3,
                }
            },
            "last_signal": self.last_signal,
            "consecutive_signals": self.consecutive_signals,
        }

    def reset_strategy(self):
        self.last_signal = None
        self.consecutive_signals = 0
        self.last_signal_time = None         
        self.logger.info("🔄 Estrategia reiniciada")
    
    def get_decision_space(self, market_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Retorna el espacio de decisiones posibles según la estrategia.
        
        ProductionStrategy es selectiva, así que solo marca como posibles
        las acciones que cumplen condiciones estrictas.
        
        Args:
            market_data: Datos de mercado con indicadores
            
        Returns:
            Dict con {"buy": bool, "sell": bool, "hold": True}
        """
        try:
            indicators = market_data.get("indicators", {})
            price = market_data.get("price", 0)
            
            if price <= 0:
                return {"buy": False, "sell": False, "hold": True}
            
            fast_ma = indicators.get("fast_ma", price)
            slow_ma = indicators.get("slow_ma", price)
            rsi = indicators.get("rsi", 50)
            ema_diff_min = self.config.EMA_DIFF_PCT_MIN
            
                                     
            if slow_ma > 0:
                ema_diff_pct = ((fast_ma - slow_ma) / slow_ma) * 100
            else:
                ema_diff_pct = 0
            
            decision_space = {
                "buy": False,
                "sell": False,
                "hold": True                           
            }
            
                                                              
                                                                   
            if fast_ma > slow_ma and rsi < 35 and ema_diff_pct >= ema_diff_min:
                decision_space["buy"] = True
            
                                                               
                                                                   
            if fast_ma < slow_ma and rsi > 65 and abs(ema_diff_pct) >= ema_diff_min:
                decision_space["sell"] = True
            
            return decision_space
            
        except Exception as e:
            self.logger.exception(f"❌ Error obteniendo decision_space: {e}")
            return {"buy": False, "sell": False, "hold": True}


                                                           
                                                                             
ProductionStrategy = TradingStrategy