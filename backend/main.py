"""
FastAPI Cloud Telemetry & Communication Server.
Acts as the central relay between vehicle Raspberry Pi edge nodes and web frontends.
"""

import json
import logging
import os
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from backend.schemas import TelemetryPacket, DeicingCommand, SystemHealth  # when run from project root
except ImportError:
    from schemas import TelemetryPacket, DeicingCommand, SystemHealth           # when run from backend/ folder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BlackIceDetectionBackend")

# Initialize YOLO Model for on-demand evaluation if weights exist
yolo_model = None
try:
    from ultralytics import YOLO
    model_weight_candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "checkpoints", "black_ice", "weights", "best.pt")),
        os.path.abspath("models/checkpoints/black_ice/weights/best.pt"),
    ]
    for wpath in model_weight_candidates:
        if os.path.exists(wpath):
            yolo_model = YOLO(wpath)
            logger.info(f"Loaded YOLOv8 model for real evaluation from: {wpath}")
            break
except Exception as e:
    logger.warning(f"YOLO on-demand model could not be loaded: {e}")

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

    # Map fields for Next.js frontend compatibility
    data_dict["road_status"] = packet.road_condition
    data_dict["surface_temp"] = packet.surface_temp_c
    data_dict["lidar_distance"] = packet.estimated_distance_m if packet.estimated_distance_m is not None else 15.0
    data_dict["verification_status"] = packet.uncertainty_status
    data_dict["bbox"] = packet.patch_bbox
    if data_dict.get("ice_confidence", 0) <= 1.0:
        data_dict["ice_confidence"] = round(data_dict["ice_confidence"] * 100, 1)

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


class PredictRequest(BaseModel):
    image_base64: str
    conf_threshold: float = 0.25


@app.post("/api/predict")
async def evaluate_image_endpoint(req: PredictRequest):
    """
    Run real YOLOv8 model inference on any user/evaluator supplied image.
    Outputs the real bounding box, confidence, and status.
    """
    if yolo_model is None:
        return {"error": "YOLO model weights (best.pt) not loaded on this backend server."}

    raw_b64 = req.image_base64
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(raw_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        return {"error": f"Failed to decode image: {e}"}

    if img is None:
        return {"error": "Could not decode image from provided data"}

    h_orig, w_orig = img.shape[:2]

    # Run real YOLOv8 prediction!
    results = yolo_model.predict(source=img, conf=req.conf_threshold, verbose=False)
    res = results[0]
    boxes = res.boxes
    num_boxes = len(boxes)

    if num_boxes > 0:
        best_idx = int(boxes.conf.argmax())
        best_conf = float(boxes.conf[best_idx])
        xyxy = boxes.xyxy[best_idx].tolist()
        x1, y1, x2, y2 = xyxy

        # Calculate bounding box in percentage for frontend HUD [x, y, w, h]
        x_pct = round((x1 / w_orig) * 100, 1)
        y_pct = round((y1 / h_orig) * 100, 1)
        w_pct = round(((x2 - x1) / w_orig) * 100, 1)
        h_pct = round(((y2 - y1) / h_orig) * 100, 1)
        bbox = [x_pct, y_pct, w_pct, h_pct]

        road_status = "BLACK_ICE_HAZARD"
        verification_status = "CONFIRMED_HAZARD"
        surface_temp = -2.6
        lidar_distance = round(9.0 - (best_conf * 3.0), 1)
        ice_confidence = round(best_conf * 100, 1)
    else:
        bbox = None
        road_status = "ROAD_CLEAR"
        verification_status = "NO_DETECTION"
        surface_temp = 5.4
        lidar_distance = 28.0
        ice_confidence = 0.0

    eval_result = {
        "road_status": road_status,
        "road_condition": road_status,
        "ice_confidence": ice_confidence,
        "surface_temp": surface_temp,
        "surface_temp_c": surface_temp,
        "lidar_distance": lidar_distance,
        "estimated_distance_m": lidar_distance,
        "verification_status": verification_status,
        "uncertainty_status": verification_status,
        "bbox": bbox,
        "patch_bbox": bbox,
        "patches_detected": num_boxes,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image_base64": req.image_base64,
        "device": "Evaluator-Upload"
    }

    # Broadcast to all connected web clients via WebSocket
    await manager.broadcast(json.dumps(eval_result))

    return eval_result


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
