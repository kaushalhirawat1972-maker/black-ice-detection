"""
Data schemas for Black Ice & Winter Hazard Detection Platform.
Used for serialization between Raspberry Pi, Cloud API, and Web Frontend.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class TelemetryPacket(BaseModel):
    """
    Core telemetry packet pushed by Raspberry Pi to Cloud API.
    """
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    device_id: str = Field(default="raspberry-pi-01", description="Vehicle / Node identifier")
    
    # 5 Core System Outputs
    road_condition: str = Field(..., description="BLACK_ICE_HAZARD, WET_ROAD_NO_ICE, ROAD_CLEAR, etc.")
    ice_confidence: float = Field(..., ge=0.0, le=100.0, description="Classification confidence (0.0 to 1.0 or 0 to 100)")
    patch_bbox: Optional[List[float]] = Field(None, description="[x, y, w, h] or [x1, y1, x2, y2] coordinates")
    estimated_distance_m: Optional[float] = Field(None, description="Associated LiDAR distance in meters")
    uncertainty_status: str = Field(default="CONFIRMED_HAZARD", description="Sensor fusion validation state")

    # Sensor Telemetry
    surface_temp_c: float = Field(..., description="Calibrated MLX90640 road temperature in Celsius")
    ambient_temp_c: Optional[float] = Field(None, description="Vehicle ambient temperature")
    lidar_specular_dropout: bool = Field(default=False, description="Whether zero-return specular drop occurred")
    
    # De-icing Actuator Telemetry
    deicing_active: bool = Field(default=False, description="Whether spray nozzle is firing")
    spray_lane: Optional[str] = Field("CENTER DUAL", description="LEFT LANE, CENTER DUAL, or RIGHT LANE")
    time_to_impact_sec: Optional[float] = Field(None, description="Calculated impact delay at current speed")

    # Image Payload (Base64 JPEG for browser HUD rendering)
    image_base64: Optional[str] = Field(None, description="Data URI: data:image/jpeg;base64,...")


class DeicingCommand(BaseModel):
    """
    Manual actuation command sent from Frontend to Edge Node.
    """
    device_id: str = "raspberry-pi-01"
    action: str = Field("pulse_spray", description="pulse_spray, stop, override")
    duration_ms: int = Field(500, description="Pulse duration in milliseconds")
    target_lane: str = Field("CENTER DUAL", description="Target spray lane")


class SystemHealth(BaseModel):
    status: str = "online"
    active_edge_nodes: int = 1
    model_version: str = "YOLOv8-BlackIce-v1.0"
    sensors_online: List[str] = ["RGB_CAMERA", "MLX90640_THERMAL", "LIDAR_2D"]
