"""
Sistema de notificaciones para el bot de trading
Incluye notificaciones por Telegram, email y consola
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import Config

class NotificationManager:
    """Gestor de notificaciones del bot"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Estado de notificaciones
        self.telegram_enabled = bool(self.config.TELEGRAM_BOT_TOKEN and self.config.TELEGRAM_CHAT_ID)
        self.email_enabled = False  # Configurar si se necesita
        self.console_enabled = True
        
        # Configuración de Telegram
        self.telegram_url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}/sendMessage"
        
    async def initialize(self):
        """Inicializar el sistema de notificaciones"""
        try:
            if self.telegram_enabled:
                await self._test_telegram_connection()
                
            self.logger.info("✅ Sistema de notificaciones inicializado")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando notificaciones: {e}")
            
    async def _test_telegram_connection(self):
        """Probar conexión con Telegram"""
        try:
            test_message = "🤖 Bot de Trading iniciado correctamente"
            await self._send_telegram_message(test_message)
            self.logger.info("✅ Conexión con Telegram verificada")
            
        except Exception as e:
            self.logger.error(f"❌ Error conectando con Telegram: {e}")
            self.telegram_enabled = False
            
    async def send_trade_notification(self, trade_data: Dict[str, Any]):
        """Enviar notificación de operación ejecutada"""
        try:
            message = self._format_trade_message(trade_data)
            await self._send_notification(message, "TRADE")
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación de trade: {e}")
            
    async def send_position_closed_notification(self, close_data: Dict[str, Any]):
        """Enviar notificación de posición cerrada"""
        try:
            message = self._format_position_closed_message(close_data)
            await self._send_notification(message, "POSITION_CLOSED")
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación de cierre: {e}")
            
    async def send_risk_alert(self, alert_type: str, details: Dict[str, Any]):
        """Enviar alerta de riesgo"""
        try:
            message = self._format_risk_alert_message(alert_type, details)
            await self._send_notification(message, "RISK_ALERT")
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando alerta de riesgo: {e}")
            
    async def send_emergency_notification(self, message: str):
        """Enviar notificación de emergencia"""
        try:
            emergency_message = f"🚨 EMERGENCIA: {message}"
            await self._send_notification(emergency_message, "EMERGENCY")
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación de emergencia: {e}")
            
    async def send_daily_summary(self, summary_data: Dict[str, Any]):
        """Enviar resumen diario"""
        try:
            message = self._format_daily_summary_message(summary_data)
            await self._send_notification(message, "DAILY_SUMMARY")
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando resumen diario: {e}")
            
    async def _send_notification(self, message: str, notification_type: str):
        """Enviar notificación por todos los canales habilitados"""
        try:
            # Enviar por consola
            if self.console_enabled:
                self._send_console_notification(message, notification_type)
                
            # Enviar por Telegram
            if self.telegram_enabled:
                await self._send_telegram_message(message)
                
            # Enviar por email (si está habilitado)
            if self.email_enabled:
                await self._send_email_notification(message, notification_type)
                
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación: {e}")
            
    def _send_console_notification(self, message: str, notification_type: str):
        """Enviar notificación por consola"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {notification_type}: {message}")
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando notificación por consola: {e}")
            
    async def _send_telegram_message(self, message: str):
        """Enviar mensaje por Telegram"""
        try:
            if not self.telegram_enabled:
                return
                
            payload = {
                'chat_id': self.config.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(self.telegram_url, json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando mensaje por Telegram: {e}")
            raise
            
    async def _send_email_notification(self, message: str, notification_type: str):
        """Enviar notificación por email"""
        try:
            # Implementar envío de email si es necesario
            # Por ahora, solo log
            self.logger.info(f"Email notification: {message}")
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando email: {e}")
            
    def _format_trade_message(self, trade_data: Dict[str, Any]) -> str:
        """Formatear mensaje de operación"""
        try:
            action = trade_data.get('action', 'UNKNOWN')
            symbol = trade_data.get('symbol', 'UNKNOWN')
            price = trade_data.get('price', 0)
            size = trade_data.get('position_size', 0)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            emoji = "🟢" if action == "BUY" else "🔴"
            
            message = (
                f"{emoji} <b>OPERACIÓN EJECUTADA</b>\n"
                f"⏰ {timestamp}\n"
                f"📊 {action} {symbol}\n"
                f"💰 Precio: {price:.4f}\n"
                f"📈 Cantidad: {size:.4f}\n"
                f"💵 Valor: {price * size:.2f}"
            )
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Error formateando mensaje de trade: {e}")
            return "Error formateando mensaje de operación"
            
    def _format_position_closed_message(self, close_data: Dict[str, Any]) -> str:
        """Formatear mensaje de posición cerrada"""
        try:
            pnl = close_data.get('pnl', 0)
            exit_price = close_data.get('exit_price', 0)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            emoji = "💰" if pnl > 0 else "💸"
            pnl_text = f"+{pnl:.2f}" if pnl > 0 else f"{pnl:.2f}"
            
            message = (
                f"{emoji} <b>POSICIÓN CERRADA</b>\n"
                f"⏰ {timestamp}\n"
                f"💰 PnL: {pnl_text}\n"
                f"📊 Precio de salida: {exit_price:.4f}"
            )
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Error formateando mensaje de cierre: {e}")
            return "Error formateando mensaje de cierre"
            
    def _format_risk_alert_message(self, alert_type: str, details: Dict[str, Any]) -> str:
        """Formatear mensaje de alerta de riesgo"""
        try:
            message = (
                f"⚠️ <b>ALERTA DE RIESGO</b>\n"
                f"🔍 Tipo: {alert_type}\n"
                f"📊 Detalles: {details}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            )
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Error formateando alerta de riesgo: {e}")
            return "Error formateando alerta de riesgo"
            
    def _format_daily_summary_message(self, summary_data: Dict[str, Any]) -> str:
        """Formatear mensaje de resumen diario"""
        try:
            daily_pnl = summary_data.get('daily_pnl', 0)
            total_trades = summary_data.get('total_trades', 0)
            win_rate = summary_data.get('win_rate', 0)
            max_drawdown = summary_data.get('max_drawdown', 0)
            
            emoji = "📈" if daily_pnl > 0 else "📉"
            
            message = (
                f"{emoji} <b>RESUMEN DIARIO</b>\n"
                f"💰 PnL: {daily_pnl:.2f}\n"
                f"📊 Operaciones: {total_trades}\n"
                f"🎯 Win Rate: {win_rate:.1%}\n"
                f"📉 Max Drawdown: {max_drawdown:.1%}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            )
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Error formateando resumen diario: {e}")
            return "Error formateando resumen diario"
            
    def enable_telegram(self, bot_token: str, chat_id: str):
        """Habilitar notificaciones por Telegram"""
        try:
            self.config.TELEGRAM_BOT_TOKEN = bot_token
            self.config.TELEGRAM_CHAT_ID = chat_id
            self.telegram_enabled = True
            self.telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            self.logger.info("✅ Notificaciones de Telegram habilitadas")
            
        except Exception as e:
            self.logger.error(f"❌ Error habilitando Telegram: {e}")
            
    def disable_telegram(self):
        """Deshabilitar notificaciones por Telegram"""
        self.telegram_enabled = False
        self.logger.info("❌ Notificaciones de Telegram deshabilitadas")
        
    def enable_console(self):
        """Habilitar notificaciones por consola"""
        self.console_enabled = True
        self.logger.info("✅ Notificaciones por consola habilitadas")
        
    def disable_console(self):
        """Deshabilitar notificaciones por consola"""
        self.console_enabled = False
        self.logger.info("❌ Notificaciones por consola deshabilitadas")
