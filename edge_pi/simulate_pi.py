"""
Raspberry Pi Edge Simulator for BLACK ICE DETECTION.
Simulates a vehicle-mounted Raspberry Pi 4 by reading test road images,
running the multi-sensor pipeline (YOLOv8 + Thermal + LiDAR),
and streaming real-time telemetry packets to the Cloud Communication API.
"""

import os
import sys
import time
import base64
import random
import logging
from pathlib import Path
from datetime import datetime
import cv2
import requests

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline.black_ice_pipeline import BlackIcePipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EdgeSimulator")

# Cloud API Endpoint — set CLOUD_API_URL env var or update this default after Render deployment
API_URL = os.environ.get("CLOUD_API_URL", "http://localhost:8000/api/telemetry")
DEVICE_ID = "vehicle-pi4-front"


def encode_image_base64(image_bgr, quality=75) -> str:
    """Encode OpenCV BGR image to lightweight Base64 JPEG Data URI."""
    _, buffer = cv2.imencode('.jpg', image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64_str}"


def main():
    logger.info("Initializing BLACK ICE DETECTION Edge Simulator...")

    # Load multi-sensor pipeline
    model_path = "models/checkpoints/black_ice/weights/best.pt"
    config_path = "configs/sensor_pipeline.yaml"
    
    # Auto device
    device = "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda:0"
    except Exception:
        pass

    logger.info(f"Loading pipeline with model: {model_path} on {device}")
    pipeline = BlackIcePipeline(
        config_path=config_path,
        model_path=model_path,
        device=device,
        force_simulator=True
    )

    # Gather test images
    test_dirs = [
        Path("data/processed/images/test/OD"),
        Path("data/dry/smooth"),
        Path("data/dry/slight"),
        Path("data/dry/severe"),
        Path("data/raw/white/train")
    ]
    
    image_paths = []
    for d in test_dirs:
        if d.exists():
            image_paths.extend(list(d.glob("*.jpg")) + list(d.glob("*.png")))

    if not image_paths:
        logger.error("No test images found in data directory.")
        return

    logger.info(f"Loaded {len(image_paths)} road test images for simulation cycle.")
    logger.info(f"Streaming packets to: {API_URL}")
    logger.info("Press Ctrl+C to stop simulation.")

    frame_idx = 0
    try:
        while True:
            # Cycle through images
            img_path = image_paths[frame_idx % len(image_paths)]
            frame_idx += 1

            frame = cv2.imread(str(img_path))
            if frame is None:
                continue

            # Simulate variable surface temperatures and LiDAR distance
            is_ice_category = "dry" not in str(img_path).lower()
            sim_temp = random.uniform(-6.0, 0.5) if is_ice_category else random.uniform(4.0, 18.0)
            sim_dist = random.uniform(8.0, 22.0)

            # Process through pipeline
            output = pipeline.process_image(
                image=frame,
                road_surface_temp_c=sim_temp,
                lidar_distance_m=sim_dist
            )

            # Annotate frame
            annotated = frame.copy()
            if output.patch_bbox is not None:
                x1, y1, x2, y2 = output.patch_bbox
                color = (0, 0, 235) if output.road_condition == "BLACK_ICE_HAZARD" else (0, 165, 255)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
                label = f"{output.road_condition} {output.ice_confidence:.1%}"
                cv2.putText(annotated, label, (x1, max(y1 - 10, 25)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

            deicing_active = (output.road_condition == "BLACK_ICE_HAZARD")
            b64_image = encode_image_base64(annotated, quality=70)

            # Construct TelemetryPacket
            packet = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "device_id": DEVICE_ID,
                "road_condition": output.road_condition,
                "ice_confidence": round(float(output.ice_confidence), 3),
                "patch_bbox": output.patch_bbox,
                "estimated_distance_m": round(float(output.estimated_distance), 2) if output.estimated_distance else None,
                "uncertainty_status": output.uncertainty_status,
                "surface_temp_c": round(sim_temp, 1),
                "ambient_temp_c": round(sim_temp + 2.5, 1),
                "lidar_specular_dropout": (output.road_condition == "BLACK_ICE_HAZARD"),
                "deicing_active": deicing_active,
                "spray_lane": "CENTER DUAL",
                "time_to_impact_sec": round(sim_dist / 16.6, 2) if sim_dist else None,
                "image_base64": b64_image
            }

            # Send to backend
            try:
                res = requests.post(API_URL, json=packet, timeout=1.0)
                if res.status_code == 200:
                    status_emoji = "🚨" if deicing_active else "✅"
                    logger.info(f"{status_emoji} [{frame_idx}] {output.road_condition} "
                                f"(Conf: {output.ice_confidence:.1%}, Temp: {sim_temp:.1f}C, Dist: {sim_dist:.1f}m) -> Cloud API OK")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Backend offline at {API_URL}. Run: uvicorn backend.main:app --port 8000")
            except Exception as e:
                logger.warning(f"Push failed: {e}")

            time.sleep(1.0)  # Push at 1 frame per second for clear testing
    except KeyboardInterrupt:
        logger.info("Simulation halted.")


if __name__ == "__main__":
    main()
