"""
Module 1 (Component): 2D LiDAR Scanner Interface.

Provides hardware driver for real 2D LiDAR (e.g., RPLiDAR / generic serial 2D LiDAR)
and a planar scan simulator modeling vehicle mount geometry and road reflection.
"""

import time
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class LidarScan2D:
    """Represents a single 2D planar LiDAR scan."""
    timestamp: float
    angles_deg: np.ndarray      # Azimuth angles in degrees [-180, 180] or [0, 360], forward = 0°
    ranges_m: np.ndarray        # Distance in meters for each angle
    intensities: Optional[np.ndarray] = None  # Signal reflection intensity (0-255)


class Base2DLidar:
    """Base interface for 2D LiDAR scanners."""

    def read_scan(self) -> LidarScan2D:
        """
        Acquire one full planar scan.

        Returns:
            LidarScan2D: Scan data containing angles and ranges.
        """
        raise NotImplementedError


class RPLidar2D(Base2DLidar):
    """Hardware driver for RPLiDAR / generic serial 2D LiDAR scanners."""

    def __init__(
        self,
        port: str = "COM3",
        baudrate: int = 115200,
        timeout: float = 1.0
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.lidar = None
        self.is_connected = False
        self._init_sensor()

    def _init_sensor(self):
        try:
            from rplidar import RPLidar
            self.lidar = RPLidar(self.port, baudrate=self.baudrate, timeout=self.timeout)
            info = self.lidar.get_info()
            health = self.lidar.get_health()
            self.is_connected = True
            print(f"✓ 2D LiDAR connected on {self.port} (Health: {health})")
        except Exception as e:
            self.is_connected = False
            print(f"⚠ 2D LiDAR hardware initialization skipped: {e}")

    def read_scan(self) -> LidarScan2D:
        if not self.is_connected or self.lidar is None:
            raise RuntimeError(f"2D LiDAR on {self.port} is not connected")

        # Read one scan iterator
        for scan in self.lidar.iter_scans(max_buf_meas=500):
            # scan item: (quality, angle_deg, distance_mm)
            qualities = np.array([m[0] for m in scan], dtype=np.float32)
            raw_angles = np.array([m[1] for m in scan], dtype=np.float32)
            distances_m = np.array([m[2] / 1000.0 for m in scan], dtype=np.float32)

            # Normalize angles to [-180, 180] relative to forward (0°)
            angles = (raw_angles + 180.0) % 360.0 - 180.0
            sort_idx = np.argsort(angles)

            return LidarScan2D(
                timestamp=time.time(),
                angles_deg=angles[sort_idx],
                ranges_m=distances_m[sort_idx],
                intensities=qualities[sort_idx]
            )

        raise RuntimeError("No scan data received from 2D LiDAR")

    def disconnect(self):
        if self.lidar is not None:
            try:
                self.lidar.stop()
                self.lidar.stop_motor()
                self.lidar.disconnect()
            except Exception:
                pass
            self.is_connected = False


class Lidar2DSimulator(Base2DLidar):
    """
    Simulates a 2D vehicle-mounted LiDAR scanning the road plane ahead.
    Models mounting geometry (height, pitch angle), forward road reflection,
    and specular absorption/dropout caused by smooth black ice.
    """

    def __init__(
        self,
        mount_height_m: float = 0.65,
        mount_pitch_deg: float = 2.5,
        angular_resolution_deg: float = 0.5,
        forward_fov_deg: float = 120.0,
        noise_std_m: float = 0.03
    ):
        """
        Initialize LiDAR simulator.

        Args:
            mount_height_m: Height of LiDAR sensor above road in meters.
            mount_pitch_deg: Downward pitch tilt towards the road in degrees.
            angular_resolution_deg: Angle step between consecutive rays.
            forward_fov_deg: Forward scanning field of view in degrees.
            noise_std_m: Measurement noise standard deviation.
        """
        self.mount_height_m = mount_height_m
        self.mount_pitch_deg = mount_pitch_deg
        self.angular_resolution_deg = angular_resolution_deg
        self.forward_fov_deg = forward_fov_deg
        self.noise_std_m = noise_std_m

    def read_scan(
        self,
        target_azimuth_deg: Optional[float] = None,
        target_distance_m: Optional[float] = None,
        azimuth_span_deg: float = 8.0,
        specular_absorption: bool = False
    ) -> LidarScan2D:
        """
        Generate a 2D planar LiDAR scan.

        Args:
            target_azimuth_deg: Azimuth of target object/ice patch relative to heading.
            target_distance_m: Distance of target in meters.
            azimuth_span_deg: Angular width of target.
            specular_absorption: If True, simulates black ice specular reflection
                                 (laser rays bounce away, resulting in zero/inf dropouts).
        """
        half_fov = self.forward_fov_deg / 2.0
        angles = np.arange(-half_fov, half_fov + self.angular_resolution_deg, self.angular_resolution_deg)

        # Baseline: road surface intersection distance based on mounting height and tilt angle
        # At azimuth theta, distance to flat ground: d_ground = h / sin(pitch)
        pitch_rad = np.radians(max(self.mount_pitch_deg, 0.5))
        base_ground_distance = self.mount_height_m / np.sin(pitch_rad)
        # Cosine correction for lateral azimuth angle
        ranges = base_ground_distance / np.cos(np.radians(angles))
        ranges = np.clip(ranges, 0.5, 45.0)

        # Default diffuse reflectivity for dry/damp asphalt
        intensities = np.full_like(angles, 160.0)

        # Inject target or road anomaly
        if target_azimuth_deg is not None and target_distance_m is not None:
            target_mask = np.abs(angles - target_azimuth_deg) <= (azimuth_span_deg / 2.0)
            if specular_absorption:
                # Black ice specular behavior: IR light scatters away from sensor!
                # Result: no return (range=0.0 or inf, intensity near 0)
                ranges[target_mask] = 0.0
                intensities[target_mask] = 5.0
            else:
                # Surface hit return at target distance
                ranges[target_mask] = target_distance_m
                intensities[target_mask] = 120.0

        # Add Gaussian noise to valid range readings
        noise = np.random.normal(0, self.noise_std_m, size=ranges.shape)
        ranges = np.where(ranges > 0.1, np.maximum(ranges + noise, 0.1), 0.0)

        return LidarScan2D(
            timestamp=time.time(),
            angles_deg=angles.astype(np.float32),
            ranges_m=ranges.astype(np.float32),
            intensities=intensities.astype(np.float32)
        )


def get_lidar_sensor(
    use_simulator_if_unavailable: bool = True,
    **kwargs
) -> Base2DLidar:
    """Factory function to acquire either physical 2D LiDAR or simulator."""
    try:
        sensor = RPLidar2D(**kwargs)
        if sensor.is_connected:
            return sensor
    except Exception:
        pass

    if use_simulator_if_unavailable:
        return Lidar2DSimulator()
    raise RuntimeError("Physical 2D LiDAR not available and simulator disabled")
