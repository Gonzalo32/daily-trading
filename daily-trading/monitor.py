"""
Script de monitoreo y mantenimiento del Bot de Day Trading
Permite monitorear el estado del bot y realizar tareas de mantenimiento
"""

import asyncio
import argparse
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import requests
import pandas as pd
from config import Config
from src.utils.logger import setup_logger

class BotMonitor:
    """Monitor del bot de trading"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger('INFO', 'logs/monitor.log')
        self.dashboard_url = f"http://localhost:{config.DASHBOARD_PORT}"
        
    async def check_bot_status(self) -> Dict[str, Any]:
        """Verificar estado del bot"""
        try:
            # Intentar conectar al dashboard
            response = requests.get(f"{self.dashboard_url}/api/status", timeout=5)
            
            if response.status_code == 200:
                status_data = response.json()
                return {
                    'status': 'online',
                    'data': status_data,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'error': f"HTTP {response.status_code}",
                    'timestamp': datetime.now().isoformat()
                }
                
        except requests.exceptions.ConnectionError:
            return {
                'status': 'offline',
                'error': 'No se puede conectar al bot',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Obtener posiciones actuales"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/positions", timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo posiciones: {e}")
            return []
            
    async def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas de rendimiento"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/metrics", timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo métricas: {e}")
            return {}
            
    def analyze_logs(self, hours: int = 24) -> Dict[str, Any]:
        """Analizar logs del bot"""
        try:
            log_file = self.config.LOG_FILE
            
            if not os.path.exists(log_file):
                return {'error': 'Archivo de log no encontrado'}
                
            # Leer logs de las últimas N horas
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Filtrar líneas recientes
            recent_lines = []
            for line in lines:
                try:
                    # Extraer timestamp de la línea
                    timestamp_str = line.split(' - ')[0]
                    line_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    
                    if line_time >= cutoff_time:
                        recent_lines.append(line)
                except:
                    continue
                    
            # Analizar logs
            analysis = {
                'total_lines': len(recent_lines),
                'errors': 0,
                'warnings': 0,
                'trades': 0,
                'positions_opened': 0,
                'positions_closed': 0,
                'risk_alerts': 0
            }
            
            for line in recent_lines:
                if 'ERROR' in line:
                    analysis['errors'] += 1
                elif 'WARNING' in line:
                    analysis['warnings'] += 1
                elif 'TRADE' in line:
                    analysis['trades'] += 1
                elif 'POSITION OPENED' in line:
                    analysis['positions_opened'] += 1
                elif 'POSITION CLOSED' in line:
                    analysis['positions_closed'] += 1
                elif 'RISK EVENT' in line:
                    analysis['risk_alerts'] += 1
                    
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando logs: {e}")
            return {'error': str(e)}
            
    def check_disk_space(self) -> Dict[str, Any]:
        """Verificar espacio en disco"""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage('.')
            
            return {
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2),
                'usage_percent': round((used / total) * 100, 2)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error verificando espacio en disco: {e}")
            return {'error': str(e)}
            
    def cleanup_old_logs(self, days: int = 30):
        """Limpiar logs antiguos"""
        try:
            log_dir = os.path.dirname(self.config.LOG_FILE)
            cutoff_time = datetime.now() - timedelta(days=days)
            
            cleaned_files = 0
            freed_space = 0
            
            for filename in os.listdir(log_dir):
                if filename.endswith('.log'):
                    filepath = os.path.join(log_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_time < cutoff_time:
                        file_size = os.path.getsize(filepath)
                        os.remove(filepath)
                        cleaned_files += 1
                        freed_space += file_size
                        
            return {
                'cleaned_files': cleaned_files,
                'freed_space_mb': round(freed_space / (1024**2), 2)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error limpiando logs: {e}")
            return {'error': str(e)}
            
    def generate_report(self) -> str:
        """Generar reporte de estado"""
        try:
            # Obtener estado del bot
            bot_status = asyncio.run(self.check_bot_status())
            
            # Obtener métricas
            metrics = asyncio.run(self.get_metrics())
            
            # Analizar logs
            log_analysis = self.analyze_logs()
            
            # Verificar espacio en disco
            disk_space = self.check_disk_space()
            
            # Generar reporte
            report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    📊 REPORTE DE MONITOREO                    ║
║                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                    ║
╚══════════════════════════════════════════════════════════════╝

🤖 ESTADO DEL BOT:
   Status: {bot_status['status'].upper()}
   Timestamp: {bot_status['timestamp']}
   {f"Error: {bot_status['error']}" if 'error' in bot_status else ""}

📊 MÉTRICAS DE RENDIMIENTO:
   PnL Diario: ${metrics.get('daily_pnl', 0):.2f}
   Operaciones: {metrics.get('daily_trades', 0)}
   Win Rate: {metrics.get('win_rate', 0):.1%}
   Max Drawdown: {metrics.get('max_drawdown', 0):.1%}

📝 ANÁLISIS DE LOGS (24h):
   Total Líneas: {log_analysis.get('total_lines', 0)}
   Errores: {log_analysis.get('errors', 0)}
   Advertencias: {log_analysis.get('warnings', 0)}
   Operaciones: {log_analysis.get('trades', 0)}
   Posiciones Abiertas: {log_analysis.get('positions_opened', 0)}
   Posiciones Cerradas: {log_analysis.get('positions_closed', 0)}
   Alertas de Riesgo: {log_analysis.get('risk_alerts', 0)}

💾 ESPACIO EN DISCO:
   Total: {disk_space.get('total_gb', 0):.1f} GB
   Usado: {disk_space.get('used_gb', 0):.1f} GB
   Libre: {disk_space.get('free_gb', 0):.1f} GB
   Uso: {disk_space.get('usage_percent', 0):.1f}%

{'⚠️  ADVERTENCIAS:' if log_analysis.get('errors', 0) > 10 or disk_space.get('usage_percent', 0) > 80 else '✅ Todo parece estar funcionando correctamente'}
"""
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Error generando reporte: {e}")
            return f"❌ Error generando reporte: {e}"
            
    def send_alert(self, message: str):
        """Enviar alerta"""
        try:
            if self.config.ENABLE_NOTIFICATIONS and self.config.TELEGRAM_BOT_TOKEN:
                # Enviar por Telegram
                url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': self.config.TELEGRAM_CHAT_ID,
                    'text': f"🚨 ALERTA DEL BOT:\n\n{message}",
                    'parse_mode': 'HTML'
                }
                
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
                
                self.logger.info("✅ Alerta enviada por Telegram")
            else:
                print(f"🚨 ALERTA: {message}")
                
        except Exception as e:
            self.logger.error(f"❌ Error enviando alerta: {e}")
            
    def check_alerts(self):
        """Verificar condiciones de alerta"""
        try:
            alerts = []
            
            # Verificar estado del bot
            bot_status = asyncio.run(self.check_bot_status())
            if bot_status['status'] != 'online':
                alerts.append(f"Bot {bot_status['status']}: {bot_status.get('error', 'Error desconocido')}")
                
            # Verificar métricas
            metrics = asyncio.run(self.get_metrics())
            if metrics.get('daily_pnl', 0) < -1000:  # Pérdida mayor a $1000
                alerts.append(f"Pérdida diaria alta: ${metrics['daily_pnl']:.2f}")
                
            # Verificar logs
            log_analysis = self.analyze_logs()
            if log_analysis.get('errors', 0) > 10:
                alerts.append(f"Muchos errores en logs: {log_analysis['errors']}")
                
            # Verificar espacio en disco
            disk_space = self.check_disk_space()
            if disk_space.get('usage_percent', 0) > 80:
                alerts.append(f"Espacio en disco bajo: {disk_space['usage_percent']:.1f}%")
                
            # Enviar alertas
            if alerts:
                alert_message = "\n".join(f"• {alert}" for alert in alerts)
                self.send_alert(alert_message)
                
        except Exception as e:
            self.logger.error(f"❌ Error verificando alertas: {e}")

