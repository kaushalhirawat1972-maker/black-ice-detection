"""
FastAPI Cloud Telemetry & Communication Server.
Acts as the central relay between vehicle Raspberry Pi edge nodes and web frontends.
"""

import json
import logging
import os
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

try:
    from backend.schemas import TelemetryPacket, DeicingCommand, SystemHealth  # when run from project root
except ImportError:
    from schemas import TelemetryPacket, DeicingCommand, SystemHealth           # when run from backend/ folder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BlackIceDetectionBackend")

app = FastAPI(
    title="BLACK ICE DETECTION - Cloud Communication API",
    description="Real-time multi-sensor telemetry relay for Black Ice Detection & Autonomous De-icing",
    version="1.0.0"
)

# Enable CORS for local dev and cloud deployments (Vercel, Netlify, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Cache
latest_telemetry: Dict[str, Any] = {}
scan_history: List[Dict[str, Any]] = []
MAX_HISTORY = 100

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Frontend client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Frontend client disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Error broadcasting to client: {e}")
                self.disconnect(connection)

manager = ConnectionManager()


# Static Files and Dashboard Mount
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend_bridge"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/dashboard")
async def get_dashboard():
    dashboard_path = os.path.join(frontend_dir, "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"error": "dashboard.html not found"}


@app.get("/")
def root():
    return {
        "service": "BLACK ICE DETECTION",
        "status": "active",
        "docs_url": "/docs",
        "websocket_url": "/ws/live"
    }


@app.get("/api/health", response_model=SystemHealth)
def get_health():
    """Healthcheck endpoint for system status pills."""
    return SystemHealth()


@app.get("/api/telemetry/latest")
def get_latest_telemetry():
    """Fetch the latest snapshot of road conditions and sensor telemetry."""
    if not latest_telemetry:
        return {"status": "waiting_for_data", "message": "No vehicle edge packets received yet."}
    return latest_telemetry


@app.get("/api/history")
def get_scan_history(limit: int = 50):
    """Retrieve recent road scan records for the Scans History table."""
    return scan_history[-limit:]


@app.post("/api/telemetry")
async def ingest_telemetry(packet: TelemetryPacket):
    """
    Called by Raspberry Pi edge client (or PC simulator) to push new frame and sensor data.
    """
    global latest_telemetry
    data_dict = packet.model_dump()
    latest_telemetry = data_dict

    # Append to rolling history
    scan_history.append({
        "timestamp": packet.timestamp,
        "device_id": packet.device_id,
        "road_condition": packet.road_condition,
        "ice_confidence": packet.ice_confidence,
        "surface_temp_c": packet.surface_temp_c,
        "estimated_distance_m": packet.estimated_distance_m,
        "uncertainty_status": packet.uncertainty_status,
        "deicing_active": packet.deicing_active
    })
    if len(scan_history) > MAX_HISTORY:
        scan_history.pop(0)

    # Broadcast to all live web dashboard browsers via WebSocket
    payload_str = json.dumps(data_dict)
    await manager.broadcast(payload_str)

    return {"status": "acknowledged", "broadcast_clients": len(manager.active_connections)}


@app.post("/api/actuator/command")
async def send_actuator_command(cmd: DeicingCommand):
    """
    Remote de-icing actuation override trigger from web dashboard.
    """
    logger.info(f"Manual actuation dispatched: {cmd.action} for {cmd.duration_ms}ms to {cmd.target_lane}")
    return {"status": "command_sent", "details": cmd.model_dump()}


@app.websocket("/ws/live")
async def live_telemetry_stream(websocket: WebSocket):
    """
    High-speed WebSocket endpoint delivering live camera frames and telemetry to frontend.
    """
    await manager.connect(websocket)
    try:
        # Send current state immediately upon connection
        if latest_telemetry:
            await websocket.send_text(json.dumps(latest_telemetry))
        while True:
            # Keep connection open; receive heartbeats / commands
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
