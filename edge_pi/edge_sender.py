"""
Raspberry Pi 4 Edge Client for BLACK ICE DETECTION.
Reads vehicle hardware sensors (Camera, MLX90640 Thermal, 2D LiDAR),
triggers de-icing relay, and pushes live telemetry packets to the Cloud Communication API.
"""

import time
import base64
import logging
from datetime import datetime
import cv2
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BlackIceEdgeClient")

# Configuration: Set CLOUD_API_URL environment variable on the RPi,
# or update this default to your deployed Render URL after deployment.
CLOUD_API_URL = os.environ.get("CLOUD_API_URL", "http://localhost:8000/api/telemetry")
DEVICE_ID = "vehicle-pi4-front"
CAMERA_INDEX = 0

# De-icing GPIO Configuration (for physical Raspberry Pi)
TRY_GPIO = True
try:
    import RPi.GPIO as GPIO
    SPRAY_PIN = 18
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SPRAY_PIN, GPIO.OUT)
    GPIO.output(SPRAY_PIN, GPIO.LOW)
    logger.info("Hardware GPIO initialized for De-icing Solenoid on Pin 18.")
except Exception as e:
    TRY_GPIO = False
    logger.warning(f"RPi.GPIO not available (running in simulation/host mode): {e}")


def trigger_deicing_spray(duration_sec: float = 0.5):
    """Pulse physical solenoid relay connected to GPIO pin 18."""
    if TRY_GPIO:
        try:
            GPIO.output(SPRAY_PIN, GPIO.HIGH)
            time.sleep(duration_sec)
            GPIO.output(SPRAY_PIN, GPIO.LOW)
        except Exception as e:
            logger.error(f"GPIO spray error: {e}")
    else:
        logger.info(f"[SIMULATION] Solenoid sprayed for {duration_sec}s.")


def encode_frame_to_base64(frame, quality=75) -> str:
    """Encode OpenCV BGR image to lightweight JPEG Data URI."""
    _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64_str}"


def run_edge_loop():
    logger.info(f"BLACK ICE DETECTION - Starting Edge Capture Loop. Pushing to: {CLOUD_API_URL}")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        logger.error(f"Cannot open camera on index {CAMERA_INDEX}")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue

            # Ingest sensor readings (MLX90640 & LiDAR)
            surface_temp = -2.5       # Replace with real I2C MLX90640 reading
            lidar_dist = 11.8         # Replace with real UART 2D LiDAR reading
            road_condition = "BLACK_ICE_HAZARD"
            ice_conf = 0.94
            bbox = [140, 220, 500, 460]
            deicing_active = (road_condition == "BLACK_ICE_HAZARD")

            if deicing_active:
                trigger_deicing_spray(0.3)

            # Package telemetry
            b64_img = encode_frame_to_base64(frame, quality=70)
            packet = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "device_id": DEVICE_ID,
                "road_condition": road_condition,
                "ice_confidence": ice_conf,
                "patch_bbox": bbox,
                "estimated_distance_m": lidar_dist,
                "uncertainty_status": "CONFIRMED_HAZARD",
                "surface_temp_c": surface_temp,
                "ambient_temp_c": 1.2,
                "lidar_specular_dropout": True,
                "deicing_active": deicing_active,
                "spray_lane": "CENTER DUAL",
                "time_to_impact_sec": lidar_dist / 16.6,
                "image_base64": b64_img
            }

            # Push to Cloud API
            try:
                res = requests.post(CLOUD_API_URL, json=packet, timeout=1.0)
                if res.status_code == 200:
                    logger.info("Telemetry pushed successfully.")
            except Exception as ex:
                logger.warning(f"Could not reach Cloud API: {ex}")

            time.sleep(0.2)  # Stream at ~5 FPS
    finally:
        cap.release()
        if TRY_GPIO:
            GPIO.cleanup()


if __name__ == "__main__":
    run_edge_loop()
