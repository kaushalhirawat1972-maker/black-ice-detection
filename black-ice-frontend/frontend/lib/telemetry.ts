export type RoadStatus = 'BLACK_ICE_HAZARD' | 'WET_ROAD_NO_ICE' | 'ROAD_CLEAR'
export type VerificationStatus = 'CONFIRMED_HAZARD' | 'WARM_SURFACE_FILTERED' | 'NO_DETECTION'
export type SpectrumMode = 'Visible' | 'Thermal' | 'Edge'
export type Tone = 'hazard' | 'warn' | 'safe'

/** Bounding box in percentages of the viewport: [x, y, width, height] */
export type BBox = [number, number, number, number]

/** Shape of a single frame pushed by dashboard.py (over WebSocket) */
export interface TelemetryFrame {
  road_status: RoadStatus
  ice_confidence: number
  surface_temp: number
  lidar_distance: number
  verification_status: VerificationStatus
  image_base64?: string | null
  bbox?: BBox | null
  timestamp: string
  device: string
}

export interface ScanRecord {
  id: string
  timestamp: string
  road_status: RoadStatus
  ice_confidence: number
  surface_temp: number
  lidar_distance: number
  verification_status: VerificationStatus
}

export const STATUS_META: Record<RoadStatus, { label: string; short: string; tone: Tone; description: string }> = {
  BLACK_ICE_HAZARD: {
    label: 'Black ice hazard',
    short: 'Black Ice',
    tone: 'hazard',
    description: 'Invisible ice glaze confirmed by thermal, vision and LiDAR fusion. De-icing actuation armed.',
  },
  WET_ROAD_NO_ICE: {
    label: 'Wet road, no ice',
    short: 'Wet Road',
    tone: 'warn',
    description: 'Reflective wet surface detected, but surface temperature is outside the freezing envelope.',
  },
  ROAD_CLEAR: {
    label: 'Road clear',
    short: 'Clear',
    tone: 'safe',
    description: 'Dry asphalt. No ice signatures across any sensor channel.',
  },
}

export const VERIFICATION_TONE: Record<VerificationStatus, Tone> = {
  CONFIRMED_HAZARD: 'hazard',
  WARM_SURFACE_FILTERED: 'warn',
  NO_DETECTION: 'safe',
}

export const TONE_STYLES: Record<Tone, { text: string; bg: string; border: string; dot: string; hex: string }> = {
  hazard: { text: 'text-hazard', bg: 'bg-hazard/10', border: 'border-hazard/30', dot: 'bg-hazard', hex: '#d98a3d' },
  warn: { text: 'text-warn', bg: 'bg-warn/10', border: 'border-warn/30', dot: 'bg-warn', hex: '#d9a441' },
  safe: { text: 'text-safe', bg: 'bg-safe/10', border: 'border-safe/30', dot: 'bg-safe', hex: '#5fae8a' },
}

export const SCENARIOS: (Omit<TelemetryFrame, 'timestamp' | 'device'> & { image_base64?: string | null })[] = [
  {
    road_status: 'BLACK_ICE_HAZARD',
    ice_confidence: 93.3,
    surface_temp: -2.8,
    lidar_distance: 6.2,
    verification_status: 'CONFIRMED_HAZARD',
    bbox: [17.9, 31.9, 82.1, 67.6],
    image_base64: '/test_samples/ice_sample_3.jpg',
  },
  {
    road_status: 'BLACK_ICE_HAZARD',
    ice_confidence: 89.2,
    surface_temp: -1.9,
    lidar_distance: 7.8,
    verification_status: 'CONFIRMED_HAZARD',
    bbox: [51.5, 59.6, 37.8, 21.1],
    image_base64: '/test_samples/ice_sample_2.jpg',
  },
  {
    road_status: 'BLACK_ICE_HAZARD',
    ice_confidence: 84.5,
    surface_temp: -3.4,
    lidar_distance: 9.1,
    verification_status: 'CONFIRMED_HAZARD',
    bbox: [18.8, 66.3, 15.8, 12.5],
    image_base64: '/test_samples/ice_sample_1.jpg',
  },
  {
    road_status: 'ROAD_CLEAR',
    ice_confidence: 2.1,
    surface_temp: 5.6,
    lidar_distance: 35.0,
    verification_status: 'NO_DETECTION',
    bbox: null,
    image_base64: '/test_samples/dry_sample_1.jpg',
  },
]

export const SAMPLE_HISTORY: ScanRecord[] = [
  { id: 's1', timestamp: '2026-10-27 21:20:05', road_status: 'BLACK_ICE_HAZARD', ice_confidence: 94.2, surface_temp: -2.5, lidar_distance: 11.8, verification_status: 'CONFIRMED_HAZARD' },
  { id: 's2', timestamp: '2026-10-27 21:18:42', road_status: 'WET_ROAD_NO_ICE', ice_confidence: 38.9, surface_temp: 4.1, lidar_distance: 16.2, verification_status: 'WARM_SURFACE_FILTERED' },
  { id: 's3', timestamp: '2026-10-27 21:16:10', road_status: 'ROAD_CLEAR', ice_confidence: 4.7, surface_temp: 6.8, lidar_distance: 31.5, verification_status: 'NO_DETECTION' },
  { id: 's4', timestamp: '2026-10-27 21:13:57', road_status: 'BLACK_ICE_HAZARD', ice_confidence: 88.6, surface_temp: -4.1, lidar_distance: 9.4, verification_status: 'CONFIRMED_HAZARD' },
  { id: 's5', timestamp: '2026-10-27 21:11:23', road_status: 'WET_ROAD_NO_ICE', ice_confidence: 52.3, surface_temp: 3.4, lidar_distance: 13.7, verification_status: 'WARM_SURFACE_FILTERED' },
  { id: 's6', timestamp: '2026-10-27 21:08:01', road_status: 'ROAD_CLEAR', ice_confidence: 2.1, surface_temp: 8.9, lidar_distance: 36.0, verification_status: 'NO_DETECTION' },
]

export function formatTimestamp(date: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

/** Turns machine codes like CONFIRMED_HAZARD into "Confirmed hazard" for display. */
export function readable(code: string): string {
  const s = code.toLowerCase().replace(/_/g, ' ')
  return s.charAt(0).toUpperCase() + s.slice(1)
}
