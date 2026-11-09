"""
Module 1 — Sensor Acquisition Hub.

Coordinates synchronized acquisition from:
- RGB Camera (visual frame)
- MLX90640 Thermal Array (32x24 surface infrared matrix)
- 2D LiDAR (planar distance scan)
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Union
import numpy as np
import cv2

from src.sensors.mlx90640 import BaseThermalSensor, get_thermal_sensor
from src.sensors.lidar2d import Base2DLidar, LidarScan2D, get_lidar_sensor
from src.utils.camera import Camera


@dataclass
class SensorFrame:
    """Synchronized multi-sensor data container."""
    timestamp: float
    rgb_frame: np.ndarray             # (H, W, 3) BGR image
    thermal_matrix: np.ndarray        # (24, 32) surface temperature matrix in °C
    lidar_scan: LidarScan2D           # 2D planar LiDAR scan
    sensor_health: Dict[str, bool]    # Health status of each sensor


class SensorAcquisitionHub:
    """
    Module 1: Manages real-time multi-sensor acquisition.
    Acquires synchronized RGB frames, MLX90640 thermal matrices, and 2D LiDAR scans.
    Supports real hardware with seamless simulator fallback.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        camera_source: Union[int, str] = 0,
        enable_thermal: bool = True,
        enable_lidar: bool = True,
        force_simulator: bool = False
    ):
        """
        Initialize Sensor Acquisition Hub.

        Args:
            config: Sensor configuration dictionary.
            camera_source: Camera index or video path.
            enable_thermal: Whether to acquire thermal data.
            enable_lidar: Whether to acquire LiDAR scans.
            force_simulator: Force simulator mode even if hardware is available.
        """
        self.config = config or {}
        sensors_cfg = self.config.get("sensors", {})

        # 1. Camera Initialization
        cam_cfg = sensors_cfg.get("camera", {})
        src = cam_cfg.get("source", camera_source)
        width = cam_cfg.get("width", 640)
        height = cam_cfg.get("height", 480)
        fps = cam_cfg.get("fps", 30)

        self.camera = Camera(source=src, width=width, height=height, fps=fps)
        self.camera_ok = False

        # 2. MLX90640 Thermal Array Initialization
        self.enable_thermal = enable_thermal
        thermal_cfg = sensors_cfg.get("mlx90640", {})
        if force_simulator:
            from src.sensors.mlx90640 import MLX90640Simulator
            self.thermal_sensor = MLX90640Simulator()
            self.thermal_ok = True
        elif enable_thermal:
            try:
                self.thermal_sensor = get_thermal_sensor(
                    use_simulator_if_unavailable=thermal_cfg.get("use_simulator_if_unavailable", True),
                    i2c_bus=thermal_cfg.get("i2c_bus", 1),
                    i2c_address=thermal_cfg.get("i2c_address", 0x33),
                    refresh_rate_hz=thermal_cfg.get("refresh_rate_hz", 4)
                )
                self.thermal_ok = True
            except Exception as e:
                print(f"⚠ Thermal acquisition warning: {e}")
                self.thermal_sensor = None
                self.thermal_ok = False
        else:
            self.thermal_sensor = None
            self.thermal_ok = False

        # 3. 2D LiDAR Initialization
        self.enable_lidar = enable_lidar
        lidar_cfg = sensors_cfg.get("lidar_2d", {})
        if force_simulator:
            from src.sensors.lidar2d import Lidar2DSimulator
            self.lidar_sensor = Lidar2DSimulator(
                mount_height_m=lidar_cfg.get("mount_height_m", 0.65),
                mount_pitch_deg=lidar_cfg.get("mount_pitch_deg", 2.5),
                forward_fov_deg=lidar_cfg.get("forward_fov_deg", 120.0)
            )
            self.lidar_ok = True
        elif enable_lidar:
            try:
                self.lidar_sensor = get_lidar_sensor(
                    use_simulator_if_unavailable=lidar_cfg.get("use_simulator_if_unavailable", True),
                    port=lidar_cfg.get("port", "COM3"),
                    baudrate=lidar_cfg.get("baudrate", 115200)
                )
                self.lidar_ok = True
            except Exception as e:
                print(f"⚠ 2D LiDAR acquisition warning: {e}")
                self.lidar_sensor = None
                self.lidar_ok = False
        else:
            self.lidar_sensor = None
            self.lidar_ok = False

    def start(self) -> bool:
        """Start acquisition devices."""
        self.camera_ok = self.camera.open()
        return self.camera_ok

    def acquire_frame(self) -> Optional[SensorFrame]:
        """
        Synchronously acquire one frame across all 3 modalities.

        Returns:
            SensorFrame containing RGB image, thermal matrix, and LiDAR scan.
        """
        ts = time.time()

        # Capture RGB Frame
        ret, rgb_frame = self.camera.read()
        if not ret or rgb_frame is None:
            return None

        # Capture MLX90640 Thermal Matrix
        if self.thermal_sensor is not None:
            try:
                thermal_matrix = self.thermal_sensor.read_temperature_matrix()
                self.thermal_ok = True
            except Exception as e:
                thermal_matrix = np.full((24, 32), 20.0, dtype=np.float32)
                self.thermal_ok = False
        else:
            thermal_matrix = np.full((24, 32), 20.0, dtype=np.float32)

        # Capture 2D LiDAR Scan
        if self.lidar_sensor is not None:
            try:
                lidar_scan = self.lidar_sensor.read_scan()
                self.lidar_ok = True
            except Exception as e:
                lidar_scan = LidarScan2D(
                    timestamp=ts,
                    angles_deg=np.array([], dtype=np.float32),
                    ranges_m=np.array([], dtype=np.float32)
                )
                self.lidar_ok = False
        else:
            lidar_scan = LidarScan2D(
                timestamp=ts,
                angles_deg=np.array([], dtype=np.float32),
                ranges_m=np.array([], dtype=np.float32)
            )

        return SensorFrame(
            timestamp=ts,
            rgb_frame=rgb_frame,
            thermal_matrix=thermal_matrix,
            lidar_scan=lidar_scan,
            sensor_health={
                "camera": self.camera_ok,
                "thermal_mlx90640": self.thermal_ok,
                "lidar_2d": self.lidar_ok
            }
        )

    def create_frame_from_image(
        self,
        image: Union[str, Path, np.ndarray],
        thermal_matrix: Optional[np.ndarray] = None,
        lidar_scan: Optional[LidarScan2D] = None,
        road_surface_temp_c: Optional[float] = None
    ) -> SensorFrame:
        """
        Create a synchronized SensorFrame from an input image.
        Synthesizes matching thermal and LiDAR data if not provided.
        """
        if isinstance(image, (str, Path)):
            img = cv2.imread(str(image))
            if img is None:
                raise FileNotFoundError(f"Failed to read image at {image}")
        else:
            img = image

        ts = time.time()

        # Build or use thermal matrix
        if thermal_matrix is not None:
            t_mat = thermal_matrix
        elif road_surface_temp_c is not None:
            t_mat = np.full((24, 32), road_surface_temp_c, dtype=np.float32)
        elif self.thermal_sensor is not None:
            t_mat = self.thermal_sensor.read_temperature_matrix()
        else:
            from src.sensors.mlx90640 import MLX90640Simulator
            t_mat = MLX90640Simulator().read_temperature_matrix()

        # Build or use LiDAR scan
        if lidar_scan is not None:
            l_scan = lidar_scan
        elif self.lidar_sensor is not None:
            l_scan = self.lidar_sensor.read_scan()
        else:
            from src.sensors.lidar2d import Lidar2DSimulator
            l_scan = Lidar2DSimulator().read_scan()

        return SensorFrame(
            timestamp=ts,
            rgb_frame=img,
            thermal_matrix=t_mat,
            lidar_scan=l_scan,
            sensor_health={"camera": True, "thermal_mlx90640": True, "lidar_2d": True}
        )

    def release(self):
        """Release all hardware resources."""
        if self.camera:
            self.camera.release()
        if hasattr(self.lidar_sensor, "disconnect"):
            try:
                self.lidar_sensor.disconnect()
            except Exception:
                pass
