"""
Module 5 — 2D LiDAR Association.

Associates visual detections with valid 2D LiDAR rays and estimates center distance
when scan geometry permits. Also models specular absorption/dropout typical of smooth black ice.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List
import numpy as np

from src.sensors.lidar2d import LidarScan2D


@dataclass
class LidarAssociationResult:
    """Result of Module 5 LiDAR association."""
    estimated_distance_m: Optional[float]  # Estimated center distance in meters (None if unavailable)
    valid_ray_count: int                   # Number of valid returns within the detection sector
    total_rays_in_sector: int              # Total rays aimed into the bounding box azimuth
    center_azimuth_deg: float              # Azimuth angle of patch center in degrees
    azimuth_span_deg: Tuple[float, float]  # (min_angle, max_angle) of detection
    geometry_permitted: bool               # True if scan geometry permitted association
    specular_drop_detected: bool           # True if specular laser dropout (black ice signature) detected
    association_status: str                # Status message


class LidarAssociator:
    """
    Module 5: Associates visual bounding boxes with 2D LiDAR scan rays.
    Estimates center distance in meters when geometry permits.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        camera_fov_h_deg: float = 65.0,
        mount_height_m: float = 0.65,
        mount_pitch_deg: float = 2.5,
        min_range_m: float = 0.3,
        max_range_m: float = 40.0,
        azimuth_margin_deg: float = 1.5,
        min_valid_rays: int = 2
    ):
        """
        Initialize LiDAR Associator.

        Args:
            config: Optional configuration dictionary.
            camera_fov_h_deg: Horizontal field of view of RGB camera in degrees.
            mount_height_m: LiDAR mounting height above ground in meters.
            mount_pitch_deg: LiDAR downward pitch angle in degrees.
            min_range_m: Minimum valid range reading in meters.
            max_range_m: Maximum valid range reading in meters.
            azimuth_margin_deg: Angular margin added to visual box azimuth bounds.
            min_valid_rays: Minimum valid rays required for confident distance estimation.
        """
        self.config = config or {}
        lidar_cfg = self.config.get("sensors", {}).get("lidar_2d", {})
        cam_cfg = self.config.get("sensors", {}).get("camera", {})
        assoc_cfg = self.config.get("lidar_association", {})

        self.camera_fov_h_deg = cam_cfg.get("horizontal_fov_deg", camera_fov_h_deg)
        self.mount_height_m = lidar_cfg.get("mount_height_m", mount_height_m)
        self.mount_pitch_deg = lidar_cfg.get("mount_pitch_deg", mount_pitch_deg)
        self.min_range_m = lidar_cfg.get("min_range_m", min_range_m)
        self.max_range_m = lidar_cfg.get("max_range_m", max_range_m)
        self.azimuth_margin_deg = assoc_cfg.get("azimuth_margin_deg", azimuth_margin_deg)
        self.min_valid_rays = assoc_cfg.get("min_valid_rays", min_valid_rays)

    def calculate_azimuth_from_pixel(self, x: float, image_width: int) -> float:
        """
        Convert pixel horizontal coordinate to azimuth angle in degrees.
        Center pixel = 0.0°, Left < 0.0°, Right > 0.0°.
        """
        norm_x = (x - (image_width / 2.0)) / (image_width / 2.0)
        azimuth = norm_x * (self.camera_fov_h_deg / 2.0)
        return float(azimuth)

    def associate(
        self,
        patch_bbox: Optional[Tuple[int, int, int, int]],
        image_shape: Tuple[int, int],
        lidar_scan: LidarScan2D
    ) -> LidarAssociationResult:
        """
        Associate detection patch with 2D LiDAR rays.

        Args:
            patch_bbox: [x1, y1, x2, y2] bounding box in pixel coordinates.
            image_shape: (height, width) of the camera frame.
            lidar_scan: 2D planar LiDAR scan.

        Returns:
            LidarAssociationResult with estimated distance and geometry status.
        """
        if patch_bbox is None or lidar_scan is None or len(lidar_scan.angles_deg) == 0:
            return LidarAssociationResult(
                estimated_distance_m=None,
                valid_ray_count=0,
                total_rays_in_sector=0,
                center_azimuth_deg=0.0,
                azimuth_span_deg=(0.0, 0.0),
                geometry_permitted=False,
                specular_drop_detected=False,
                association_status="NO_TARGET_OR_SCAN"
            )

        img_h, img_w = image_shape
        x1, y1, x2, y2 = patch_bbox

        # 1. Calculate visual azimuth span
        theta_left = self.calculate_azimuth_from_pixel(x1, img_w)
        theta_right = self.calculate_azimuth_from_pixel(x2, img_w)
        min_az = min(theta_left, theta_right) - self.azimuth_margin_deg
        max_az = max(theta_left, theta_right) + self.azimuth_margin_deg
        center_az = self.calculate_azimuth_from_pixel((x1 + x2) / 2.0, img_w)

        # 2. Filter LiDAR rays within the detection sector
        angles = lidar_scan.angles_deg
        ranges = lidar_scan.ranges_m

        sector_mask = (angles >= min_az) & (angles <= max_az)
        total_rays = int(np.sum(sector_mask))

        if total_rays == 0:
            return LidarAssociationResult(
                estimated_distance_m=None,
                valid_ray_count=0,
                total_rays_in_sector=0,
                center_azimuth_deg=round(center_az, 2),
                azimuth_span_deg=(round(min_az, 2), round(max_az, 2)),
                geometry_permitted=False,
                specular_drop_detected=False,
                association_status="OUT_OF_LIDAR_FOV"
            )

        sector_ranges = ranges[sector_mask]
        valid_mask = (sector_ranges >= self.min_range_m) & (sector_ranges <= self.max_range_m)
        valid_ranges = sector_ranges[valid_mask]
        valid_count = int(len(valid_ranges))

        # 3. Detect Specular Absorption / Dropout (Black Ice Signature)
        # Smooth ice sheets specularly deflect laser pulses away, causing zero returns
        missing_count = total_rays - valid_count
        drop_ratio = missing_count / float(total_rays)
        specular_drop = (total_rays >= 3 and drop_ratio >= 0.6)

        # 4. Check Scan Geometry & Estimate Center Distance
        # If severe dropout occurred within the patch, flag specular reflection signature
        if specular_drop:
            estimated_dist = None
            geometry_permitted = True
            association_status = "SPECULAR_ABSORPTION_DETECTED"
        elif valid_count >= self.min_valid_rays:
            # Robust median distance estimation
            estimated_dist = float(np.median(valid_ranges))
            geometry_permitted = True
            association_status = "VALID_DISTANCE"
        else:
            estimated_dist = None
            geometry_permitted = False
            association_status = "INSUFFICIENT_LIDAR_RAYS"

        return LidarAssociationResult(
            estimated_distance_m=round(estimated_dist, 2) if estimated_dist is not None else None,
            valid_ray_count=valid_count,
            total_rays_in_sector=total_rays,
            center_azimuth_deg=round(center_az, 2),
            azimuth_span_deg=(round(min_az, 2), round(max_az, 2)),
            geometry_permitted=geometry_permitted,
            specular_drop_detected=specular_drop,
            association_status=association_status
        )
