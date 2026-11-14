"""
Stream YOLOv8 Black Ice Model predictions to the Frontend Dashboard.

This script runs your trained model on test images and pushes the live
predictions (image, bounding box, confidence, temp, LiDAR) to your backend,
which broadcasts them in real time to your frontend (localhost:3000 or Vercel).

Usage:
  # Stream to your cloud backend on Render (default)
  python stream_model_to_frontend.py

  # Stream to a local backend if running locally
  python stream_model_to_frontend.py --backend http://localhost:8000

  # Step through images one-by-one by pressing Enter
  python stream_model_to_frontend.py --step

  # Test a specific image or folder
  python stream_model_to_frontend.py --source path/to/images
"""

import argparse
import base64
import glob
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import cv2
import requests
from ultralytics import YOLO

DEFAULT_BACKEND = "https://black-ice-detection-w33c.onrender.com"
DEFAULT_SOURCE = "data/processed/images/test/OD"
DEFAULT_WEIGHTS = "models/checkpoints/black_ice/weights/best.pt"

def image_to_base64(img_bgr, max_width=800):
    """Resize image to reasonable size and encode as JPEG base64."""
    h, w = img_bgr.shape[:2]
    if w > max_width:
        scale = max_width / float(w)
        img_bgr = cv2.resize(img_bgr, (max_width, int(h * scale)))
    
    success, buffer = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not success:
        return None
    b64_str = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"

def main():
    parser = argparse.ArgumentParser(description="Stream Black Ice Model to Frontend")
    parser.add_argument("--backend", type=str, default=DEFAULT_BACKEND, help="Backend URL (Render or localhost)")
    parser.add_argument("--source", type=str, default=DEFAULT_SOURCE, help="Folder of test images or single image")
    parser.add_argument("--weights", type=str, default=DEFAULT_WEIGHTS, help="Path to trained model weights")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between frames (in auto mode)")
    parser.add_argument("--step", action="store_true", help="Press Enter to send next image step-by-step")
    parser.add_argument("--loop", action="store_true", default=True, help="Loop through images continuously")
    args = parser.parse_args()

    weights_path = Path(args.weights)
    if not weights_path.exists():
        print(f"❌ Error: Model weights not found at {weights_path}")
        sys.exit(1)

    print("=" * 70)
    print("🚀 BLACK ICE MODEL — LIVE FRONTEND FEEDER")
    print(f"📦 Model: {weights_path}")
    print(f"🌐 Backend Target: {args.backend}")
    print("=" * 70)

    # Test backend connection
    telemetry_url = f"{args.backend.rstrip('/')}/api/telemetry"
    try:
        print(f"📡 Testing connection to backend ({args.backend})...")
        r = requests.get(f"{args.backend.rstrip('/')}/api/health", timeout=6)
        print(f"✓ Backend online! Status: {r.status_code}")
    except Exception as e:
        print(f"⚠️ Warning: Could not reach backend: {e}")
        print("If Render free-tier was sleeping, it may take ~30 seconds to wake up.")

    print(f"🧠 Loading YOLOv8 model...")
    model = YOLO(str(weights_path))

    # Collect images
    source_path = Path(args.source)
    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    if source_path.is_file():
        image_files = [source_path]
    else:
        image_files = [p for p in source_path.rglob("*") if p.suffix.lower() in valid_exts]

    if not image_files:
        print(f"❌ No valid images found in {source_path}")
        sys.exit(1)

    print(f"📁 Found {len(image_files)} test images to feed into the frontend.")
    print("Open your frontend dashboard in browser (Workbench tab) to see the live feed!")
    print("-" * 70)

    img_idx = 0
    while True:
        img_path = image_files[img_idx % len(image_files)]
        img_idx += 1

        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            continue

        h_orig, w_orig = img_bgr.shape[:2]

        # Run inference
        results = model.predict(source=img_bgr, conf=args.conf, verbose=False)
        res = results[0]
        boxes = res.boxes

        num_detections = len(boxes)
        has_ice = num_detections > 0

        # Calculate bounding box in percentage [x, y, w, h] for frontend HUD
        bbox_pct = None
        best_conf = 0.0

        if has_ice:
            # Pick highest confidence box
            best_idx = int(boxes.conf.argmax())
            best_conf = float(boxes.conf[best_idx])
            xyxy = boxes.xyxy[best_idx].tolist()
            x1, y1, x2, y2 = xyxy

            # Convert to percentages for frontend viewport overlay
            x_pct = round((x1 / w_orig) * 100, 1)
            y_pct = round((y1 / h_orig) * 100, 1)
            w_pct = round(((x2 - x1) / w_orig) * 100, 1)
            h_pct = round(((y2 - y1) / h_orig) * 100, 1)
            bbox_pct = [x_pct, y_pct, w_pct, h_pct]

            road_status = "BLACK_ICE_HAZARD"
            verification_status = "CONFIRMED_HAZARD"
            surface_temp = -2.8
            lidar_dist = round(8.5 - (best_conf * 3.0), 1)
        else:
            road_status = "ROAD_CLEAR"
            verification_status = "NO_DETECTION"
            best_conf = 0.05
            surface_temp = 3.2
            lidar_dist = 24.0

        # Encode image to base64
        b64_image = image_to_base64(img_bgr)

        # Build payload matching frontend & backend schema
        # In frontend: ice_confidence is displayed 0-100%
        packet = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "device_id": "BlackIce-Model-Tester",
            "road_condition": road_status,
            "road_status": road_status,  # For direct frontend websocket compatibility
            "ice_confidence": round(best_conf * 100, 1),
            "patch_bbox": bbox_pct,
            "bbox": bbox_pct,            # For frontend HUD bbox overlay
            "surface_temp_c": surface_temp,
            "surface_temp": surface_temp,
            "estimated_distance_m": lidar_dist,
            "lidar_distance": lidar_dist,
            "uncertainty_status": verification_status,
            "verification_status": verification_status,
            "deicing_active": has_ice,
            "image_base64": b64_image
        }

        # Send to backend
        try:
            resp = requests.post(telemetry_url, json=packet, timeout=5)
            short_name = img_path.name[:25]
            if has_ice:
                print(f"[{img_idx:02d}] 🚨 SENT HAZARD: {short_name:<25} | Conf: {best_conf*100:.1f}% | Box: {bbox_pct}")
            else:
                print(f"[{img_idx:02d}] ⚪ SENT CLEAR : {short_name:<25} | No ice")
        except Exception as e:
            print(f"⚠️ Error sending packet: {e}")

        if args.step:
            input("👉 Press Enter to send next image...")
        else:
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
