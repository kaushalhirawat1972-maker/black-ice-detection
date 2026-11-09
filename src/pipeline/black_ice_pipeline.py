"""
Integrated Black Ice Detection Pipeline.

Coordinates:
- Module 1: Sensor Acquisition (RGB Camera + MLX90640 Thermal Array + 2D LiDAR)
- Module 2: Temperature Screening (Calibrated road temperature vs icing-risk range)
- Vision Model: Single image input -> Is black ice or not, confidence, patch bbox
- Module 5: LiDAR Association (2D ray filtering, center distance estimation, specular detection)

Produces Final Output:
Road condition · Ice confidence · Patch bounding box · Estimated distance · Uncertainty status
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Union, List
import numpy as np
import yaml

from src.sensors.acquisition import SensorAcquisitionHub, SensorFrame
from src.screening.temperature import TemperatureScreener, TemperatureScreeningResult
from src.lidar.association import LidarAssociator, LidarAssociationResult
from src.inference.detector import BlackIceDetector


@dataclass
class PipelineOutput:
    """
    Final Output standard format:
    Road condition · Ice confidence · Patch bounding box · Estimated distance · Uncertainty status
    """
    road_condition: str                                # Road condition (e.g., BLACK_ICE_HAZARD, WET_ROAD_NO_ICE, CLEAR)
    ice_confidence: float                              # Ice confidence score [0.0 - 1.0]
    patch_bbox: Optional[Tuple[int, int, int, int]]    # Patch bounding box [x1, y1, x2, y2] in pixels
    estimated_distance: Optional[float]                # Estimated center distance in meters
    uncertainty_status: str                            # Uncertainty status descriptor

    # Detailed subsystem telemetry
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert output to standard dictionary."""
        return {
            "road_condition": self.road_condition,
            "ice_confidence": self.ice_confidence,
            "patch_bbox": self.patch_bbox,
            "estimated_distance": self.estimated_distance,
            "uncertainty_status": self.uncertainty_status,
            "details": self.details
        }

    def summary(self) -> str:
        """Formatted human-readable single-line summary."""
        dist_str = f"{self.estimated_distance:.2f} m" if self.estimated_distance is not None else "N/A"
        bbox_str = str(self.patch_bbox) if self.patch_bbox is not None else "None"
        return (
            f"[{self.road_condition}] "
            f"Confidence: {self.ice_confidence:.1%} | "
            f"BBox: {bbox_str} | "
            f"Distance: {dist_str} | "
            f"Status: {self.uncertainty_status}"
        )


