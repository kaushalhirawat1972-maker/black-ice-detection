"""
Module 2 — Temperature Screening.

Checks calibrated road-surface temperatures from the MLX90640 thermal array
against a configurable icing-risk range.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import numpy as np


@dataclass
class TemperatureScreeningResult:
    """Result of Module 2 temperature screening."""
    is_icing_risk: bool                  # True if surface temperature falls in icing-risk range
    mean_surface_temp_c: float          # Mean calibrated road surface temperature in °C
    min_surface_temp_c: float           # Coldest spot on road surface in °C
    patch_temp_c: Optional[float]       # Average temperature inside detected patch ROI (if any)
    thermal_risk_score: float           # Normalized risk score [0.0 = safe, 1.0 = high risk]
    screening_status: str               # Status descriptor
    calibrated_matrix: np.ndarray       # Full calibrated 24x32 thermal matrix
    icing_risk_range: Tuple[float, float] # Configured [min, max] range


class TemperatureScreener:
    """
    Module 2: Road Surface Temperature Screening.
    Applies emissivity calibration and evaluates road temperatures against configurable risk boundaries.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        min_risk_temp_c: float = -10.0,
        max_risk_temp_c: float = 3.0,
        critical_min_c: float = -3.0,
        critical_max_c: float = 1.0,
        emissivity: float = 0.95,
        offset_c: float = 0.0,
        gain: float = 1.0,
        road_roi_row_start: int = 10,
        road_roi_row_end: int = 24
    ):
        """
        Initialize Temperature Screener.

        Args:
            config: Optional configuration dictionary.
            min_risk_temp_c: Lower bound of icing risk range in °C.
            max_risk_temp_c: Upper bound of icing risk range in °C.
            critical_min_c: Lower bound of critical freezing band in °C.
            critical_max_c: Upper bound of critical freezing band in °C.
            emissivity: Road surface emissivity (asphalt/concrete ~0.95).
            offset_c: Sensor calibration offset in °C.
            gain: Sensor calibration gain.
            road_roi_row_start: Start row of MLX90640 road ROI (0-23).
            road_roi_row_end: End row of MLX90640 road ROI (1-24).
        """
        self.config = config or {}
        scr_cfg = self.config.get("temperature_screening", {})
        risk_range_cfg = scr_cfg.get("icing_risk_range", {})
        crit_range_cfg = scr_cfg.get("critical_freezing_range", {})
        cal_cfg = self.config.get("sensors", {}).get("mlx90640", {}).get("calibration", {})

        self.min_risk_temp_c = risk_range_cfg.get("min_temp_c", min_risk_temp_c)
        self.max_risk_temp_c = risk_range_cfg.get("max_temp_c", max_risk_temp_c)
        self.critical_min_c = crit_range_cfg.get("min_temp_c", critical_min_c)
        self.critical_max_c = crit_range_cfg.get("max_temp_c", critical_max_c)

        self.emissivity = cal_cfg.get("emissivity", emissivity)
        self.offset_c = cal_cfg.get("offset_c", offset_c)
        self.gain = cal_cfg.get("gain", gain)

        self.road_roi_row_start = scr_cfg.get("road_roi_row_start", road_roi_row_start)
        self.road_roi_row_end = scr_cfg.get("road_roi_row_end", road_roi_row_end)

    def calibrate(self, raw_matrix: np.ndarray) -> np.ndarray:
        """
        Calibrate raw MLX90640 temperature matrix for surface emissivity and sensor offset.

        Args:
            raw_matrix: Raw temperature array (24, 32) in °C.

        Returns:
            np.ndarray: Calibrated surface temperatures in °C.
        """
        # Emissivity compensation & linear gain/offset calibration
        # T_calibrated = ((T_raw + 273.15) / (emissivity ** 0.25)) - 273.15
        t_kelvin = raw_matrix + 273.15
        cal_kelvin = t_kelvin / (max(self.emissivity, 0.1) ** 0.25)
        calibrated = (cal_kelvin - 273.15) * self.gain + self.offset_c
        return calibrated.astype(np.float32)

    def screen_temperature(
        self,
        thermal_matrix: np.ndarray,
        patch_bbox: Optional[Tuple[int, int, int, int]] = None,
        image_shape: Optional[Tuple[int, int]] = None
    ) -> TemperatureScreeningResult:
        """
        Screen road temperatures against the configurable icing-risk range.

        Args:
            thermal_matrix: 24x32 temperature matrix from MLX90640 in °C.
            patch_bbox: Optional visual detection bounding box [x1, y1, x2, y2].
            image_shape: Optional image dimensions (height, width).

        Returns:
            TemperatureScreeningResult containing screening assessment.
        """
        calibrated = self.calibrate(thermal_matrix)

        # 1. Extract Road Surface Region of Interest (lower rows)
        r_start = np.clip(self.road_roi_row_start, 0, 23)
        r_end = np.clip(self.road_roi_row_end, r_start + 1, 24)
        road_roi = calibrated[r_start:r_end, :]

        mean_surface_temp = float(np.mean(road_roi))
        min_surface_temp = float(np.min(road_roi))

        # 2. Extract Patch-Specific Temperature (if bounding box provided)
        patch_temp = None
        if patch_bbox is not None and image_shape is not None:
            img_h, img_w = image_shape
            x1, y1, x2, y2 = patch_bbox

            # Project camera coordinates to 24x32 thermal grid
            t_r1 = int(np.clip(round((y1 / img_h) * 24), 0, 23))
            t_r2 = int(np.clip(round((y2 / img_h) * 24), t_r1 + 1, 24))
            t_c1 = int(np.clip(round((x1 / img_w) * 32), 0, 31))
            t_c2 = int(np.clip(round((x2 / img_w) * 32), t_c1 + 1, 32))

            patch_area = calibrated[t_r1:t_r2, t_c1:t_c2]
            if patch_area.size > 0:
                patch_temp = float(np.mean(patch_area))

        # Primary reference temperature: patch if available, otherwise mean road surface
        eval_temp = patch_temp if patch_temp is not None else mean_surface_temp

        # 3. Check against configurable icing-risk range
        is_icing_risk = (self.min_risk_temp_c <= eval_temp <= self.max_risk_temp_c)

        # 4. Compute Thermal Risk Score and Status
        if eval_temp > self.max_risk_temp_c:
            screening_status = "ABOVE_FREEZING_SAFE"
            # Farther above 3°C, lower the risk score
            thermal_risk_score = max(0.0, 1.0 - (eval_temp - self.max_risk_temp_c) / 5.0)
            is_icing_risk = False
        elif self.critical_min_c <= eval_temp <= self.critical_max_c:
            screening_status = "CRITICAL_FREEZING"
            thermal_risk_score = 1.0
        elif self.critical_max_c < eval_temp <= self.max_risk_temp_c:
            screening_status = "NEAR_FREEZING"
            # Linear transition between critical and safe
            ratio = (self.max_risk_temp_c - eval_temp) / (self.max_risk_temp_c - self.critical_max_c)
            thermal_risk_score = 0.5 + 0.5 * ratio
        elif self.min_risk_temp_c <= eval_temp < self.critical_min_c:
            screening_status = "SUB_ZERO_COLD"
            thermal_risk_score = 0.85
        else:
            screening_status = "EXTREME_COLD"
            thermal_risk_score = 0.50

        return TemperatureScreeningResult(
            is_icing_risk=is_icing_risk,
            mean_surface_temp_c=round(mean_surface_temp, 2),
            min_surface_temp_c=round(min_surface_temp, 2),
            patch_temp_c=round(patch_temp, 2) if patch_temp is not None else None,
            thermal_risk_score=round(float(thermal_risk_score), 3),
            screening_status=screening_status,
            calibrated_matrix=calibrated,
            icing_risk_range=(self.min_risk_temp_c, self.max_risk_temp_c)
        )