def main():
    """Función principal del monitor"""
    parser = argparse.ArgumentParser(description='Monitor del Bot de Day Trading')
    parser.add_argument('--status', action='store_true', help='Verificar estado del bot')
    parser.add_argument('--report', action='store_true', help='Generar reporte completo')
    parser.add_argument('--cleanup', action='store_true', help='Limpiar logs antiguos')
    parser.add_argument('--alerts', action='store_true', help='Verificar alertas')
    parser.add_argument('--daemon', action='store_true', help='Ejecutar en modo daemon')
    parser.add_argument('--interval', type=int, default=300, help='Intervalo en segundos para modo daemon')
    
    args = parser.parse_args()
    
    # Configurar
    config = Config()
    monitor = BotMonitor(config)
    
    if args.status:
        # Verificar estado
        status = asyncio.run(monitor.check_bot_status())
        print(f"Estado del bot: {status['status']}")
        if 'error' in status:
            print(f"Error: {status['error']}")
            
    elif args.report:
        # Generar reporte
        report = monitor.generate_report()
        print(report)
        
    elif args.cleanup:
        # Limpiar logs
        result = monitor.cleanup_old_logs()
        print(f"Archivos limpiados: {result.get('cleaned_files', 0)}")
        print(f"Espacio liberado: {result.get('freed_space_mb', 0)} MB")
        
    elif args.alerts:
        # Verificar alertas
        monitor.check_alerts()
        print("Verificación de alertas completada")
        
    elif args.daemon:
        # Modo daemon
        print(f"🚀 Iniciando monitor en modo daemon (intervalo: {args.interval}s)")
        print("Presiona Ctrl+C para detener")
        
        try:
            while True:
                monitor.check_alerts()
                asyncio.run(asyncio.sleep(args.interval))
        except KeyboardInterrupt:
            print("\n🛑 Monitor detenido")
            
    else:
        # Modo interactivo
        print("🤖 Monitor del Bot de Day Trading")
        print("Usa --help para ver opciones disponibles")

if __name__ == "__main__":
    main()
