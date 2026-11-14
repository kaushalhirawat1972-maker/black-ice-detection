"""
Start local FastAPI backend server with on-demand YOLOv8 Model Inference.

Usage:
    python run_backend.py
"""

import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 65)
    print("🚀 Starting Black Ice Detection Local Model & Telemetry Server...")
    print("🌐 Backend running on: http://localhost:8000")
    print("📡 WebSocket endpoint: ws://localhost:8000/ws/live")
    print("🔍 Real-time image prediction: POST http://localhost:8000/api/predict")
    print("=" * 65)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
