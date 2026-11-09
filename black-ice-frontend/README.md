# BLACK ICE DETECTION — Next.js 3D Frontend

This is your custom Next.js 16 + React 19 + Tailwind CSS + Framer Motion dashboard for the **BLACK ICE DETECTION — ROAD PERCEPTION INTELLIGENCE** system.

---

## 🚀 How to Run the Frontend

### 1. Start the Development Server
Open PowerShell in the `black-ice-frontend/frontend/` folder:
```powershell
cd black-ice-frontend/frontend
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## ⚡ Connecting to the Live Python AI Pipeline

Your frontend supports both **Offline Simulation** and **Live AI Streaming**:

1. **Automatic Offline Simulation**: If the backend is not running, the dashboard runs realistic scenario cycles (Hazard $\rightarrow$ Wet Road $\rightarrow$ Clear) with dynamic jitter.
2. **Live AI Inference Stream**:
   - Start the FastAPI backend server in a separate terminal:
     ```powershell
     uvicorn backend.main:app --port 8000
     ```
   - Start the Edge Simulator:
     ```powershell
     python edge_pi/simulate_pi.py
     ```
   - As soon as the backend is running, the top status badge will shift to **`LIVE STREAM`**, streaming real-time YOLOv8 detections, sub-zero MLX90640 thermals, and LiDAR distance telemetry directly to your Next.js dashboard!

---

## 📦 What We Configured & Verified

1. **Production Build Verified**:
   - `npm run build` compiles with zero errors (`Exit code 0`).
   - Server-side font loader was stabilized so the build works offline and behind proxies without network blocking.
2. **Universal Telemetry Adapter**:
   - `components/telemetry-provider.tsx` automatically maps both Python backend packets (`road_condition`, `surface_temp_c`, `estimated_distance_m`, `uncertainty_status`, `patch_bbox`) and Next.js frontend state variables.
3. **Environment Config**:
   - Created `.env.local` configured to `ws://localhost:8000/ws/live`.
