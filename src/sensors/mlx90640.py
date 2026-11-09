"""
Module 1 (Component): MLX90640 32x24 Thermal Array Sensor Interface.

Provides hardware driver for real I2C MLX90640 sensors and a physics-based
simulator fallback for testing, evaluation, and environments without physical I2C.
"""

import time
import numpy as np
from typing import Optional, Tuple


class BaseThermalSensor:
    """Base interface for thermal array sensors."""

    def read_temperature_matrix(self) -> np.ndarray:
        """
        Read thermal frame as 24x32 temperature array in degrees Celsius.

        Returns:
            np.ndarray: Shape (24, 32) of temperatures in °C.
        """
        raise NotImplementedError


class MLX90640Sensor(BaseThermalSensor):
    """Hardware driver for MLX90640 32x24 IR array sensor."""

    def __init__(
        self,
        i2c_bus: int = 1,
        i2c_address: int = 0x33,
        refresh_rate_hz: int = 4
    ):
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self.refresh_rate_hz = refresh_rate_hz
        self.sensor = None
        self.is_connected = False
        self._init_sensor()

    def _init_sensor(self):
        try:
            import board
            import busio
            import adafruit_mlx90640

            i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
            self.sensor = adafruit_mlx90640.MLX90640(i2c)
            # Set refresh rate
            rate_map = {
                1: adafruit_mlx90640.RefreshRate.REFRESH_1_HZ,
                2: adafruit_mlx90640.RefreshRate.REFRESH_2_HZ,
                4: adafruit_mlx90640.RefreshRate.REFRESH_4_HZ,
                8: adafruit_mlx90640.RefreshRate.REFRESH_8_HZ,
                16: adafruit_mlx90640.RefreshRate.REFRESH_16_HZ,
            }
            self.sensor.refresh_rate = rate_map.get(
                self.refresh_rate_hz,
                adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
            )
            self.is_connected = True
            print(f"✓ MLX90640 initialized on I2C address 0x{self.i2c_address:02x}")
        except Exception as e:
            self.is_connected = False
            print(f"⚠ MLX90640 hardware initialization skipped: {e}")

    def read_temperature_matrix(self) -> np.ndarray:
        if not self.is_connected or self.sensor is None:
            raise RuntimeError("MLX90640 hardware is not connected")

        raw_frame = [0.0] * 768
        self.sensor.getFrame(raw_frame)
        # MLX90640 is 24 rows by 32 columns
        matrix = np.array(raw_frame, dtype=np.float32).reshape((24, 32))
        return matrix


class MLX90640Simulator(BaseThermalSensor):
    """
    Thermal array simulator modeling vehicle-mounted thermal imaging of road surface.
    Simulates ambient temperature, road thermal gradient, and sub-freezing cold patches.
    """

    def __init__(
        self,
        base_temp_c: float = -1.5,
        cold_spot_delta_c: float = -3.5,
        noise_std_c: float = 0.35
    ):
        """
        Initialize thermal simulator.

        Args:
            base_temp_c: Baseline ambient/road surface temperature in °C.
            cold_spot_delta_c: Temperature drop in icing spots in °C.
            noise_std_c: Sensor noise standard deviation.
        """
        self.base_temp_c = base_temp_c
        self.cold_spot_delta_c = cold_spot_delta_c
        self.noise_std_c = noise_std_c

    def read_temperature_matrix(
        self,
        ice_patch_center: Optional[Tuple[float, float]] = None,
        patch_radius: float = 4.0
    ) -> np.ndarray:
        """
        Generate a 24x32 thermal array.

        Args:
            ice_patch_center: (row, col) in [0..23, 0..31] where cold ice is localized.
                              If None, a default road temperature gradient is generated.
            patch_radius: Radius of the cold anomaly in grid cells.

        Returns:
            np.ndarray: 24x32 temperature array in °C.
        """
        # Vertical gradient: sky/horizon (top rows) is colder, ground is warmer,
        # but road surface near ground can drop below freezing in winter.
        rows, cols = 24, 32
        row_indices, col_indices = np.indices((rows, cols))

        # Baseline thermal distribution across the scene
        # Top rows (sky/far background): base_temp - 2°C
        # Bottom rows (road surface near vehicle): base_temp + 0.5°C
        grad = (row_indices / float(rows - 1)) * 1.5 - 0.75
        matrix = self.base_temp_c + grad

        # Add cold patch anomaly if specified
        if ice_patch_center is not None:
            pr, pc = ice_patch_center
            dist_sq = (row_indices - pr) ** 2 + (col_indices - pc) ** 2
            patch_mask = np.exp(-dist_sq / (2.0 * (patch_radius ** 2)))
            matrix += self.cold_spot_delta_c * patch_mask

        # Add realistic sensor noise
        noise = np.random.normal(0, self.noise_std_c, size=(rows, cols))
        return (matrix + noise).astype(np.float32)


def get_thermal_sensor(
    use_simulator_if_unavailable: bool = True,
    **kwargs
) -> BaseThermalSensor:
    """Factory function to acquire either physical MLX90640 or simulator."""
    try:
        sensor = MLX90640Sensor(**kwargs)
        if sensor.is_connected:
            return sensor
    except Exception:
        pass

    if use_simulator_if_unavailable:
        return MLX90640Simulator()
    raise RuntimeError("Physical MLX90640 sensor not available and simulator disabled")
