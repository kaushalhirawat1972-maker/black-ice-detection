/**
 * TypeScript Data Definitions for BLACK ICE DETECTION Frontend
 * Use these types directly in your React / Next.js / Vue components.
 */

export interface BlackIceTelemetry {
  timestamp: string;
  device_id: string;
  
  // 5 Core Detection Outputs
  road_condition: "BLACK_ICE_HAZARD" | "WET_ROAD_NO_ICE" | "ROAD_CLEAR" | string;
  ice_confidence: number;              // 0.0 to 1.0 (e.g. 0.942 = 94.2%)
  patch_bbox?: [number, number, number, number]; // [x1, y1, x2, y2]
  estimated_distance_m?: number;       // Distance in meters (e.g. 11.8)
  uncertainty_status: string;          // e.g. "CONFIRMED_HAZARD"

  // Sensor Telemetry
  surface_temp_c: number;              // Road temperature in Celsius (e.g. -2.5)
  ambient_temp_c?: number;             // Ambient temperature
  lidar_specular_dropout: boolean;     // True if laser mirrored away on smooth ice

  // Actuator Telemetry
  deicing_active: boolean;             // True if spray nozzle is currently pulsing
  spray_lane?: string;                 // "LEFT LANE", "CENTER DUAL", or "RIGHT LANE"
  time_to_impact_sec?: number;         // Countdown to impact at vehicle speed

  // Visual Feed
  image_base64?: string;               // JPEG Data URI: "data:image/jpeg;base64,..."
}

export interface HistoricalScan {
  timestamp: string;
  device_id: string;
  road_condition: string;
  ice_confidence: number;
  surface_temp_c: number;
  estimated_distance_m?: number;
  uncertainty_status: string;
  deicing_active: boolean;
}