class BlackIcePipeline:
    """
    End-to-End Multi-Sensor Black Ice Detection Pipeline.
    """

    def __init__(
        self,
        config_path: Union[str, Path] = "configs/sensor_pipeline.yaml",
        model_path: Optional[str] = None,
        device: str = "cuda:1",
        force_simulator: bool = False
    ):
        """
        Initialize the complete pipeline.

        Args:
            config_path: Path to pipeline YAML configuration file.
            model_path: Optional override for YOLO weights path.
            device: Computing device ("cuda:1", "cuda:0", "cpu").
            force_simulator: Force sensor simulation mode.
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # 1. Vision Model
        vis_cfg = self.config.get("vision_model", {})
        m_path = model_path or vis_cfg.get("model_path", "models/checkpoints/black_ice/weights/best.pt")
        dev = device or vis_cfg.get("device", "cuda:1")
        conf_thr = vis_cfg.get("conf_threshold", 0.35)
        iou_thr = vis_cfg.get("iou_threshold", 0.45)

        print(f"Initializing Vision Model from {m_path}...")
        self.detector = BlackIceDetector(
            model_path=m_path,
            conf_threshold=conf_thr,
            iou_threshold=iou_thr,
            device=dev
        )

        # 2. Module 1: Sensor Acquisition Hub
        print("Initializing Module 1: Sensor Acquisition Hub...")
        self.sensor_hub = SensorAcquisitionHub(
            config=self.config,
            force_simulator=force_simulator
        )

        # 3. Module 2: Temperature Screener
        print("Initializing Module 2: Temperature Screening...")
        self.temperature_screener = TemperatureScreener(config=self.config)

        # 4. Module 5: LiDAR Associator
        print("Initializing Module 5: LiDAR Association...")
        self.lidar_associator = LidarAssociator(config=self.config)

        # Fusion thresholds
        self.fusion_cfg = self.config.get("fusion", {})
        self.wet_road_temp_cutoff = self.fusion_cfg.get("wet_road_temp_cutoff_c", 3.0)
        self.high_conf_thresh = self.fusion_cfg.get("high_confidence_threshold", 0.75)
        self.med_conf_thresh = self.fusion_cfg.get("medium_confidence_threshold", 0.40)

        print("✓ Black Ice Detection Pipeline fully initialized.")

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration."""
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def process_sensor_frame(self, frame: SensorFrame) -> PipelineOutput:
        """
        Process a multi-sensor frame through the full pipeline.

        Args:
            frame: SensorFrame containing RGB image, thermal matrix, and LiDAR scan.

        Returns:
            PipelineOutput with the 5 required fields and details.
        """
        img = frame.rgb_frame
        h, w = img.shape[:2]

        # Step 1: Vision Model Inference (Input image -> Is black ice or not)
        vision_res = self.detector.predict_image(img)
        is_vision_ice = vision_res["is_black_ice"]
        ice_conf = float(vision_res["ice_confidence"])
        patch_bbox = vision_res["patch_bbox"]

        # Step 2: Module 2 — Temperature Screening
        temp_res = self.temperature_screener.screen_temperature(
            thermal_matrix=frame.thermal_matrix,
            patch_bbox=patch_bbox,
            image_shape=(h, w)
        )

        # Step 3: Module 5 — LiDAR Association
        lidar_res = self.lidar_associator.associate(
            patch_bbox=patch_bbox,
            image_shape=(h, w),
            lidar_scan=frame.lidar_scan
        )

        # Step 4: Decision Fusion & Uncertainty Assessment
        road_condition, uncertainty_status = self._fuse_modalities(
            is_vision_ice=is_vision_ice,
            ice_conf=ice_conf,
            temp_res=temp_res,
            lidar_res=lidar_res,
            sensor_health=frame.sensor_health
        )

        details = {
            "vision": {
                "label": vision_res["label"],
                "num_patches": vision_res["num_patches"],
                "detections": vision_res["detections"]
            },
            "temperature_screening": {
                "mean_surface_temp_c": temp_res.mean_surface_temp_c,
                "min_surface_temp_c": temp_res.min_surface_temp_c,
                "patch_temp_c": temp_res.patch_temp_c,
                "is_icing_risk": temp_res.is_icing_risk,
                "screening_status": temp_res.screening_status,
                "thermal_risk_score": temp_res.thermal_risk_score,
                "icing_risk_range": temp_res.icing_risk_range
            },
            "lidar_association": {
                "valid_rays": lidar_res.valid_ray_count,
                "total_rays": lidar_res.total_rays_in_sector,
                "center_azimuth_deg": lidar_res.center_azimuth_deg,
                "geometry_permitted": lidar_res.geometry_permitted,
                "specular_drop_detected": lidar_res.specular_drop_detected,
                "association_status": lidar_res.association_status
            },
            "sensor_health": frame.sensor_health,
            "timestamp": frame.timestamp
        }

        return PipelineOutput(
            road_condition=road_condition,
            ice_confidence=round(ice_conf, 3),
            patch_bbox=patch_bbox,
            estimated_distance=lidar_res.estimated_distance_m,
            uncertainty_status=uncertainty_status,
            details=details
        )

    def process_image(
        self,
        image: Union[str, Path, np.ndarray],
        road_surface_temp_c: Optional[float] = None,
        lidar_distance_m: Optional[float] = None,
        thermal_matrix: Optional[np.ndarray] = None
    ) -> PipelineOutput:
        """
        Convenience method: Input an image (and optional sensor data) and run full pipeline.

        Args:
            image: Image file path or numpy array.
            road_surface_temp_c: Optional road temperature override in °C.
            lidar_distance_m: Optional LiDAR distance override in meters.
            thermal_matrix: Optional custom 24x32 thermal matrix.

        Returns:
            PipelineOutput.
        """
        # If distance provided, synthesize matching scan aligned with detection azimuth
        lidar_scan = None
        if lidar_distance_m is not None:
            from src.sensors.lidar2d import Lidar2DSimulator
            target_az = 0.0
            span_az = 8.0
            try:
                temp_vis = self.detector.predict_image(image)
                if temp_vis["patch_bbox"] is not None:
                    x1, y1, x2, y2 = temp_vis["patch_bbox"]
                    img_w = temp_vis["image_shape"][1]
                    target_az = self.lidar_associator.calculate_azimuth_from_pixel((x1 + x2) / 2.0, img_w)
                    az_left = self.lidar_associator.calculate_azimuth_from_pixel(x1, img_w)
                    az_right = self.lidar_associator.calculate_azimuth_from_pixel(x2, img_w)
                    span_az = abs(az_right - az_left) + 2.0
            except Exception:
                pass

            lidar_scan = Lidar2DSimulator().read_scan(
                target_azimuth_deg=target_az,
                target_distance_m=lidar_distance_m,
                azimuth_span_deg=span_az
            )

        # Build synchronized SensorFrame
        sensor_frame = self.sensor_hub.create_frame_from_image(
            image=image,
            thermal_matrix=thermal_matrix,
            lidar_scan=lidar_scan,
            road_surface_temp_c=road_surface_temp_c
        )

        return self.process_sensor_frame(sensor_frame)

    def _fuse_modalities(
        self,
        is_vision_ice: bool,
        ice_conf: float,
        temp_res: TemperatureScreeningResult,
        lidar_res: LidarAssociationResult,
        sensor_health: Dict[str, bool]
    ) -> Tuple[str, str]:
        """
        Fuse Vision + Temperature Screening (Module 2) + LiDAR Association (Module 5).

        Returns:
            Tuple[road_condition, uncertainty_status]
        """
        # Check sensor degradation
        all_sensors_ok = all(sensor_health.values())

        if is_vision_ice:
            # Case A: Visual candidate detected
            # Screen against temperature: ice cannot physically exist above freezing range (> 3°C)
            ref_temp = temp_res.patch_temp_c if temp_res.patch_temp_c is not None else temp_res.mean_surface_temp_c

            if ref_temp > self.wet_road_temp_cutoff:
                # Road temperature is too warm for ice -> it's standing water/wet road
                road_condition = "WET_ROAD_NO_ICE"
                uncertainty_status = "TEMP_SAFE_WET_SURFACE"
            else:
                # Temperature is in freezing/icing risk range!
                road_condition = "BLACK_ICE_HAZARD"

                if lidar_res.estimated_distance_m is not None:
                    if ice_conf >= self.high_conf_thresh:
                        uncertainty_status = "CONFIRMED_HIGH_CERTAINTY"
                    else:
                        uncertainty_status = "CONFIRMED_MEDIUM_CERTAINTY"
                elif lidar_res.specular_drop_detected:
                    # Specular dropout is a strong optical signature of smooth black ice!
                    uncertainty_status = "CONFIRMED_SPECULAR_LIDAR_ABSORPTION"
                elif not lidar_res.geometry_permitted:
                    uncertainty_status = "HIGH_RISK_LIDAR_OUT_OF_GEOMETRY"
                else:
                    uncertainty_status = "HIGH_RISK_NO_LIDAR_RETURN"

                if not all_sensors_ok:
                    uncertainty_status += "_SENSOR_DEGRADED"

        else:
            # Case B: No visual ice detected
            if temp_res.is_icing_risk and temp_res.mean_surface_temp_c <= 0.0:
                # Freezing road surface without obvious visual ice
                road_condition = "POTENTIAL_RISK"
                uncertainty_status = "SUBVISUAL_FREEZING_SURFACE"
            else:
                road_condition = "CLEAR"
                uncertainty_status = "SAFE"

        return road_condition, uncertainty_status
