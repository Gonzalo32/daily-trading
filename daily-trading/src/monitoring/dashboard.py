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
        self.current_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "stopped",
            "positions": [],
            "metrics": {
                "daily_pnl": 0.0,
                "daily_trades": 0,
                "win_rate": None,
                "max_drawdown": None
            },
            "balance": {
                "current": 0.0,
                "peak": 0.0,
                "exposure": 0.0
            },
            "market": None,
            "current_signal": None
        }
        
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
                # Enviar datos iniciales inmediatamente
                await websocket.send_text(json.dumps(self.current_data))
                
                while True:
                    # Enviar datos actuales cada segundo
                    try:
                        await websocket.send_text(json.dumps(self.current_data))
                    except Exception as e:
                        self.logger.error(f"Error enviando datos WebSocket: {e}")
                        break
                    await asyncio.sleep(1)  # Actualizar cada segundo
                    
            except WebSocketDisconnect:
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
            except Exception as e:
                self.logger.error(f"Error en WebSocket: {e}")
                if websocket in self.websocket_connections:
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
            # Actualizar datos manteniendo estructura completa
            if data:
                self.current_data.update(data)
            
            # Asegurar campos obligatorios
            self.current_data["timestamp"] = datetime.now().isoformat()
            self.current_data["status"] = "running" if self.is_running else "stopped"
            
            # Asegurar que todos los campos existan con valores por defecto
            if "positions" not in self.current_data or self.current_data["positions"] is None:
                self.current_data["positions"] = []
            if "metrics" not in self.current_data or self.current_data["metrics"] is None:
                self.current_data["metrics"] = {
                    "daily_pnl": 0.0,
                    "daily_trades": 0,
                    "win_rate": None,
                    "max_drawdown": None
                }
            if "balance" not in self.current_data or self.current_data["balance"] is None:
                self.current_data["balance"] = {
                    "current": 0.0,
                    "peak": 0.0,
                    "exposure": 0.0
                }
            
            # Enviar actualización a clientes WebSocket
            await self._broadcast_update()
            
        except Exception as e:
            self.logger.error(f"❌ Error actualizando datos del dashboard: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
    async def _broadcast_update(self):
        """Enviar actualización a todos los clientes WebSocket"""
        try:
            if not self.websocket_connections:
                return
            
            # Serializar datos asegurando que sea JSON válido
            try:
                message = json.dumps(self.current_data, default=str)
            except Exception as e:
                self.logger.error(f"Error serializando datos: {e}")
                return
            
            # Enviar a todas las conexiones activas
            disconnected = []
            for websocket in self.websocket_connections:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    self.logger.debug(f"Error enviando a WebSocket: {e}")
                    disconnected.append(websocket)
                    
            # Remover conexiones desconectadas
            for websocket in disconnected:
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
                
        except Exception as e:
            self.logger.error(f"❌ Error enviando actualización WebSocket: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
    def _get_dashboard_html(self) -> str:
        """Generar HTML del dashboard"""
        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trading Bot Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #1a1a1a;
                    color: #ffffff;
                }
                .container {
                    max-width: 1800px;
                    margin: 0 auto;
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .header-top {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 15px;
                    flex-wrap: wrap;
                }
                .status {
                    display: inline-block;
                    padding: 10px 20px;
                    border-radius: 20px;
                    font-weight: bold;
                    margin: 0;
                }
                .status.running {
                    background-color: #4CAF50;
                }
                .status.stopped {
                    background-color: #f44336;
                }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 15px;
                    margin-bottom: 30px;
                }
                @media (min-width: 1400px) {
                    .grid {
                        grid-template-columns: repeat(5, 1fr);
                    }
                }
                @media (max-width: 1399px) and (min-width: 1100px) {
                    .grid {
                        grid-template-columns: repeat(4, 1fr);
                    }
                }
                @media (max-width: 1099px) and (min-width: 800px) {
                    .grid {
                        grid-template-columns: repeat(3, 1fr);
                    }
                }
                @media (max-width: 799px) {
                    .grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }
                .grid-primary {
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                }
                .grid-chart-row {
                    grid-template-columns: minmax(0, 2fr) minmax(260px, 1fr);
                }
                @media (max-width: 799px) {
                    .grid-chart-row {
                        grid-template-columns: 1fr;
                    }
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
                    height: 500px;
                    background-color: #3d3d3d;
                    border-radius: 5px;
                    padding: 10px;
                    position: relative;
                    width: 100%;
                }
                .chart canvas {
                    width: 100% !important;
                    height: 100% !important;
                    display: block;
                }
                .refresh {
                    display: inline-block;
                    margin: 0;
                }
                .refresh button {
                    background-color: #4CAF50;
                    color: #ffffff;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 20px;
                    cursor: pointer;
                    font-weight: bold;
                    font-size: 14px;
                    letter-spacing: 0.5px;
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
                    <div class="header-top">
                        <div class="status" id="status">Conectando...</div>
                        <button class="refresh" onclick="location.reload()">🔄 Actualizar</button>
                    </div>
                    <p id="timestamp">-</p>
                </div>
                
                <div class="grid grid-primary">
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
                        <h3>🔍 Análisis en Tiempo Real</h3>
                        <div class="metric">
                            <span>Símbolo:</span>
                            <span id="market-symbol">-</span>
                        </div>
                        <div class="metric">
                            <span>Precio Actual:</span>
                            <span id="market-price">-</span>
                        </div>
                        <div class="metric">
                            <span>Volumen:</span>
                            <span id="market-volume">-</span>
                        </div>
                        <div class="metric">
                            <span>Cambio 24h:</span>
                            <span id="market-change">-</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>📈 Indicadores Técnicos</h3>
                        <div class="metric">
                            <span>RSI:</span>
                            <span id="indicator-rsi">-</span>
                        </div>
                        <div class="metric">
                            <span>Media Rápida (9):</span>
                            <span id="indicator-fast-ma">-</span>
                        </div>
                        <div class="metric">
                            <span>Media Lenta (21):</span>
                            <span id="indicator-slow-ma">-</span>
                        </div>
                        <div class="metric">
                            <span>MACD:</span>
                            <span id="indicator-macd">-</span>
                        </div>
                        <div class="metric">
                            <span>Señal MACD:</span>
                            <span id="indicator-macd-signal">-</span>
                        </div>
                        <div class="metric">
                            <span>ATR (Volatilidad):</span>
                            <span id="indicator-atr">-</span>
                        </div>
                    </div>
                </div>
                
                <div class="grid grid-chart-row">
                    <div class="card">
                        <h3>📊 Gráfico de Precios en Tiempo Real</h3>
                        <div class="chart">
                            <canvas id="price-chart"></canvas>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>🎯 Señal Actual</h3>
                        <div class="metric">
                            <span>Estado:</span>
                            <span id="signal-status">Analizando...</span>
                        </div>
                        <div class="metric">
                            <span>Acción:</span>
                            <span id="signal-action">-</span>
                        </div>
                        <div class="metric">
                            <span>Fuerza:</span>
                            <span id="signal-strength">-</span>
                        </div>
                        <div class="metric">
                            <span>Razón:</span>
                            <span id="signal-reason">-</span>
                        </div>
                        <div class="metric">
                            <span>Stop Loss:</span>
                            <span id="signal-stop-loss">-</span>
                        </div>
                        <div class="metric">
                            <span>Take Profit:</span>
                            <span id="signal-take-profit">-</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                let ws = null;
                let reconnectInterval = null;
                let priceChart = null;
                let candleHistory = [];
                const MAX_CANDLES = 50;
                
                // Función para dibujar velas manualmente
                function drawCandlestick(ctx, x, open, high, low, close, width, isUp) {
                    const bodyTop = Math.min(open, close);
                    const bodyBottom = Math.max(open, close);
                    const bodyHeight = bodyBottom - bodyTop;
                    const wickTop = high;
                    const wickBottom = low;
                    
                    // Color: verde si sube, rojo si baja
                    ctx.strokeStyle = isUp ? '#4CAF50' : '#f44336';
                    ctx.fillStyle = isUp ? '#4CAF50' : '#f44336';
                    
                    // Dibujar mecha superior
                    ctx.beginPath();
                    ctx.moveTo(x, wickTop);
                    ctx.lineTo(x, bodyTop);
                    ctx.stroke();
                    
                    // Dibujar cuerpo
                    ctx.fillRect(x - width/2, bodyTop, width, bodyHeight || 1);
                    
                    // Dibujar mecha inferior
                    ctx.beginPath();
                    ctx.moveTo(x, bodyBottom);
                    ctx.lineTo(x, wickBottom);
                    ctx.stroke();
                }
                
                // Inicializar gráfico con canvas personalizado para velas
                function initChart() {
                    const canvas = document.getElementById('price-chart');
                    if (!canvas) {
                        console.error('Canvas no encontrado');
                        return;
                    }
                    
                    const ctx = canvas.getContext('2d');
                    
                    // Ajustar tamaño inicial del canvas
                    function initialResize() {
                        const container = canvas.parentElement;
                        const rect = container.getBoundingClientRect();
                        canvas.width = rect.width - 20; // Restar padding
                        canvas.height = rect.height - 20; // Restar padding
                    }
                    initialResize();
                    
                    // Guardar contexto para uso posterior
                    priceChart = {
                        canvas: canvas,
                        ctx: ctx,
                        data: [],
                        resize: function() {
                            const container = this.canvas.parentElement;
                            const rect = container.getBoundingClientRect();
                            this.canvas.width = rect.width - 20;
                            this.canvas.height = rect.height - 20;
                            if (this.data && this.data.length > 0) {
                                this.draw();
                            }
                        },
                        draw: function() {
                            if (!this.data || this.data.length === 0) return;
                            
                            const padding = 40;
                            const chartWidth = this.canvas.width - padding * 2;
                            const chartHeight = this.canvas.height - padding * 2;
                            
                            // Limpiar canvas
                            this.ctx.fillStyle = '#3d3d3d';
                            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                            
                            // Calcular min y max para escala
                            let minPrice = Infinity;
                            let maxPrice = -Infinity;
                            this.data.forEach(candle => {
                                minPrice = Math.min(minPrice, candle.l, candle.o, candle.c, candle.h);
                                maxPrice = Math.max(maxPrice, candle.h, candle.o, candle.c, candle.l);
                            });
                            
                            const priceRange = maxPrice - minPrice || 1;
                            const candleWidth = chartWidth / this.data.length * 0.8;
                            const spacing = chartWidth / this.data.length;
                            
                            // Dibujar velas
                            this.data.forEach((candle, index) => {
                                const x = padding + index * spacing + spacing / 2;
                                const isUp = candle.c >= candle.o;
                                
                                // Convertir precios a coordenadas Y (invertido)
                                const scaleY = (price) => {
                                    return padding + chartHeight - ((price - minPrice) / priceRange * chartHeight);
                                };
                                
                                const openY = scaleY(candle.o);
                                const highY = scaleY(candle.h);
                                const lowY = scaleY(candle.l);
                                const closeY = scaleY(candle.c);
                                
                                // Dibujar mecha superior
                                this.ctx.strokeStyle = isUp ? '#4CAF50' : '#f44336';
                                this.ctx.beginPath();
                                this.ctx.moveTo(x, highY);
                                this.ctx.lineTo(x, Math.min(openY, closeY));
                                this.ctx.stroke();
                                
                                // Dibujar cuerpo
                                this.ctx.fillStyle = isUp ? '#4CAF50' : '#f44336';
                                const bodyTop = Math.min(openY, closeY);
                                const bodyBottom = Math.max(openY, closeY);
                                this.ctx.fillRect(x - candleWidth/2, bodyTop, candleWidth, Math.max(bodyBottom - bodyTop, 1));
                                
                                // Dibujar mecha inferior
                                this.ctx.beginPath();
                                this.ctx.moveTo(x, Math.max(openY, closeY));
                                this.ctx.lineTo(x, lowY);
                                this.ctx.stroke();
                            });
                            
                            // Dibujar ejes
                            this.ctx.strokeStyle = '#888';
                            this.ctx.lineWidth = 1;
                            // Eje Y izquierdo
                            this.ctx.beginPath();
                            this.ctx.moveTo(padding, padding);
                            this.ctx.lineTo(padding, padding + chartHeight);
                            this.ctx.stroke();
                            // Eje X inferior
                            this.ctx.beginPath();
                            this.ctx.moveTo(padding, padding + chartHeight);
                            this.ctx.lineTo(padding + chartWidth, padding + chartHeight);
                            this.ctx.stroke();
                            
                            // Etiquetas de precio
                            this.ctx.fillStyle = '#888';
                            this.ctx.font = '10px Arial';
                            this.ctx.fillText(maxPrice.toFixed(2), 5, padding + 10);
                            this.ctx.fillText(minPrice.toFixed(2), 5, padding + chartHeight - 5);
                        }
                    };
                    
                    // Ajustar tamaño cuando cambie la ventana
                    window.addEventListener('resize', function() {
                        priceChart.resize();
                    });
                }
                
                function updateChart(ohlcData, timestamp) {
                    if (!priceChart || !ohlcData) return;
                    
                    // Crear vela actual
                    const candle = {
                        o: parseFloat(ohlcData.open || ohlcData.price || 0),
                        h: parseFloat(ohlcData.high || ohlcData.price || 0),
                        l: parseFloat(ohlcData.low || ohlcData.price || 0),
                        c: parseFloat(ohlcData.close || ohlcData.price || 0),
                        timestamp: timestamp
                    };
                    
                    // Agregar nueva vela
                    candleHistory.push(candle);
                    
                    // Limitar a MAX_CANDLES velas
                    if (candleHistory.length > MAX_CANDLES) {
                        candleHistory.shift();
                    }
                    
                    // Actualizar gráfico
                    priceChart.data = candleHistory;
                    priceChart.draw();
                }
                
                function updateChartFromHistory(ohlcHistory) {
                    if (!priceChart || !ohlcHistory || ohlcHistory.length === 0) return;
                    
                    candleHistory = ohlcHistory.map(candle => ({
                        o: parseFloat(candle.open || 0),
                        h: parseFloat(candle.high || 0),
                        l: parseFloat(candle.low || 0),
                        c: parseFloat(candle.close || 0),
                        timestamp: candle.timestamp
                    }));
                    
                    priceChart.data = candleHistory;
                    priceChart.draw();
                }
                
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
                        try {
                            const data = JSON.parse(event.data);
                            console.log('Datos recibidos:', data);
                            updateDashboard(data);
                        } catch (e) {
                            console.error('Error parseando datos WebSocket:', e, event.data);
                        }
                    };
                    
                    ws.onclose = function(event) {
                        console.log('WebSocket desconectado. Código:', event.code, 'Razón:', event.reason);
                        document.getElementById('status').textContent = 'Desconectado';
                        document.getElementById('status').className = 'status stopped';
                        
                        // Intentar reconectar cada 5 segundos
                        if (reconnectInterval) {
                            clearInterval(reconnectInterval);
                        }
                        reconnectInterval = setInterval(connectWebSocket, 5000);
                    };
                    
                    ws.onerror = function(error) {
                        console.error('Error WebSocket:', error);
                        document.getElementById('status').textContent = 'Error de conexión';
                        document.getElementById('status').className = 'status stopped';
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
                        document.getElementById('exposure').textContent = data.balance.exposure ? data.balance.exposure.toFixed(2) : '-';
                    }
                    
                    // Actualizar posiciones
                    if (data.positions) {
                        updatePositions(data.positions);
                    }
                    
                    // Actualizar datos de mercado en tiempo real
                    if (data.market) {
                        document.getElementById('market-symbol').textContent = data.market.symbol || '-';
                        document.getElementById('market-price').textContent = data.market.price ? data.market.price.toFixed(4) : '-';
                        document.getElementById('market-volume').textContent = data.market.volume ? data.market.volume.toFixed(2) : '-';
                        const change = data.market.change_percent;
                        if (change !== undefined && change !== null) {
                            const changeEl = document.getElementById('market-change');
                            changeEl.textContent = change.toFixed(2) + '%';
                            changeEl.className = change >= 0 ? 'positive' : 'negative';
                        }
                    }
                    
                    // Actualizar indicadores técnicos
                    if (data.market && data.market.indicators) {
                        const ind = data.market.indicators;
                        const timestamp = data.timestamp || new Date().toISOString();
                        
                        document.getElementById('indicator-rsi').textContent = ind.rsi ? ind.rsi.toFixed(2) : '-';
                        document.getElementById('indicator-fast-ma').textContent = ind.fast_ma ? ind.fast_ma.toFixed(4) : '-';
                        document.getElementById('indicator-slow-ma').textContent = ind.slow_ma ? ind.slow_ma.toFixed(4) : '-';
                        document.getElementById('indicator-macd').textContent = ind.macd ? ind.macd.toFixed(4) : '-';
                        document.getElementById('indicator-macd-signal').textContent = ind.macd_signal ? ind.macd_signal.toFixed(4) : '-';
                        document.getElementById('indicator-atr').textContent = ind.atr ? ind.atr.toFixed(4) : '-';
                        
                        // Actualizar gráfico de velas
                        if (data.market.ohlc_history && data.market.ohlc_history.length > 0) {
                            // Usar historial completo si está disponible
                            updateChartFromHistory(data.market.ohlc_history);
                        } else if (data.market.open && data.market.high && data.market.low && data.market.close) {
                            // Usar datos OHLC actuales
                            updateChart({
                                open: data.market.open,
                                high: data.market.high,
                                low: data.market.low,
                                close: data.market.close,
                                price: data.market.price
                            }, timestamp);
                        }
                    }
                    
                    // Actualizar señal actual
                    if (data.current_signal) {
                        const sig = data.current_signal;
                        document.getElementById('signal-status').textContent = sig.action ? 'Señal Detectada' : 'Sin Señal';
                        document.getElementById('signal-status').className = sig.action ? 'positive' : '';
                        document.getElementById('signal-action').textContent = sig.action || '-';
                        document.getElementById('signal-strength').textContent = sig.strength ? (sig.strength * 100).toFixed(1) + '%' : '-';
                        document.getElementById('signal-reason').textContent = sig.reason || '-';
                        document.getElementById('signal-stop-loss').textContent = sig.stop_loss ? sig.stop_loss.toFixed(4) : '-';
                        document.getElementById('signal-take-profit').textContent = sig.take_profit ? sig.take_profit.toFixed(4) : '-';
                    } else {
                        document.getElementById('signal-status').textContent = 'Analizando...';
                        document.getElementById('signal-action').textContent = '-';
                        document.getElementById('signal-strength').textContent = '-';
                        document.getElementById('signal-reason').textContent = '-';
                        document.getElementById('signal-stop-loss').textContent = '-';
                        document.getElementById('signal-take-profit').textContent = '-';
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
                    initChart();
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
