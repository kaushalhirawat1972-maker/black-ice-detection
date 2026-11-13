"""
Raspberry Pi Edge Client for BLACK ICE DETECTION.

Integrates:
1. RGB Camera (USB or CSI)
2. MLX90640 Thermal Array (32x24 IR array over I2C)
3. 2D LiDAR (RPLiDAR / USB serial)
4. Vision Model (YOLOv8 trained weights)
5. Decision Fusion (Temperature Screening + LiDAR Specular Association)

Pushes live annotated frames and telemetry packets to the Cloud Backend (Render).
"""

import os
import sys
import time
import base64
import logging
from pathlib import Path
from datetime import datetime
import cv2
import requests

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline.black_ice_pipeline import BlackIcePipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BlackIceEdgeClient")

# ----------------- CONFIGURATION -----------------
CLOUD_API_URL = os.environ.get("CLOUD_API_URL", "http://localhost:8000/api/telemetry")
DEVICE_ID = os.environ.get("DEVICE_ID", "vehicle-pi4-front")
MODEL_PATH = os.environ.get("MODEL_PATH", "models/checkpoints/black_ice/weights/best.pt")
CONFIG_PATH = os.environ.get("CONFIG_PATH", "configs/sensor_pipeline.yaml")
FORCE_SIMULATOR = os.environ.get("FORCE_SIMULATOR", "false").lower() == "true"

# ----------------- HARDWARE ALERT GPIO (Optional) -----------------
LED_PIN = 17
gpio_handle = None
try:
    import lgpio
    gpio_handle = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(gpio_handle, LED_PIN, 0)
    logger.info("✓ Hardware GPIO alert LED claimed on Pin 17")
except Exception as e:
    logger.info(f"GPIO alert disabled: {e}")


def trigger_led(is_hazard: bool):
    """Trigger physical alert LED on Raspberry Pi."""
    if gpio_handle is not None:
        try:
            import lgpio
            lgpio.gpio_write(gpio_handle, LED_PIN, 1 if is_hazard else 0)
        except Exception:
            pass


def encode_frame_to_base64(frame_bgr, quality=65) -> str:
    """Encode OpenCV BGR image to lightweight JPEG Data URI for dashboard rendering."""
    _, buffer = cv2.imencode('.jpg', frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64_str}"


def run_edge_loop():
    logger.info("=" * 65)
    logger.info("STARTING BLACK ICE MULTI-SENSOR EDGE CLIENT")
    logger.info(f"Target Cloud API : {CLOUD_API_URL}")
    logger.info(f"YOLO Model Path  : {MODEL_PATH}")
    logger.info(f"Config File      : {CONFIG_PATH}")
    logger.info("Sensors Active   : RGB Camera + MLX90640 Thermal + 2D LiDAR")
    logger.info("=" * 65)

    # Automatically select CPU for Pi (or CUDA if available)
    device = "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda:0"
    except Exception:
        pass

    # Initialize complete multi-sensor pipeline
    pipeline = BlackIcePipeline(
        config_path=CONFIG_PATH,
        model_path=MODEL_PATH,
        device=device,
        force_simulator=FORCE_SIMULATOR
    )

    # Start sensor acquisition hub (Camera, Thermal, LiDAR)
    pipeline.sensor_hub.start()
    logger.info("✓ Multi-sensor acquisition active. Streaming to cloud...")

    try:
        while True:
            # 1. Acquire synchronized multi-sensor frame
            frame = pipeline.sensor_hub.acquire_frame()
            if frame is None or frame.rgb_frame is None:
                time.sleep(0.02)
                continue

            # 2. Process through Vision (YOLO) + Temp Screening (Thermal) + LiDAR Association
            output = pipeline.process_sensor_frame(frame)
            is_hazard = (output.road_condition == "BLACK_ICE_HAZARD")

            # 3. Hardware LED alert
            trigger_led(is_hazard)

            # 4. Extract telemetry values
            surface_temp = output.details.get("temperature_screening", {}).get("mean_surface_temp_c", 0.0)
            lidar_dist = output.estimated_distance
            specular_drop = output.details.get("lidar_association", {}).get("specular_dropout", False)

            # 5. Annotate camera frame with bounding boxes and HUD
            annotated_frame = frame.rgb_frame.copy()
            if output.patch_bbox is not None:
                x1, y1, x2, y2 = output.patch_bbox
                box_color = (0, 0, 255) if is_hazard else (0, 165, 255)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, 3)
                label = f"{output.road_condition} ({output.ice_confidence:.1%})"
                if lidar_dist is not None:
                    label += f" {lidar_dist:.1f}m"
                cv2.putText(
                    annotated_frame, label, (x1, max(y1 - 10, 25)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, box_color, 2
                )

            # 6. Package TelemetryPacket matching backend schemas
            b64_image = encode_frame_to_base64(annotated_frame, quality=65)
            packet = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "device_id": DEVICE_ID,
                "road_condition": output.road_condition,
                "ice_confidence": round(float(output.ice_confidence), 3),
                "patch_bbox": list(output.patch_bbox) if output.patch_bbox is not None else None,
                "estimated_distance_m": round(float(lidar_dist), 2) if lidar_dist is not None else None,
                "uncertainty_status": output.uncertainty_status,
                "surface_temp_c": round(float(surface_temp), 1),
                "ambient_temp_c": round(float(surface_temp) + 2.5, 1),
                "lidar_specular_dropout": specular_drop,
                "deicing_active": is_hazard,
                "spray_lane": "CENTER DUAL",
                "time_to_impact_sec": round(float(lidar_dist) / 16.6, 2) if lidar_dist else None,
                "image_base64": b64_image
            }

            # 7. Push telemetry packet to Cloud API (Render)
            try:
                res = requests.post(CLOUD_API_URL, json=packet, timeout=1.5)
                if res.status_code == 200:
                    status_icon = "🚨" if is_hazard else "🟢"
                    dist_txt = f"{lidar_dist:.1f}m" if lidar_dist else "N/A"
                    logger.info(
                        f"{status_icon} {output.road_condition} "
                        f"(Conf: {output.ice_confidence:.1%}, Temp: {surface_temp:.1f}°C, Dist: {dist_txt}) -> Cloud OK"
                    )
            except requests.exceptions.RequestException as req_err:
                logger.warning(f"Cloud API unreachable: {req_err}")

            # Stream at ~3-5 FPS (optimal for network bandwidth & Pi CPU)
            time.sleep(0.2)

    except KeyboardInterrupt:
        logger.info("Stopping edge loop...")
    finally:
        pipeline.sensor_hub.release()
        if gpio_handle is not None:
            try:
                import lgpio
                lgpio.gpio_write(gpio_handle, LED_PIN, 0)
                lgpio.gpiochip_close(gpio_handle)
            except Exception:
                pass
        logger.info("Edge client cleanly shut down.")


if __name__ == "__main__":
    run_edge_loop()
