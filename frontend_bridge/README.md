# BLACK ICE DETECTION — Communication Bridge & Frontend Guide

This directory contains the bridge between your **custom frontend design**, the **FastAPI Cloud Backend**, and the **Raspberry Pi edge hardware**.

---

## 1. Quick Start (Test Everything Right Now on Your PC)

You can test the entire pipeline on your computer in 3 steps:

### Step 1: Start the Backend Server
Open a terminal in your project root and run:
```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
* **Swagger API Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.
* **WebSocket Endpoint**: `ws://localhost:8000/ws/live`

### Step 2: Start the Edge Simulator
Open a second terminal and run:
```powershell
python edge_pi/simulate_pi.py
```
* It reads test images from your dataset, runs your trained YOLOv8 + thermal + LiDAR pipeline, and pushes live packets to the backend at 1 frame per second.

### Step 3: View Live Telemetry in Browser
Simply double-click or open:
* **`frontend_bridge/dashboard.html`** (Ultra-futuristic 3D frosted glass web dashboard with cursor spotlight, tilt effects, spectrum modes, and demo mode)
* or `frontend_bridge/test_client.html` (Minimal diagnostics test client)

> **Offline Demo Mode**: Even if you haven't started the backend or edge simulator yet, simply opening `frontend_bridge/dashboard.html` will automatically activate **Demo Mode** after 3 seconds, streaming real detection imagery, animated bounding boxes, and multi-sensor telemetry cycles!

---

## 2. Connecting Your Custom Frontend

When you design your own frontend (in React, Next.js, Vue, or HTML/Tailwind), connect it using these endpoints:

### WebSocket Feed (Real-Time Live Updates)
* **URL**: `ws://localhost:8000/ws/live` (or `wss://your-cloud-url.onrender.com/ws/live` on cloud)
* Each message received is a JSON object with:
  ```json
  {
    "timestamp": "2026-10-27 21:20:05",
    "device_id": "vehicle-pi4-front",
    "road_condition": "BLACK_ICE_HAZARD",
    "ice_confidence": 0.942,
    "patch_bbox": [140, 220, 500, 460],
    "estimated_distance_m": 11.8,
    "uncertainty_status": "CONFIRMED_HAZARD",
    "surface_temp_c": -2.5,
    "deicing_active": true,
    "spray_lane": "CENTER DUAL",
    "time_to_impact_sec": 0.71,
    "image_base64": "data:image/jpeg;base64,..."
  }
  ```

### REST Endpoints
* **`GET /api/health`**: System status check.
* **`GET /api/telemetry/latest`**: Fetch the most recent telemetry packet.
* **`GET /api/history`**: Get the list of recent scans for your history table.
* **`POST /api/actuator/command`**: Remote manual spray test pulse trigger.

### For React Developers
Copy:
* `frontend_bridge/types.ts` into your frontend `src/` folder.
* `frontend_bridge/useLiveTelemetry.ts` into your frontend `src/hooks/` folder.
* In any component, simply call:
  ```tsx
  const { telemetry, isConnected } = useLiveTelemetry("ws://localhost:8000/ws/live");
  ```

---

## 3. Running on Real Raspberry Pi 4

1. Copy the `edge_pi/` folder to your Raspberry Pi.
2. Install requirements:
   ```bash
   pip install -r edge_pi/requirements_pi.txt
   ```
3. In `edge_pi/edge_sender.py`, set:
   ```python
   CLOUD_API_URL = "https://your-cloud-backend.onrender.com/api/telemetry"
   ```
4. Run:
   ```bash
   python edge_pi/edge_sender.py
   ```
