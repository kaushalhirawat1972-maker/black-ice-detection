# Black Ice Detection System

Real-time black ice detection and de-icing system using YOLOv8, thermal sensors, and LiDAR.

## Architecture

```
Raspberry Pi / PC (runs YOLOv8 model locally)
        │
        │  POST /api/telemetry  (JSON: detections + camera frame)
        ▼
  Cloud Backend (FastAPI on Render.com)
        │
        │  WebSocket /ws/live  (broadcasts live to dashboard)
        ▼
  Web Dashboard (Next.js on Vercel.com)
```

## Project Structure

```
backend/              FastAPI backend server (deployed on Render)
black-ice-frontend/   Next.js dashboard (deployed on Vercel)
edge_pi/              Raspberry Pi edge client + simulator
src/                  Model training pipeline
models/               Trained YOLOv8 weights (not in git - too large)
```

## Running Locally

### Backend
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd black-ice-frontend/frontend
pnpm install
pnpm dev
```

### Simulator (sends fake RPi data to backend)
```bash
python edge_pi/simulate_pi.py
```

## Deployment

- **Backend**: Render.com (free tier)
- **Frontend**: Vercel.com (free tier)

Set `CLOUD_API_URL` environment variable on the RPi to point to the deployed backend.
