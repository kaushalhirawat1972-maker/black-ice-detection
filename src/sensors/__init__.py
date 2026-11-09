"""
Sensors package: Module 1 multi-sensor acquisition.
"""

from src.sensors.mlx90640 import (
    BaseThermalSensor,
    MLX90640Sensor,
    MLX90640Simulator,
    get_thermal_sensor
)
from src.sensors.lidar2d import (
    LidarScan2D,
    Base2DLidar,
    RPLidar2D,
    Lidar2DSimulator,
    get_lidar_sensor
)
from src.sensors.acquisition import (
    SensorFrame,
    SensorAcquisitionHub
)

__all__ = [
    "BaseThermalSensor",
    "MLX90640Sensor",
    "MLX90640Simulator",
    "get_thermal_sensor",
    "LidarScan2D",
    "Base2DLidar",
    "RPLidar2D",
    "Lidar2DSimulator",
    "get_lidar_sensor",
    "SensorFrame",
    "SensorAcquisitionHub"
]
