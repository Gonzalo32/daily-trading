"""
Dashboard de monitoreo del bot de trading
Interfaz web profesional para day trading
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
    """Dashboard web profesional para day trading"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.app = FastAPI(title="Trading Bot Dashboard", version="2.0.0")
        self.setup_routes()
        
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
            "current_signal": None,
            "orders": []  # Historial de órdenes ejecutadas
        }
        
    def setup_routes(self):
        """Configurar rutas del dashboard"""
        
        @self.app.get("/")
        async def dashboard_home():
            return HTMLResponse(content=self._get_dashboard_html())
            
        @self.app.get("/api/status")
        async def get_status():
            return {
                "status": "running" if self.is_running else "stopped",
                "timestamp": datetime.now().isoformat(),
                "data": self.current_data
            }
            
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Mantener la conexión viva, o leer mensajes si querés
                    try:
                        await websocket.receive_text()
                    except WebSocketDisconnect:
                        break
            except WebSocketDisconnect:
                pass
            except Exception as e:
                self.logger.error("❌ WebSocket error", exc_info=True)
            finally:
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)

                
    async def start(self):
        """Iniciar el dashboard"""
        try:
            self.is_running = True
            self.logger.info(f"🚀 Dashboard iniciando en puerto {self.config.DASHBOARD_PORT}")
            
            config = uvicorn.Config(
                self.app, 
                host="0.0.0.0", 
                port=self.config.DASHBOARD_PORT,
                log_level="info",
                loop="asyncio"
            )
            self.server = uvicorn.Server(config)
            
            # Iniciar el servidor en una tarea en segundo plano
            async def run_server():
                try:
                    await self.server.serve()
                except Exception as e:
                    self.logger.error(f"❌ Error en servidor dashboard: {e}")
                    self.is_running = False
            
            # Crear tarea y no esperar (corre en segundo plano)
            self.server_task = asyncio.create_task(run_server())
            
            # Esperar un momento para que el servidor inicie
            await asyncio.sleep(2)
            
            self.logger.info(f"✅ Dashboard disponible en: http://localhost:{self.config.DASHBOARD_PORT}")
            self.logger.info(f"✅ Dashboard también en: http://127.0.0.1:{self.config.DASHBOARD_PORT}")
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando dashboard: {e}")
            self.is_running = False
            raise
            
    async def stop(self):
        """Detener el dashboard"""
        try:
            self.is_running = False
            if hasattr(self, 'server'):
                self.server.should_exit = True
            if hasattr(self, 'server_task'):
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
            self.logger.info("🛑 Dashboard detenido")
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo dashboard: {e}")
            
    async def update_data(self, data: Dict[str, Any]):
        """Actualizar datos del dashboard"""
        try:
            if data:
                self.current_data.update(data)
            
            self.current_data["timestamp"] = datetime.now().isoformat()
            self.current_data["status"] = "running" if self.is_running else "stopped"
            
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
            
            await self._broadcast_update()
            
        except Exception as e:
            self.logger.error(f"❌ Error: {e}")
            
    async def _broadcast_update(self):
        """Enviar actualización WebSocket"""
        try:
            if not self.websocket_connections:
                return
            
            try:
                message = json.dumps(self.current_data, default=str)
            except Exception as e:
                self.logger.error(f"Error serialización: {e}")
                return
            
            disconnected = []
            for websocket in self.websocket_connections:
                try:
                    await websocket.send_text(message)
                except Exception:
                    disconnected.append(websocket)
                    
            for websocket in disconnected:
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
                
        except Exception as e:
            self.logger.error(f"❌ Error: {e}")
            
    def _get_dashboard_html(self) -> str:
        """Generar HTML del dashboard profesional"""
        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Pro Trading Dashboard</title>
            <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                
                body {
                    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                    background: #0e0e0e;
                    color: #e0e0e0;
                    overflow: hidden;
                }
                
                .trading-layout {
                    display: grid;
                    grid-template-rows: 50px 1fr 200px;
                    height: 100vh;
                    gap: 2px;
                    background: #000;
                }
                
                /* HEADER */
                .header {
                    background: #1a1a1a;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0 20px;
                    border-bottom: 1px solid #2a2a2a;
                }
                
                .header-left {
                    display: flex;
                    align-items: center;
                    gap: 20px;
                }
                
                .logo {
                    font-size: 18px;
                    font-weight: 700;
                    color: #4CAF50;
                }
                
                .asset-info {
                    display: flex;
                    gap: 15px;
                    font-size: 13px;
                }
                
                .asset-info .item {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }
                
                .asset-info .label {
                    color: #888;
                    font-size: 10px;
                    text-transform: uppercase;
                }
                
                .asset-info .value {
                    font-weight: 600;
                }
                
                .price-up { color: #26a69a; }
                .price-down { color: #ef5350; }
                
                .header-right {
                    display: flex;
                    gap: 10px;
                    align-items: center;
                }
                
                .status-badge {
                    padding: 6px 14px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
                
                .status-running { background: #1b5e20; color: #4CAF50; }
                .status-stopped { background: #b71c1c; color: #ef5350; }
                
                /* MAIN AREA */
                .main-area {
                    display: grid;
                    grid-template-columns: 1fr 300px;
                    gap: 2px;
                    overflow: hidden;
                }
                
                /* CHART AREA */
                .chart-area {
                    display: flex;
                    flex-direction: column;
                    background: #131722;
                }
                
                .chart-toolbar {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 12px;
                    background: #1a1a1a;
                    border-bottom: 1px solid #2a2a2a;
                }
                
                .timeframe-selector {
                    display: flex;
                    gap: 4px;
                }
                
                .timeframe-btn {
                    padding: 6px 12px;
                    background: #2a2a2a;
                    border: none;
                    color: #888;
                    cursor: pointer;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: 600;
                    transition: all 0.2s;
                }
                
                .timeframe-btn:hover {
                    background: #3a3a3a;
                    color: #fff;
                }
                
                .timeframe-btn.active {
                    background: #4CAF50;
                    color: #fff;
                }
                
                .chart-tools {
                    display: flex;
                    gap: 8px;
                }
                
                .tool-btn {
                    padding: 6px 10px;
                    background: transparent;
                    border: 1px solid #3a3a3a;
                    color: #888;
                    cursor: pointer;
                    border-radius: 3px;
                    font-size: 11px;
                    transition: all 0.2s;
                }
                
                .tool-btn:hover {
                    border-color: #4CAF50;
                    color: #4CAF50;
                }
                
                .chart-container {
                    flex: 1;
                    position: relative;
                    overflow: hidden;
                }
                
                #tradingview-chart {
                    width: 100%;
                    height: 100%;
                }
                
                .chart-legend {
                    position: absolute;
                    top: 10px;
                    left: 10px;
                    background: rgba(26, 26, 26, 0.9);
                    padding: 10px;
                    border-radius: 4px;
                    font-size: 12px;
                    pointer-events: none;
                    z-index: 10;
                }
                
                .legend-row {
                    display: flex;
                    gap: 15px;
                    margin-bottom: 5px;
                }
                
                .legend-item {
                    display: flex;
                    gap: 5px;
                    align-items: center;
                }
                
                .legend-label {
                    color: #888;
                }
                
                .legend-value {
                    font-weight: 600;
                }
                
                /* SIDEBAR */
                .sidebar {
                    background: #1a1a1a;
                    display: flex;
                    flex-direction: column;
                    overflow-y: auto;
                }
                
                .sidebar-section {
                    border-bottom: 1px solid #2a2a2a;
                    padding: 12px;
                }
                
                .sidebar-section h3 {
                    font-size: 12px;
                    color: #888;
                    text-transform: uppercase;
                    margin-bottom: 10px;
                    font-weight: 600;
                }
                
                .info-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 8px;
                }
                
                .info-item {
                    display: flex;
                    flex-direction: column;
                    gap: 3px;
                }
                
                .info-label {
                    font-size: 10px;
                    color: #888;
                    text-transform: uppercase;
                }
                
                .info-value {
                    font-size: 13px;
                    font-weight: 600;
                }
                
                .signal-card {
                    background: #2a2a2a;
                    padding: 10px;
                    border-radius: 4px;
                    margin-bottom: 8px;
                }
                
                .signal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }
                
                .signal-action {
                    font-size: 14px;
                    font-weight: 700;
                }
                
                .signal-buy { color: #26a69a; }
                .signal-sell { color: #ef5350; }
                
                .signal-strength {
                    font-size: 11px;
                    color: #888;
                }
                
                .positions-list {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                
                .position-card {
                    background: #2a2a2a;
                    padding: 10px;
                    border-radius: 4px;
                    border-left: 3px solid;
                }
                
                .position-card.buy { border-left-color: #26a69a; }
                .position-card.sell { border-left-color: #ef5350; }
                
                .position-header {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 6px;
                }
                
                .position-symbol {
                    font-weight: 700;
                    font-size: 13px;
                }
                
                .position-pnl {
                    font-size: 13px;
                    font-weight: 600;
                }
                
                /* BOTTOM PANEL */
                .bottom-panel {
                    background: #1a1a1a;
                    border-top: 1px solid #2a2a2a;
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 20px;
                    padding: 15px;
                    overflow-y: auto;
                }
                
                .panel-card {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                
                .panel-card h4 {
                    font-size: 11px;
                    color: #888;
                    text-transform: uppercase;
                    font-weight: 600;
                }
                
                .orders-table {
                    font-size: 11px;
                }
                
                .order-row {
                    display: grid;
                    grid-template-columns: 50px 1fr 80px 80px;
                    gap: 8px;
                    padding: 6px 0;
                    border-bottom: 1px solid #2a2a2a;
                }
                
                .order-marker {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    margin-top: 2px;
                }
                
                .marker-buy { background: #26a69a; }
                .marker-sell { background: #ef5350; }
                
                /* HOTKEYS OVERLAY */
                .hotkeys-overlay {
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: rgba(26, 26, 26, 0.98);
                    border: 1px solid #4CAF50;
                    border-radius: 8px;
                    padding: 20px;
                    display: none;
                    z-index: 1000;
                }
                
                .hotkeys-overlay.show {
                    display: block;
                }
                
                .hotkey-list {
                    display: grid;
                    grid-template-columns: 100px 1fr;
                    gap: 10px;
                    font-size: 13px;
                }
                
                .hotkey-key {
                    background: #2a2a2a;
                    padding: 4px 8px;
                    border-radius: 3px;
                    text-align: center;
                    font-weight: 600;
                    color: #4CAF50;
                }
                
                /* ALERTS */
                .alert-badge {
                    position: absolute;
                    top: 50%;
                    right: 10px;
                    transform: translateY(-50%);
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #ff9800;
                    animation: pulse 2s infinite;
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.3; }
                }
                
                /* SCROLLBAR */
                ::-webkit-scrollbar {
                    width: 6px;
                    height: 6px;
                }
                
                ::-webkit-scrollbar-track {
                    background: #1a1a1a;
                }
                
                ::-webkit-scrollbar-thumb {
                    background: #3a3a3a;
                    border-radius: 3px;
                }
                
                ::-webkit-scrollbar-thumb:hover {
                    background: #4a4a4a;
                }
            </style>
        </head>
        <body>
            <div class="trading-layout">
                <!-- HEADER -->
                <div class="header">
                    <div class="header-left">
                        <div class="logo">⚡ PRO TRADING BOT</div>
                        <div class="asset-info">
                            <div class="item">
                                <span class="label">Símbolo</span>
                                <span class="value" id="header-symbol">BTC/USDT</span>
                            </div>
                            <div class="item">
                                <span class="label">Precio</span>
                                <span class="value" id="header-price">-</span>
                            </div>
                            <div class="item">
                                <span class="label">24h Change</span>
                                <span class="value" id="header-change">-</span>
                            </div>
                            <div class="item">
                                <span class="label">24h High</span>
                                <span class="value" id="header-high">-</span>
                            </div>
                            <div class="item">
                                <span class="label">24h Low</span>
                                <span class="value" id="header-low">-</span>
                            </div>
                            <div class="item">
                                <span class="label">Volume</span>
                                <span class="value" id="header-volume">-</span>
                            </div>
                        </div>
                    </div>
                    <div class="header-right">
                        <span id="timestamp" style="font-size: 11px; color: #888;">-</span>
                        <div class="status-badge" id="status">Conectando...</div>
                    </div>
                </div>
                
                <!-- MAIN AREA -->
                <div class="main-area">
                    <!-- CHART AREA -->
                    <div class="chart-area">
                        <div class="chart-toolbar">
                            <div class="timeframe-selector">
                                <button class="timeframe-btn" data-timeframe="1m">1m</button>
                                <button class="timeframe-btn" data-timeframe="5m">5m</button>
                                <button class="timeframe-btn active" data-timeframe="1h">1h</button>
                                <button class="timeframe-btn" data-timeframe="4h">4h</button>
                                <button class="timeframe-btn" data-timeframe="1d">1D</button>
                            </div>
                            <div class="chart-tools">
                                <button class="tool-btn" onclick="toggleIndicator('vwap')">📊 VWAP</button>
                                <button class="tool-btn" onclick="toggleIndicator('ema')">📈 EMA</button>
                                <button class="tool-btn" onclick="toggleIndicator('volume')">📊 Volume</button>
                                <button class="tool-btn" onclick="resetChartView()">🔄 Reset</button>
                                <button class="tool-btn" onclick="toggleHotkeys()">⌨️ Hotkeys</button>
                            </div>
                        </div>
                        <div class="chart-container">
                            <div id="tradingview-chart"></div>
                            <div class="chart-legend">
                                <div class="legend-row">
                                    <div class="legend-item">
                                        <span class="legend-label">O:</span>
                                        <span class="legend-value" id="legend-open">-</span>
                                    </div>
                                    <div class="legend-item">
                                        <span class="legend-label">H:</span>
                                        <span class="legend-value" id="legend-high">-</span>
                                    </div>
                                    <div class="legend-item">
                                        <span class="legend-label">L:</span>
                                        <span class="legend-value" id="legend-low">-</span>
                                    </div>
                                    <div class="legend-item">
                                        <span class="legend-label">C:</span>
                                        <span class="legend-value" id="legend-close">-</span>
                                    </div>
                                </div>
                                <div class="legend-row">
                                    <div class="legend-item">
                                        <span class="legend-label">Vol:</span>
                                        <span class="legend-value" id="legend-volume">-</span>
                                    </div>
                                    <div class="legend-item">
                                        <span class="legend-label">Velas:</span>
                                        <span class="legend-value" id="legend-candles">0</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- SIDEBAR -->
                    <div class="sidebar">
                        <div class="sidebar-section">
                            <h3>🎯 Señal Actual</h3>
                            <div class="signal-card" id="signal-container">
                                <div class="signal-header">
                                    <span class="signal-action" id="signal-action">Analizando...</span>
                                    <span class="signal-strength" id="signal-strength">-</span>
                                </div>
                                <div class="info-item">
                                    <span class="info-label">Razón</span>
                                    <span class="info-value" id="signal-reason">-</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="sidebar-section">
                            <h3>📊 Indicadores</h3>
                            <div class="info-grid">
                                <div class="info-item">
                                    <span class="info-label">RSI</span>
                                    <span class="info-value" id="ind-rsi">-</span>
                                </div>
                                <div class="info-item">
                                    <span class="info-label">EMA 9</span>
                                    <span class="info-value" id="ind-ema9">-</span>
                                </div>
                                <div class="info-item">
                                    <span class="info-label">EMA 21</span>
                                    <span class="info-value" id="ind-ema21">-</span>
                                </div>
                                <div class="info-item">
                                    <span class="info-label">MACD</span>
                                    <span class="info-value" id="ind-macd">-</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="sidebar-section">
                            <h3>💼 Posiciones</h3>
                            <div class="positions-list" id="positions-list">
                                <div style="color: #888; font-size: 12px; text-align: center; padding: 20px;">
                                    Sin posiciones
                                </div>
                            </div>
                        </div>
                        
                        <div class="sidebar-section">
                            <h3>💰 Balance</h3>
                            <div class="info-grid">
                                <div class="info-item">
                                    <span class="info-label">Balance</span>
                                    <span class="info-value" id="balance-current">-</span>
                                </div>
                                <div class="info-item">
                                    <span class="info-label">PnL Diario</span>
                                    <span class="info-value" id="balance-pnl">-</span>
                                </div>
                                <div class="info-item">
                                    <span class="info-label">Exposición</span>
                                    <span class="info-value" id="balance-exposure">-</span>
                                </div>
                                <div class="info-item">
                                    <span class="info-label">Trades</span>
                                    <span class="info-value" id="balance-trades">-</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- BOTTOM PANEL -->
                <div class="bottom-panel">
                    <div class="panel-card">
                        <h4>📋 Órdenes Ejecutadas</h4>
                        <div class="orders-table" id="orders-table">
                            <div style="color: #888; font-size: 11px;">Sin órdenes</div>
                        </div>
                    </div>
                    <div class="panel-card">
                        <h4>📈 Métricas</h4>
                        <div class="info-item">
                            <span class="info-label">Win Rate</span>
                            <span class="info-value" id="metric-winrate">-</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Max Drawdown</span>
                            <span class="info-value" id="metric-drawdown">-</span>
                        </div>
                    </div>
                    <div class="panel-card">
                        <h4>🔔 Alertas Activas</h4>
                        <div id="alerts-list" style="font-size: 11px; color: #888;">
                            <div>✓ Bot operando</div>
                            <div>✓ Conexión estable</div>
                        </div>
                    </div>
                    <div class="panel-card">
                        <h4>ℹ️ Info del Sistema</h4>
                        <div class="info-item">
                            <span class="info-label">Latencia</span>
                            <span class="info-value" id="system-latency">< 100ms</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Uptime</span>
                            <span class="info-value" id="system-uptime">00:00:00</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- HOTKEYS OVERLAY -->
            <div class="hotkeys-overlay" id="hotkeys-overlay">
                <h3 style="margin-bottom: 15px; color: #4CAF50;">⌨️ Atajos de Teclado</h3>
                <div class="hotkey-list">
                    <span class="hotkey-key">Espacio</span><span>Pausar/Reanudar</span>
                    <span class="hotkey-key">R</span><span>Reset Vista</span>
                    <span class="hotkey-key">V</span><span>Toggle VWAP</span>
                    <span class="hotkey-key">E</span><span>Toggle EMAs</span>
                    <span class="hotkey-key">+/-</span><span>Zoom In/Out</span>
                    <span class="hotkey-key">←/→</span><span>Navegar</span>
                    <span class="hotkey-key">H</span><span>Ver Hotkeys</span>
                    <span class="hotkey-key">ESC</span><span>Cerrar</span>
                </div>
            </div>
            
            <script>
                // Estado global
                let ws = null;
                let chart = null;
                let candlestickSeries = null;
                let volumeSeries = null;
                let vwapSeries = null;
                let ema9Series = null;
                let ema21Series = null;
                let historicalCandles = [];
                let orderMarkers = [];
                let lastHistoryLength = 0;
                let startTime = Date.now();
                let showVWAP = true;
                let showEMA = true;
                let showVolume = true;
                
                // Inicializar gráfico
                function initChart() {
                    const container = document.getElementById('tradingview-chart');
                    if (!container || typeof LightweightCharts === 'undefined') return;
                    
                    chart = LightweightCharts.createChart(container, {
                        layout: {
                            background: { type: 'solid', color: '#131722' },
                            textColor: '#d1d5db',
                        },
                        grid: {
                            vertLines: { color: '#1e222d' },
                            horzLines: { color: '#1e222d' },
                        },
                        crosshair: {
                            mode: LightweightCharts.CrosshairMode.Normal,
                            vertLine: {
                                color: '#758696',
                                width: 1,
                                style: LightweightCharts.LineStyle.Dashed,
                            },
                            horzLine: {
                                color: '#758696',
                                width: 1,
                                style: LightweightCharts.LineStyle.Dashed,
                            },
                        },
                        rightPriceScale: {
                            borderColor: '#2b2b43',
                            scaleMargins: {
                                top: 0.02,
                                bottom: 0.02,
                            },
                            mode: LightweightCharts.PriceScaleMode.Normal,
                            autoScale: true,
                        },
                        timeScale: {
                            borderColor: '#2b2b43',
                            timeVisible: true,
                            secondsVisible: false,
                        },
                        width: container.clientWidth,
                        height: container.clientHeight,
                        localization: {
                            locale: 'es-ES',
                        },
                        handleScroll: {
                            mouseWheel: true,
                            pressedMouseMove: true,
                        },
                        handleScale: {
                            axisPressedMouseMove: {
                                time: true,
                                price: true,
                            },
                            mouseWheel: true,
                            pinch: true,
                        },
                    });
                    
                    chart.timeScale().applyOptions({
                        rightOffset: 6,
                        barSpacing: 10,
                        minBarSpacing: 0.5,
                        fixRightEdge: false,
                        lockVisibleTimeRangeOnResize: false,
                    });
                    
                    // Series principales
                    candlestickSeries = chart.addCandlestickSeries({
                        upColor: '#26a69a',
                        downColor: '#ef5350',
                        wickUpColor: '#26a69a',
                        wickDownColor: '#ef5350',
                        borderUpColor: '#1e8e81',
                        borderDownColor: '#d64c46',
                        borderVisible: true,
                        wickVisible: true,
                        priceLineVisible: true,
                        priceFormat: {
                            type: 'price',
                            precision: 2,
                            minMove: 0.01,
                        },
                    });
                    
                    volumeSeries = chart.addHistogramSeries({
                        color: '#26a69a',
                        priceFormat: {
                            type: 'volume',
                        },
                        priceScaleId: '',
                        scaleMargins: {
                            top: 0.92,
                            bottom: 0,
                        },
                    });
                    
                    // EMA 9
                    ema9Series = chart.addLineSeries({
                        color: '#2196F3',
                        lineWidth: 2,
                        title: 'EMA 9',
                    });
                    
                    // EMA 21
                    ema21Series = chart.addLineSeries({
                        color: '#FF9800',
                        lineWidth: 2,
                        title: 'EMA 21',
                    });
                    
                    // VWAP
                    vwapSeries = chart.addLineSeries({
                        color: '#9C27B0',
                        lineWidth: 2,
                        lineStyle: LightweightCharts.LineStyle.Dashed,
                        title: 'VWAP',
                    });
                    
                    // Resize
                    window.addEventListener('resize', () => {
                        if (chart) {
                            chart.applyOptions({
                                width: container.clientWidth,
                                height: container.clientHeight,
                            });
                        }
                    });
                    
                    // Subscribe to crosshair moves
                    chart.subscribeCrosshairMove((param) => {
                        if (param.time && param.seriesData.get(candlestickSeries)) {
                            const data = param.seriesData.get(candlestickSeries);
                            updateLegend(data);
                        }
                    });
                }
                
                // Actualizar leyenda
                function updateLegend(data) {
                    if (!data) return;
                    document.getElementById('legend-open').textContent = data.open?.toFixed(2) || '-';
                    document.getElementById('legend-high').textContent = data.high?.toFixed(2) || '-';
                    document.getElementById('legend-low').textContent = data.low?.toFixed(2) || '-';
                    document.getElementById('legend-close').textContent = data.close?.toFixed(2) || '-';
                }
                
                // Actualizar gráfico
                function updateChart(ohlcHistory) {
                    if (!chart || !candlestickSeries || !Array.isArray(ohlcHistory) || ohlcHistory.length === 0) {
                        return;
                    }
                    
                    if (ohlcHistory.length === lastHistoryLength && historicalCandles.length > 0) {
                        const lastCandle = ohlcHistory[ohlcHistory.length - 1];
                        const timeInSeconds = Math.floor(new Date(lastCandle.timestamp).getTime() / 1000);
                        
                        if (!isNaN(timeInSeconds) && timeInSeconds > 0) {
                            const candleData = {
                                time: timeInSeconds,
                                open: parseFloat(lastCandle.open),
                                high: parseFloat(lastCandle.high),
                                low: parseFloat(lastCandle.low),
                                close: parseFloat(lastCandle.close),
                            };
                            
                            candlestickSeries.update(candleData);
                            
                            if (volumeSeries && showVolume) {
                                volumeSeries.update({
                                    time: timeInSeconds,
                                    value: parseFloat(lastCandle.volume || 0),
                                    color: candleData.close >= candleData.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
                                });
                            }
                            
                            chart.priceScale('right').applyOptions({ autoScale: true });
                            updateLegend(candleData);
                        }
                        return;
                    }
                    
                    historicalCandles = ohlcHistory
                        .map(c => {
                            const timeInSeconds = Math.floor(new Date(c.timestamp).getTime() / 1000);
                            return {
                                time: timeInSeconds,
                                open: parseFloat(c.open),
                                high: parseFloat(c.high),
                                low: parseFloat(c.low),
                                close: parseFloat(c.close),
                                volume: parseFloat(c.volume || 0),
                            };
                        })
                        .filter(c => !isNaN(c.time) && c.time > 0)
                        .sort((a, b) => a.time - b.time);
                    
                    if (historicalCandles.length > 0) {
                        candlestickSeries.setData(historicalCandles);
                        
                        // Volume
                        if (volumeSeries && showVolume) {
                            const volumeData = historicalCandles.map(c => ({
                                time: c.time,
                                value: c.volume,
                                color: c.close >= c.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
                            }));
                            volumeSeries.setData(volumeData);
                        }
                        
                        // EMA 9 y 21
                        if (showEMA) {
                            const ema9Data = calculateEMA(historicalCandles, 9);
                            const ema21Data = calculateEMA(historicalCandles, 21);
                            ema9Series.setData(ema9Data);
                            ema21Series.setData(ema21Data);
                        }
                        
                        // VWAP
                        if (showVWAP) {
                            const vwapData = calculateVWAP(historicalCandles);
                            vwapSeries.setData(vwapData);
                        }
                        
                        chart.timeScale().fitContent();
                        chart.timeScale().scrollToRealTime();
                        chart.priceScale('right').applyOptions({ autoScale: true });
                        lastHistoryLength = ohlcHistory.length;
                        
                        document.getElementById('legend-candles').textContent = historicalCandles.length;
                        
                        const last = historicalCandles[historicalCandles.length - 1];
                        updateLegend(last);
                        document.getElementById('legend-volume').textContent = last.volume.toFixed(2);
                    }
                }
                
                // Calcular EMA
                function calculateEMA(candles, period) {
                    if (candles.length < period) return [];
                    
                    const k = 2 / (period + 1);
                    let ema = candles[0].close;
                    const result = [{ time: candles[0].time, value: ema }];
                    
                    for (let i = 1; i < candles.length; i++) {
                        ema = candles[i].close * k + ema * (1 - k);
                        result.push({ time: candles[i].time, value: ema });
                    }
                    
                    return result;
                }
                
                // Calcular VWAP
                function calculateVWAP(candles) {
                    let cumulativeTPV = 0;
                    let cumulativeVolume = 0;
                    const result = [];
                    
                    for (const candle of candles) {
                        const typicalPrice = (candle.high + candle.low + candle.close) / 3;
                        cumulativeTPV += typicalPrice * candle.volume;
                        cumulativeVolume += candle.volume;
                        
                        if (cumulativeVolume > 0) {
                            result.push({
                                time: candle.time,
                                value: cumulativeTPV / cumulativeVolume
                            });
                        }
                    }
                    
                    return result;
                }
                
                // Toggle indicadores
                function toggleIndicator(indicator) {
                    if (indicator === 'vwap') {
                        showVWAP = !showVWAP;
                        if (vwapSeries) {
                            vwapSeries.applyOptions({ visible: showVWAP });
                        }
                    } else if (indicator === 'ema') {
                        showEMA = !showEMA;
                        if (ema9Series && ema21Series) {
                            ema9Series.applyOptions({ visible: showEMA });
                            ema21Series.applyOptions({ visible: showEMA });
                        }
                    } else if (indicator === 'volume') {
                        showVolume = !showVolume;
                        if (volumeSeries) {
                            volumeSeries.applyOptions({ visible: showVolume });
                        }
                    }
                }
                
                // Reset vista
                function resetChartView() {
                    if (chart) {
                        chart.timeScale().fitContent();
                    }
                }
                
                // Toggle hotkeys
                function toggleHotkeys() {
                    const overlay = document.getElementById('hotkeys-overlay');
                    overlay.classList.toggle('show');
                }
                
                // WebSocket
                function connectWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}/ws`;
                    ws = new WebSocket(wsUrl);
                    
                    ws.onopen = () => {
                        document.getElementById('status').textContent = 'Conectado';
                        document.getElementById('status').className = 'status-badge status-running';
                    };
                    
                    ws.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            updateDashboard(data);
                        } catch (e) {
                            console.error('Error:', e);
                        }
                    };
                    
                    ws.onclose = () => {
                        document.getElementById('status').textContent = 'Desconectado';
                        document.getElementById('status').className = 'status-badge status-stopped';
                        setTimeout(connectWebSocket, 5000);
                    };
                }
                
                // Actualizar dashboard
                function updateDashboard(data) {
                    // Timestamp
                    document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleString('es-ES', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                    });
                    
                    // Header info
                    if (data.market) {
                        const m = data.market;
                        document.getElementById('header-symbol').textContent = m.symbol || '-';
                        document.getElementById('header-price').textContent = m.price ? '$' + m.price.toFixed(2) : '-';
                        
                        const changeEl = document.getElementById('header-change');
                        if (m.change_percent !== undefined) {
                            changeEl.textContent = (m.change_percent >= 0 ? '+' : '') + m.change_percent.toFixed(2) + '%';
                            changeEl.className = m.change_percent >= 0 ? 'price-up' : 'price-down';
                        }
                        
                        document.getElementById('header-high').textContent = m.high ? '$' + m.high.toFixed(2) : '-';
                        document.getElementById('header-low').textContent = m.low ? '$' + m.low.toFixed(2) : '-';
                        document.getElementById('header-volume').textContent = m.volume ? m.volume.toFixed(2) : '-';
                        
                        // Indicadores
                        if (m.indicators) {
                            const ind = m.indicators;
                            document.getElementById('ind-rsi').textContent = ind.rsi?.toFixed(2) || '-';
                            document.getElementById('ind-ema9').textContent = ind.fast_ma?.toFixed(2) || '-';
                            document.getElementById('ind-ema21').textContent = ind.slow_ma?.toFixed(2) || '-';
                            document.getElementById('ind-macd').textContent = ind.macd?.toFixed(4) || '-';
                        }
                        
                        // Gráfico
                        if (m.ohlc_history && m.ohlc_history.length > 0) {
                            updateChart(m.ohlc_history);
                        }
                    }
                    
                    // Señal actual
                    if (data.current_signal) {
                        const sig = data.current_signal;
                        const actionEl = document.getElementById('signal-action');
                        actionEl.textContent = sig.action || 'Analizando...';
                        actionEl.className = 'signal-action ' + (sig.action === 'BUY' ? 'signal-buy' : sig.action === 'SELL' ? 'signal-sell' : '');
                        document.getElementById('signal-strength').textContent = sig.strength ? 'Fuerza: ' + (sig.strength * 100).toFixed(1) + '%' : '';
                        document.getElementById('signal-reason').textContent = sig.reason || '-';
                    }
                    
                    // Posiciones
                    if (data.positions && data.positions.length > 0) {
                        const html = data.positions.map(pos => `
                            <div class="position-card ${pos.side.toLowerCase()}">
                                <div class="position-header">
                                    <span class="position-symbol">${pos.symbol} ${pos.side}</span>
                                    <span class="position-pnl ${pos.pnl >= 0 ? 'price-up' : 'price-down'}">
                                        ${pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                                    </span>
                                </div>
                                <div style="font-size: 11px; color: #888;">
                                    <div>Entry: $${pos.entry_price.toFixed(4)}</div>
                                    <div>Size: ${pos.size.toFixed(4)}</div>
                                </div>
                            </div>
                        `).join('');
                        document.getElementById('positions-list').innerHTML = html;
                    } else {
                        document.getElementById('positions-list').innerHTML = '<div style="color: #888; font-size: 12px; text-align: center; padding: 20px;">Sin posiciones</div>';
                    }
                    
                    // Balance
                    if (data.balance) {
                        document.getElementById('balance-current').textContent = '$' + (data.balance.current?.toFixed(2) || '-');
                        const pnl = data.metrics?.daily_pnl || 0;
                        const pnlEl = document.getElementById('balance-pnl');
                        pnlEl.textContent = (pnl >= 0 ? '+' : '') + '$' + pnl.toFixed(2);
                        pnlEl.style.color = pnl >= 0 ? '#26a69a' : '#ef5350';
                        document.getElementById('balance-exposure').textContent = '$' + (data.balance.exposure?.toFixed(2) || '0');
                        document.getElementById('balance-trades').textContent = data.metrics?.daily_trades || '0';
                    }
                    
                    // Métricas
                    if (data.metrics) {
                        document.getElementById('metric-winrate').textContent = data.metrics.win_rate ? (data.metrics.win_rate * 100).toFixed(1) + '%' : '-';
                        document.getElementById('metric-drawdown').textContent = data.metrics.max_drawdown ? (data.metrics.max_drawdown * 100).toFixed(1) + '%' : '-';
                    }
                    
                    // Uptime
                    const uptime = Math.floor((Date.now() - startTime) / 1000);
                    const hours = Math.floor(uptime / 3600).toString().padStart(2, '0');
                    const minutes = Math.floor((uptime % 3600) / 60).toString().padStart(2, '0');
                    const seconds = (uptime % 60).toString().padStart(2, '0');
                    document.getElementById('system-uptime').textContent = `${hours}:${minutes}:${seconds}`;
                }
                
                // Hotkeys
                document.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape') {
                        document.getElementById('hotkeys-overlay').classList.remove('show');
                    } else if (e.key === 'h' || e.key === 'H') {
                        toggleHotkeys();
                    } else if (e.key === 'r' || e.key === 'R') {
                        resetChartView();
                    } else if (e.key === 'v' || e.key === 'V') {
                        toggleIndicator('vwap');
                    } else if (e.key === 'e' || e.key === 'E') {
                        toggleIndicator('ema');
                    }
                });
                
                // Inicializar
                window.onload = () => {
                    initChart();
                    connectWebSocket();
                };
                
                window.onbeforeunload = () => {
                    if (ws) ws.close();
                };
            </script>
        </body>
        </html>
        """

