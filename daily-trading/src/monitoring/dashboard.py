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
                    grid-template-columns: minmax(0, 3fr) minmax(260px, 1fr);
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
                    height: 700px;
                    background-color: #1e1e1e;
                    border-radius: 8px;
                    padding: 10px;
                    position: relative;
                    width: 100%;
                    border: 2px solid #4CAF50;
                    box-sizing: border-box;
                    overflow: hidden;
                }
                .chart canvas {
                    width: 100% !important;
                    height: 100% !important;
                    display: block;
                    box-sizing: border-box;
                }
                .chart-container {
                    width: 100%;
                    min-height: 700px;
                    box-sizing: border-box;
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
                    <div class="card chart-container">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <h3 style="margin: 0;">📊 Gráfico de Precios en Tiempo Real</h3>
                            <div style="display: flex; gap: 10px;">
                                <button onclick="resetChartView()" style="background: #4CAF50; color: white; border: none; padding: 5px 15px; border-radius: 5px; cursor: pointer; font-size: 12px;">🔄 Reset</button>
                                <button onclick="zoomIn()" style="background: #2196F3; color: white; border: none; padding: 5px 15px; border-radius: 5px; cursor: pointer; font-size: 12px;">➕ Zoom In</button>
                                <button onclick="zoomOut()" style="background: #2196F3; color: white; border: none; padding: 5px 15px; border-radius: 5px; cursor: pointer; font-size: 12px;">➖ Zoom Out</button>
                            </div>
                        </div>
                        <div style="margin-bottom: 10px; color: #888; font-size: 12px;">
                            <span id="chart-info">Cargando datos...</span>
                            <span style="margin-left: 20px; color: #4CAF50;">🖱️ Scroll para zoom | Arrastra para desplazar</span>
                        </div>
                        <div class="chart" style="position: relative;">
                            <canvas id="price-chart"></canvas>
                            <div id="chart-tooltip" style="position: absolute; background: rgba(0,0,0,0.9); color: white; padding: 10px; border-radius: 5px; pointer-events: none; display: none; z-index: 1000; font-size: 12px; border: 1px solid #4CAF50;"></div>
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
                let currentCandle = null; // Vela actual en tiempo real
                let lastCandleTimestamp = null; // Timestamp de la última vela completa
                const MAX_CANDLES = 200; // Aumentado para mostrar más datos históricos
                
                // Variables para interactividad
                let chartZoom = 1.0;
                let chartOffset = 0; // Offset para pan
                let isDragging = false;
                let dragStartX = 0;
                let hoveredCandle = null;
                let mouseX = 0;
                let mouseY = 0;
                
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
                        // Calcular tamaño considerando padding del contenedor
                        const containerPadding = 20; // padding del .card
                        const chartPadding = 10; // padding del .chart
                        canvas.width = rect.width - (containerPadding * 2) - (chartPadding * 2);
                        canvas.height = rect.height - (containerPadding * 2) - (chartPadding * 2);
                    }
                    initialResize();
                    
                    // Eventos de interactividad
                    let isMouseDown = false;
                    let lastMouseX = 0;
                    
                    canvas.addEventListener('wheel', function(e) {
                        e.preventDefault();
                        const delta = e.deltaY > 0 ? 0.9 : 1.1;
                        const mouseX = e.offsetX;
                        const rect = canvas.getBoundingClientRect();
                        const x = mouseX - rect.left;
                        
                        // Zoom hacia el punto del mouse
                        const oldZoom = chartZoom;
                        chartZoom = Math.max(0.5, Math.min(5.0, chartZoom * delta));
                        
                        // Ajustar offset para mantener el punto del mouse en la misma posición
                        const zoomChange = chartZoom / oldZoom;
                        chartOffset = x - (x - chartOffset) * zoomChange;
                        
                        if (priceChart && priceChart.data && priceChart.data.length > 0) {
                            priceChart.draw();
                        }
                    });
                    
                    canvas.addEventListener('mousedown', function(e) {
                        isMouseDown = true;
                        isDragging = true;
                        lastMouseX = e.offsetX;
                        canvas.style.cursor = 'grabbing';
                    });
                    
                    canvas.addEventListener('mousemove', function(e) {
                        mouseX = e.offsetX;
                        mouseY = e.offsetY;
                        
                        if (isMouseDown) {
                            const deltaX = e.offsetX - lastMouseX;
                            chartOffset += deltaX;
                            lastMouseX = e.offsetX;
                            
                            // Limitar el offset
                            if (priceChart && priceChart.data && priceChart.data.length > 0) {
                                const padding = 60;
                                const chartWidth = canvas.width - padding * 2;
                                const visibleCandles = Math.ceil(priceChart.data.length / chartZoom);
                                const spacing = chartWidth / priceChart.data.length;
                                const maxOffset = Math.max(0, (priceChart.data.length - visibleCandles) * spacing);
                                chartOffset = Math.max(0, Math.min(maxOffset, chartOffset));
                            }
                            
                            if (priceChart && priceChart.data && priceChart.data.length > 0) {
                                priceChart.draw();
                            }
                        } else {
                            // Mostrar tooltip al pasar el mouse
                            updateTooltip(e.offsetX, e.offsetY);
                        }
                    });
                    
                    canvas.addEventListener('mouseup', function() {
                        isMouseDown = false;
                        isDragging = false;
                        canvas.style.cursor = 'default';
                    });
                    
                    canvas.addEventListener('mouseleave', function() {
                        isMouseDown = false;
                        isDragging = false;
                        canvas.style.cursor = 'default';
                        document.getElementById('chart-tooltip').style.display = 'none';
                    });
                    
                    // Guardar contexto para uso posterior
                    priceChart = {
                        canvas: canvas,
                        ctx: ctx,
                        data: [],
                        resize: function() {
                            const container = this.canvas.parentElement;
                            const rect = container.getBoundingClientRect();
                            const containerPadding = 20;
                            const chartPadding = 10;
                            this.canvas.width = rect.width - (containerPadding * 2) - (chartPadding * 2);
                            this.canvas.height = rect.height - (containerPadding * 2) - (chartPadding * 2);
                            if (this.data && this.data.length > 0) {
                                this.draw();
                            }
                        },
                        indicators: {
                            fastMA: [],
                            slowMA: [],
                            rsi: [],
                            macd: [],
                            volume: []
                        },
                        draw: function() {
                            if (!this.data || this.data.length === 0) {
                                // Mostrar mensaje si no hay datos
                                this.ctx.fillStyle = '#ffffff';
                                this.ctx.font = 'bold 16px Arial';
                                this.ctx.textAlign = 'center';
                                this.ctx.fillText('Esperando datos del mercado...', this.canvas.width / 2, this.canvas.height / 2);
                                return;
                            }
                            
                            const padding = 60;
                            const chartWidth = this.canvas.width - padding * 2;
                            const chartHeight = this.canvas.height - padding * 2;
                            
                            // Limpiar canvas con fondo oscuro
                            this.ctx.fillStyle = '#1e1e1e';
                            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                            
                            // Calcular min y max para escala
                            let minPrice = Infinity;
                            let maxPrice = -Infinity;
                            this.data.forEach(candle => {
                                minPrice = Math.min(minPrice, candle.l, candle.o, candle.c, candle.h);
                                maxPrice = Math.max(maxPrice, candle.h, candle.o, candle.c, candle.l);
                            });
                            
                            // Agregar margen del 2% arriba y abajo para mejor visualización
                            const priceRange = maxPrice - minPrice || 1;
                            const margin = priceRange * 0.02;
                            minPrice -= margin;
                            maxPrice += margin;
                            const adjustedRange = maxPrice - minPrice;
                            
                            // Aplicar zoom y offset
                            const baseSpacing = chartWidth / this.data.length;
                            const visibleCandles = Math.ceil(this.data.length / chartZoom);
                            const startIndex = Math.max(0, Math.floor(chartOffset / baseSpacing));
                            const endIndex = Math.min(this.data.length, startIndex + visibleCandles);
                            const visibleData = this.data.slice(startIndex, endIndex);
                            
                            const candleWidth = Math.max(2, Math.min(12, (chartWidth / visibleCandles) * 0.7));
                            const spacing = chartWidth / visibleCandles;
                            
                            // Convertir precios a coordenadas Y (invertido) - Definir fuera del forEach
                            const scaleY = (price) => {
                                return padding + chartHeight - ((price - minPrice) / adjustedRange * chartHeight);
                            };
                            
                            // Dibujar grid horizontal (líneas de precio)
                            this.ctx.strokeStyle = '#333';
                            this.ctx.lineWidth = 1;
                            for (let i = 0; i <= 5; i++) {
                                const y = padding + (chartHeight / 5) * i;
                                this.ctx.beginPath();
                                this.ctx.moveTo(padding, y);
                                this.ctx.lineTo(padding + chartWidth, y);
                                this.ctx.stroke();
                            }
                            
                            // Dibujar marcas de tiempo en el eje X
                            this.ctx.strokeStyle = '#555';
                            this.ctx.lineWidth = 1;
                            this.ctx.fillStyle = '#888';
                            this.ctx.font = '10px Arial';
                            this.ctx.textAlign = 'center';
                            
                            // Mostrar marcas de tiempo cada N velas
                            const timeMarkInterval = Math.max(1, Math.floor(visibleCandles / 8));
                            for (let i = 0; i < visibleData.length; i += timeMarkInterval) {
                                const globalIndex = startIndex + i;
                                if (globalIndex < this.data.length) {
                                    const candle = this.data[globalIndex];
                                    const x = padding + i * spacing + spacing / 2;
                                    
                                    // Línea vertical
                                    this.ctx.beginPath();
                                    this.ctx.moveTo(x, padding + chartHeight);
                                    this.ctx.lineTo(x, padding + chartHeight + 5);
                                    this.ctx.stroke();
                                    
                                    // Etiqueta de tiempo
                                    if (candle.timestamp) {
                                        try {
                                            const date = new Date(candle.timestamp);
                                            const timeStr = date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
                                            this.ctx.fillText(timeStr, x, padding + chartHeight + 18);
                                        } catch (e) {
                                            // Si no se puede parsear, mostrar índice
                                            this.ctx.fillText('#' + globalIndex, x, padding + chartHeight + 18);
                                        }
                                    }
                                }
                            }
                            
                            // Dibujar velas con mejor visualización
                            visibleData.forEach((candle, localIndex) => {
                                const globalIndex = startIndex + localIndex;
                                const x = padding + localIndex * spacing + spacing / 2;
                                const isUp = candle.c >= candle.o;
                                
                                const openY = scaleY(candle.o);
                                const highY = scaleY(candle.h);
                                const lowY = scaleY(candle.l);
                                const closeY = scaleY(candle.c);
                                
                                // Colores más vibrantes
                                const upColor = '#00ff88';
                                const downColor = '#ff4444';
                                
                                // Dibujar mecha superior (más gruesa)
                                this.ctx.strokeStyle = isUp ? upColor : downColor;
                                this.ctx.lineWidth = 1.5;
                                this.ctx.beginPath();
                                this.ctx.moveTo(x, highY);
                                this.ctx.lineTo(x, Math.min(openY, closeY));
                                this.ctx.stroke();
                                
                                // Dibujar cuerpo (más visible)
                                this.ctx.fillStyle = isUp ? upColor : downColor;
                                const bodyTop = Math.min(openY, closeY);
                                const bodyBottom = Math.max(openY, closeY);
                                this.ctx.fillRect(x - candleWidth/2, bodyTop, candleWidth, Math.max(bodyBottom - bodyTop, 2));
                                
                                // Borde del cuerpo para mejor definición
                                this.ctx.strokeStyle = isUp ? '#00cc66' : '#cc0000';
                                this.ctx.lineWidth = 1;
                                this.ctx.strokeRect(x - candleWidth/2, bodyTop, candleWidth, Math.max(bodyBottom - bodyTop, 2));
                                
                                // Dibujar mecha inferior
                                this.ctx.strokeStyle = isUp ? upColor : downColor;
                                this.ctx.lineWidth = 1.5;
                                this.ctx.beginPath();
                                this.ctx.moveTo(x, Math.max(openY, closeY));
                                this.ctx.lineTo(x, lowY);
                                this.ctx.stroke();
                            });
                            
                            // Dibujar ejes con mejor estilo
                            this.ctx.strokeStyle = '#666';
                            this.ctx.lineWidth = 2;
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
                            
                            // Dibujar medias móviles si están disponibles (solo para datos visibles)
                            if (this.indicators && this.indicators.fastMA && this.indicators.fastMA.length > 0) {
                                this.ctx.strokeStyle = '#00bfff';
                                this.ctx.lineWidth = 2;
                                this.ctx.beginPath();
                                let firstPoint = true;
                                visibleData.forEach((candle, localIndex) => {
                                    const globalIndex = startIndex + localIndex;
                                    if (globalIndex < this.indicators.fastMA.length && this.indicators.fastMA[globalIndex] !== null) {
                                        const ma = this.indicators.fastMA[globalIndex];
                                        const x = padding + localIndex * spacing + spacing / 2;
                                        const y = scaleY(ma);
                                        if (firstPoint) {
                                            this.ctx.moveTo(x, y);
                                            firstPoint = false;
                                        } else {
                                            this.ctx.lineTo(x, y);
                                        }
                                    }
                                });
                                this.ctx.stroke();
                                
                                // Etiqueta MA rápida (última visible)
                                if (visibleData.length > 0) {
                                    const lastVisibleIndex = startIndex + visibleData.length - 1;
                                    if (lastVisibleIndex < this.indicators.fastMA.length && this.indicators.fastMA[lastVisibleIndex] !== null) {
                                        const lastMA = this.indicators.fastMA[lastVisibleIndex];
                                        const x = padding + (visibleData.length - 1) * spacing + spacing / 2;
                                        const y = scaleY(lastMA);
                                        this.ctx.fillStyle = '#00bfff';
                                        this.ctx.font = 'bold 10px Arial';
                                        this.ctx.textAlign = 'left';
                                        this.ctx.fillText('MA9: ' + lastMA.toFixed(2), x + 5, y - 5);
                                    }
                                }
                            }
                            
                            if (this.indicators && this.indicators.slowMA && this.indicators.slowMA.length > 0) {
                                this.ctx.strokeStyle = '#ff8800';
                                this.ctx.lineWidth = 2;
                                this.ctx.beginPath();
                                let firstPoint = true;
                                visibleData.forEach((candle, localIndex) => {
                                    const globalIndex = startIndex + localIndex;
                                    if (globalIndex < this.indicators.slowMA.length && this.indicators.slowMA[globalIndex] !== null) {
                                        const ma = this.indicators.slowMA[globalIndex];
                                        const x = padding + localIndex * spacing + spacing / 2;
                                        const y = scaleY(ma);
                                        if (firstPoint) {
                                            this.ctx.moveTo(x, y);
                                            firstPoint = false;
                                        } else {
                                            this.ctx.lineTo(x, y);
                                        }
                                    }
                                });
                                this.ctx.stroke();
                                
                                // Etiqueta MA lenta (última visible)
                                if (visibleData.length > 0) {
                                    const lastVisibleIndex = startIndex + visibleData.length - 1;
                                    if (lastVisibleIndex < this.indicators.slowMA.length && this.indicators.slowMA[lastVisibleIndex] !== null) {
                                        const lastMA = this.indicators.slowMA[lastVisibleIndex];
                                        const x = padding + (visibleData.length - 1) * spacing + spacing / 2;
                                        const y = scaleY(lastMA);
                                        this.ctx.fillStyle = '#ff8800';
                                        this.ctx.font = 'bold 10px Arial';
                                        this.ctx.textAlign = 'left';
                                        this.ctx.fillText('MA21: ' + lastMA.toFixed(2), x + 5, y + 15);
                                    }
                                }
                            }
                            
                            // Etiquetas de precio más visibles
                            this.ctx.fillStyle = '#ffffff';
                            this.ctx.font = 'bold 12px Arial';
                            this.ctx.textAlign = 'left';
                            this.ctx.fillText('Max: ' + maxPrice.toFixed(2), 5, padding + 15);
                            this.ctx.fillText('Min: ' + minPrice.toFixed(2), 5, padding + chartHeight - 5);
                            
                            // Precio actual (última vela visible)
                            if (visibleData.length > 0) {
                                const lastCandle = visibleData[visibleData.length - 1];
                                const currentPrice = lastCandle.c;
                                const currentX = padding + (visibleData.length - 1) * spacing + spacing / 2;
                                const currentY = scaleY(currentPrice);
                                
                                // Línea horizontal para precio actual
                                this.ctx.strokeStyle = '#ffff00';
                                this.ctx.lineWidth = 1;
                                this.ctx.setLineDash([5, 5]);
                                this.ctx.beginPath();
                                this.ctx.moveTo(padding, currentY);
                                this.ctx.lineTo(padding + chartWidth, currentY);
                                this.ctx.stroke();
                                this.ctx.setLineDash([]);
                                
                                // Etiqueta de precio actual
                                this.ctx.fillStyle = '#ffff00';
                                this.ctx.font = 'bold 14px Arial';
                                this.ctx.textAlign = 'right';
                                this.ctx.fillText('Precio: ' + currentPrice.toFixed(4), this.canvas.width - 10, currentY - 5);
                                
                                // Información adicional en la esquina superior derecha
                                this.ctx.fillStyle = '#888';
                                this.ctx.font = '10px Arial';
                                this.ctx.textAlign = 'right';
                                let infoY = padding + 15;
                                this.ctx.fillText('OHLC:', this.canvas.width - 10, infoY);
                                infoY += 12;
                                this.ctx.fillText('O: ' + lastCandle.o.toFixed(2), this.canvas.width - 10, infoY);
                                infoY += 12;
                                this.ctx.fillText('H: ' + lastCandle.h.toFixed(2), this.canvas.width - 10, infoY);
                                infoY += 12;
                                this.ctx.fillText('L: ' + lastCandle.l.toFixed(2), this.canvas.width - 10, infoY);
                                infoY += 12;
                                this.ctx.fillText('C: ' + lastCandle.c.toFixed(2), this.canvas.width - 10, infoY);
                            }
                            
                            // Información del gráfico
                            const infoEl = document.getElementById('chart-info');
                            if (infoEl && this.data.length > 0) {
                                const lastCandle = this.data[this.data.length - 1];
                                let infoText = `Velas: ${this.data.length} | Precio: ${lastCandle.c.toFixed(4)} | Rango: ${minPrice.toFixed(2)} - ${maxPrice.toFixed(2)}`;
                                if (this.indicators && this.indicators.rsi && this.indicators.rsi.length > 0) {
                                    const lastRSI = this.indicators.rsi[this.indicators.rsi.length - 1];
                                    infoText += ` | RSI: ${lastRSI.toFixed(2)}`;
                                }
                                if (this.indicators && this.indicators.macd && this.indicators.macd.length > 0) {
                                    const lastMACD = this.indicators.macd[this.indicators.macd.length - 1];
                                    infoText += ` | MACD: ${lastMACD.toFixed(4)}`;
                                }
                                infoEl.textContent = infoText;
                            }
                        }
                    };
                    
                    // Ajustar tamaño cuando cambie la ventana
                    window.addEventListener('resize', function() {
                        priceChart.resize();
                    });
                }
                
                function updateChart(ohlcData, timestamp) {
                    if (!priceChart || !ohlcData) return;
                    
                    const currentPrice = parseFloat(ohlcData.close || ohlcData.price || 0);
                    const currentOpen = parseFloat(ohlcData.open || ohlcData.price || 0);
                    const currentHigh = parseFloat(ohlcData.high || ohlcData.price || 0);
                    const currentLow = parseFloat(ohlcData.low || ohlcData.price || 0);
                    
                    // Detectar si es una nueva vela (cuando el open cambia significativamente)
                    const isNewCandle = currentCandle && Math.abs(currentCandle.o - currentOpen) > (currentOpen * 0.001);
                    
                    if (!currentCandle || isNewCandle) {
                        // Si hay una vela anterior, agregarla al historial antes de crear una nueva
                        if (currentCandle && isNewCandle) {
                            candleHistory.push({...currentCandle});
                            // Limitar historial
                            if (candleHistory.length > MAX_CANDLES) {
                                candleHistory.shift();
                            }
                        }
                        
                        // Crear nueva vela actual
                        currentCandle = {
                            o: currentOpen,
                            h: Math.max(currentHigh, currentPrice),
                            l: Math.min(currentLow, currentPrice),
                            c: currentPrice,
                            timestamp: timestamp
                        };
                        lastCandleTimestamp = timestamp;
                    } else {
                        // Actualizar vela actual en tiempo real
                        currentCandle.h = Math.max(currentCandle.h, currentPrice, currentHigh);
                        currentCandle.l = Math.min(currentCandle.l, currentPrice, currentLow);
                        currentCandle.c = currentPrice; // Actualizar precio de cierre
                    }
                    
                    // Actualizar gráfico con vela actual
                    const displayData = [...candleHistory];
                    if (currentCandle) {
                        displayData.push(currentCandle);
                    }
                    
                    priceChart.data = displayData;
                    priceChart.draw();
                }
                
                function calculateMA(prices, period) {
                    const ma = [];
                    for (let i = 0; i < prices.length; i++) {
                        if (i < period - 1) {
                            ma.push(null);
                        } else {
                            const sum = prices.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
                            ma.push(sum / period);
                        }
                    }
                    return ma;
                }
                
                function updateChartFromHistory(ohlcHistory) {
                    if (!priceChart || !ohlcHistory || ohlcHistory.length === 0) return;
                    
                    // Convertir historial a formato de velas
                    candleHistory = ohlcHistory.map(candle => ({
                        o: parseFloat(candle.open || 0),
                        h: parseFloat(candle.high || 0),
                        l: parseFloat(candle.low || 0),
                        c: parseFloat(candle.close || 0),
                        timestamp: candle.timestamp
                    }));
                    
                    // Limitar a MAX_CANDLES velas históricas
                    if (candleHistory.length > MAX_CANDLES) {
                        candleHistory = candleHistory.slice(-MAX_CANDLES);
                    }
                    
                    // Calcular medias móviles desde los precios de cierre
                    const closes = candleHistory.map(c => c.c);
                    priceChart.indicators.fastMA = calculateMA(closes, 9);
                    priceChart.indicators.slowMA = calculateMA(closes, 21);
                    
                    // Combinar historial con vela actual si existe
                    const displayData = [...candleHistory];
                    if (currentCandle) {
                        displayData.push(currentCandle);
                    }
                    
                    priceChart.data = displayData;
                    priceChart.draw();
                }
                
                function updateIndicators(indicators) {
                    if (!priceChart || !indicators) return;
                    
                    // Actualizar indicadores si están disponibles
                    if (indicators.fast_ma !== undefined && indicators.fast_ma !== null) {
                        if (!priceChart.indicators.fastMA) priceChart.indicators.fastMA = [];
                        priceChart.indicators.fastMA.push(parseFloat(indicators.fast_ma));
                        if (priceChart.indicators.fastMA.length > priceChart.data.length) {
                            priceChart.indicators.fastMA.shift();
                        }
                    }
                    
                    if (indicators.slow_ma !== undefined && indicators.slow_ma !== null) {
                        if (!priceChart.indicators.slowMA) priceChart.indicators.slowMA = [];
                        priceChart.indicators.slowMA.push(parseFloat(indicators.slow_ma));
                        if (priceChart.indicators.slowMA.length > priceChart.data.length) {
                            priceChart.indicators.slowMA.shift();
                        }
                    }
                    
                    if (indicators.rsi !== undefined && indicators.rsi !== null) {
                        if (!priceChart.indicators.rsi) priceChart.indicators.rsi = [];
                        priceChart.indicators.rsi.push(parseFloat(indicators.rsi));
                        if (priceChart.indicators.rsi.length > priceChart.data.length) {
                            priceChart.indicators.rsi.shift();
                        }
                    }
                    
                    if (indicators.macd !== undefined && indicators.macd !== null) {
                        if (!priceChart.indicators.macd) priceChart.indicators.macd = [];
                        priceChart.indicators.macd.push(parseFloat(indicators.macd));
                        if (priceChart.indicators.macd.length > priceChart.data.length) {
                            priceChart.indicators.macd.shift();
                        }
                    }
                }
                
                // Funciones de control del gráfico
                function zoomIn() {
                    chartZoom = Math.min(5.0, chartZoom * 1.2);
                    if (priceChart && priceChart.data && priceChart.data.length > 0) {
                        priceChart.draw();
                    }
                }
                
                function zoomOut() {
                    chartZoom = Math.max(0.5, chartZoom * 0.8);
                    if (priceChart && priceChart.data && priceChart.data.length > 0) {
                        priceChart.draw();
                    }
                }
                
                function resetChartView() {
                    chartZoom = 1.0;
                    chartOffset = 0;
                    if (priceChart && priceChart.data && priceChart.data.length > 0) {
                        priceChart.draw();
                    }
                }
                
                function updateTooltip(x, y) {
                    if (!priceChart || !priceChart.data || priceChart.data.length === 0) return;
                    
                    const padding = 60;
                    const chartWidth = priceChart.canvas.width - padding * 2;
                    const visibleCandles = Math.ceil(priceChart.data.length / chartZoom);
                    const startIndex = Math.max(0, Math.floor(chartOffset / (chartWidth / priceChart.data.length)));
                    const spacing = chartWidth / visibleCandles;
                    
                    // Encontrar la vela más cercana al cursor
                    const localIndex = Math.floor((x - padding) / spacing);
                    const globalIndex = startIndex + localIndex;
                    
                    if (globalIndex >= 0 && globalIndex < priceChart.data.length) {
                        const candle = priceChart.data[globalIndex];
                        const tooltip = document.getElementById('chart-tooltip');
                        const rect = priceChart.canvas.getBoundingClientRect();
                        
                        let tooltipText = '<strong>Vela #' + globalIndex + '</strong><br>';
                        if (candle.timestamp) {
                            try {
                                const date = new Date(candle.timestamp);
                                tooltipText += 'Fecha: ' + date.toLocaleString('es-ES') + '<br>';
                            } catch (e) {}
                        }
                        tooltipText += 'Open: ' + candle.o.toFixed(4) + '<br>';
                        tooltipText += 'High: ' + candle.h.toFixed(4) + '<br>';
                        tooltipText += 'Low: ' + candle.l.toFixed(4) + '<br>';
                        tooltipText += 'Close: ' + candle.c.toFixed(4) + '<br>';
                        tooltipText += 'Cambio: ' + ((candle.c - candle.o) / candle.o * 100).toFixed(2) + '%';
                        
                        tooltip.innerHTML = tooltipText;
                        tooltip.style.display = 'block';
                        tooltip.style.left = (rect.left + x + 10) + 'px';
                        tooltip.style.top = (rect.top + y - 10) + 'px';
                        
                        // Asegurar que el tooltip no se salga de la pantalla
                        if (parseInt(tooltip.style.left) + tooltip.offsetWidth > window.innerWidth) {
                            tooltip.style.left = (rect.left + x - tooltip.offsetWidth - 10) + 'px';
                        }
                        if (parseInt(tooltip.style.top) + tooltip.offsetHeight > window.innerHeight) {
                            tooltip.style.top = (rect.top + y - tooltip.offsetHeight - 10) + 'px';
                        }
                    } else {
                        document.getElementById('chart-tooltip').style.display = 'none';
                    }
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
                            
                            // Actualizar indicadores en el gráfico
                            updateIndicators(ind);
                            
                            // Actualizar gráfico de velas - SIEMPRE actualizar cuando hay datos
                            if (data.market.ohlc_history && data.market.ohlc_history.length > 0) {
                                // Usar historial completo si está disponible
                                updateChartFromHistory(data.market.ohlc_history);
                            }
                            
                            // SIEMPRE actualizar vela actual en tiempo real con precio actual
                            // Esto asegura que el gráfico se actualice dinámicamente
                            if (data.market && data.market.price !== undefined && data.market.price !== null) {
                                const price = parseFloat(data.market.price);
                                const open = parseFloat(data.market.open || data.market.price);
                                const high = parseFloat(data.market.high || data.market.price);
                                const low = parseFloat(data.market.low || data.market.price);
                                const close = parseFloat(data.market.close || data.market.price);
                                
                                // Forzar actualización del gráfico
                                updateChart({
                                    open: open,
                                    high: high,
                                    low: low,
                                    close: close,
                                    price: price
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
