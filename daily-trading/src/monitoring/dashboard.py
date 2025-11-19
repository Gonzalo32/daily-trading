"""
Dashboard de monitoreo del bot de trading
Interfaz web para visualizar el estado del bot en tiempo real
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
from config import Config

class Dashboard:
    """Dashboard web para monitoreo del bot"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Inicializar FastAPI
        self.app = FastAPI(title="Trading Bot Dashboard", version="1.0.0")
        self.setup_routes()
        
        # Estado del dashboard
        self.is_running = False
        self.websocket_connections = []
        self.current_data = {}
        
    def setup_routes(self):
        """Configurar rutas del dashboard"""
        
        @self.app.get("/")
        async def dashboard_home():
            """Página principal del dashboard"""
            return HTMLResponse(content=self._get_dashboard_html())
            
        @self.app.get("/api/status")
        async def get_status():
            """Obtener estado actual del bot"""
            return {
                "status": "running" if self.is_running else "stopped",
                "timestamp": datetime.now().isoformat(),
                "data": self.current_data
            }
            
        @self.app.get("/api/positions")
        async def get_positions():
            """Obtener posiciones actuales"""
            return self.current_data.get("positions", [])
            
        @self.app.get("/api/metrics")
        async def get_metrics():
            """Obtener métricas de rendimiento"""
            return self.current_data.get("metrics", {})
            
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket para actualizaciones en tiempo real"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Enviar datos actuales
                    await websocket.send_text(json.dumps(self.current_data))
                    await asyncio.sleep(1)  # Actualizar cada segundo
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
                
    async def start(self):
        """Iniciar el dashboard"""
        try:
            self.is_running = True
            self.logger.info(f"🚀 Iniciando dashboard en puerto {self.config.DASHBOARD_PORT}")
            
            # Iniciar servidor en segundo plano usando uvicorn
            config = uvicorn.Config(
                self.app, 
                host="0.0.0.0", 
                port=self.config.DASHBOARD_PORT,
                log_level="info",
                loop="asyncio"
            )
            server = uvicorn.Server(config)
            
            # Ejecutar servidor en tarea separada de forma correcta
            async def run_server():
                await server.serve()
            
            # Crear la tarea y asegurarse de que se ejecute
            task = asyncio.create_task(run_server())
            # Dar tiempo para que el servidor inicie
            await asyncio.sleep(0.1)
            
            self.logger.info(f"✅ Dashboard iniciado en http://0.0.0.0:{self.config.DASHBOARD_PORT}")
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando dashboard: {e}")
            raise
            
    async def stop(self):
        """Detener el dashboard"""
        try:
            self.is_running = False
            self.logger.info("🛑 Dashboard detenido")
            
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo dashboard: {e}")
            
    async def update_data(self, data: Dict[str, Any]):
        """Actualizar datos del dashboard"""
        try:
            self.current_data = {
                **data,
                "timestamp": datetime.now().isoformat(),
                "status": "running" if self.is_running else "stopped"
            }
            
            # Enviar actualización a clientes WebSocket
            await self._broadcast_update()
            
        except Exception as e:
            self.logger.error(f"❌ Error actualizando datos del dashboard: {e}")
            
    async def _broadcast_update(self):
        """Enviar actualización a todos los clientes WebSocket"""
        try:
            if not self.websocket_connections:
                return
                
            message = json.dumps(self.current_data)
            
            # Enviar a todas las conexiones activas
            disconnected = []
            for websocket in self.websocket_connections:
                try:
                    await websocket.send_text(message)
                except:
                    disconnected.append(websocket)
                    
            # Remover conexiones desconectadas
            for websocket in disconnected:
                self.websocket_connections.remove(websocket)
                
        except Exception as e:
            self.logger.error(f"❌ Error enviando actualización WebSocket: {e}")
            
    def _get_dashboard_html(self) -> str:
        """Generar HTML del dashboard"""
        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trading Bot Dashboard</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #1a1a1a;
                    color: #ffffff;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .status {
                    display: inline-block;
                    padding: 10px 20px;
                    border-radius: 20px;
                    font-weight: bold;
                    margin: 10px;
                }
                .status.running {
                    background-color: #4CAF50;
                }
                .status.stopped {
                    background-color: #f44336;
                }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .card {
                    background-color: #2d2d2d;
                    border-radius: 10px;
                    padding: 20px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }
                .card h3 {
                    margin-top: 0;
                    color: #4CAF50;
                }
                .metric {
                    display: flex;
                    justify-content: space-between;
                    margin: 10px 0;
                    padding: 10px;
                    background-color: #3d3d3d;
                    border-radius: 5px;
                }
                .metric.positive {
                    color: #4CAF50;
                }
                .metric.negative {
                    color: #f44336;
                }
                .positions {
                    max-height: 400px;
                    overflow-y: auto;
                }
                .position {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 10px;
                    margin: 5px 0;
                    background-color: #3d3d3d;
                    border-radius: 5px;
                }
                .position.buy {
                    border-left: 4px solid #4CAF50;
                }
                .position.sell {
                    border-left: 4px solid #f44336;
                }
                .chart {
                    height: 300px;
                    background-color: #3d3d3d;
                    border-radius: 5px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #888;
                }
                .refresh {
                    text-align: center;
                    margin-top: 20px;
                }
                .refresh button {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                }
                .refresh button:hover {
                    background-color: #45a049;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 Trading Bot Dashboard</h1>
                    <div class="status" id="status">Conectando...</div>
                    <p id="timestamp">-</p>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h3>📊 Métricas de Rendimiento</h3>
                        <div class="metric">
                            <span>PnL Diario:</span>
                            <span id="daily-pnl">-</span>
                        </div>
                        <div class="metric">
                            <span>Operaciones:</span>
                            <span id="daily-trades">-</span>
                        </div>
                        <div class="metric">
                            <span>Win Rate:</span>
                            <span id="win-rate">-</span>
                        </div>
                        <div class="metric">
                            <span>Max Drawdown:</span>
                            <span id="max-drawdown">-</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>💰 Balance</h3>
                        <div class="metric">
                            <span>Balance Actual:</span>
                            <span id="current-balance">-</span>
                        </div>
                        <div class="metric">
                            <span>Balance Máximo:</span>
                            <span id="peak-balance">-</span>
                        </div>
                        <div class="metric">
                            <span>Exposición:</span>
                            <span id="exposure">-</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>📈 Posiciones Abiertas</h3>
                        <div class="positions" id="positions">
                            <div class="position">
                                <span>Cargando...</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>📊 Gráfico de Precios</h3>
                        <div class="chart" id="price-chart">
                            Gráfico no disponible
                        </div>
                    </div>
                </div>
                
                <div class="refresh">
                    <button onclick="location.reload()">🔄 Actualizar</button>
                </div>
            </div>
            
            <script>
                let ws = null;
                let reconnectInterval = null;
                
                function connectWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}/ws`;
                    
                    ws = new WebSocket(wsUrl);
                    
                    ws.onopen = function() {
                        console.log('WebSocket conectado');
                        document.getElementById('status').textContent = 'Conectado';
                        document.getElementById('status').className = 'status running';
                        clearInterval(reconnectInterval);
                    };
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        updateDashboard(data);
                    };
                    
                    ws.onclose = function() {
                        console.log('WebSocket desconectado');
                        document.getElementById('status').textContent = 'Desconectado';
                        document.getElementById('status').className = 'status stopped';
                        
                        // Intentar reconectar cada 5 segundos
                        reconnectInterval = setInterval(connectWebSocket, 5000);
                    };
                    
                    ws.onerror = function(error) {
                        console.error('Error WebSocket:', error);
                    };
                }
                
                function updateDashboard(data) {
                    // Actualizar timestamp
                    document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleString();
                    
                    // Actualizar métricas
                    if (data.metrics) {
                        document.getElementById('daily-pnl').textContent = data.metrics.daily_pnl ? data.metrics.daily_pnl.toFixed(2) : '-';
                        document.getElementById('daily-trades').textContent = data.metrics.daily_trades || 0;
                        document.getElementById('win-rate').textContent = data.metrics.win_rate ? (data.metrics.win_rate * 100).toFixed(1) + '%' : '-';
                        document.getElementById('max-drawdown').textContent = data.metrics.max_drawdown ? (data.metrics.max_drawdown * 100).toFixed(1) + '%' : '-';
                    }
                    
                    // Actualizar balance
                    if (data.balance) {
                        document.getElementById('current-balance').textContent = data.balance.current ? data.balance.current.toFixed(2) : '-';
                        document.getElementById('peak-balance').textContent = data.balance.peak ? data.balance.peak.toFixed(2) : '-';
                    }
                    
                    // Actualizar posiciones
                    if (data.positions) {
                        updatePositions(data.positions);
                    }
                }
                
                function updatePositions(positions) {
                    const container = document.getElementById('positions');
                    
                    if (positions.length === 0) {
                        container.innerHTML = '<div class="position"><span>No hay posiciones abiertas</span></div>';
                        return;
                    }
                    
                    container.innerHTML = positions.map(pos => `
                        <div class="position ${pos.side.toLowerCase()}">
                            <div>
                                <strong>${pos.symbol}</strong><br>
                                <small>${pos.side} @ ${pos.entry_price.toFixed(4)}</small>
                            </div>
                            <div>
                                <div>Size: ${pos.size.toFixed(4)}</div>
                                <div>PnL: <span class="${pos.pnl >= 0 ? 'positive' : 'negative'}">${pos.pnl.toFixed(2)}</span></div>
                            </div>
                        </div>
                    `).join('');
                }
                
                // Conectar al cargar la página
                window.onload = function() {
                    connectWebSocket();
                };
                
                // Limpiar al cerrar la página
                window.onbeforeunload = function() {
                    if (ws) {
                        ws.close();
                    }
                };
            </script>
        </body>
        </html>
        """
