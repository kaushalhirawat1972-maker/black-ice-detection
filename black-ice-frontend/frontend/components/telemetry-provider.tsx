'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import {
  SAMPLE_HISTORY,
  SCENARIOS,
  formatTimestamp,
  type BBox,
  type RoadStatus,
  type ScanRecord,
  type SpectrumMode,
  type TelemetryFrame,
  type VerificationStatus,
} from '@/lib/telemetry'

/**
 * WebSocket endpoint: uses NEXT_PUBLIC_TELEMETRY_WS_URL or defaults to FastAPI backend on port 8000.
 */
const WS_URL = process.env.NEXT_PUBLIC_TELEMETRY_WS_URL || 'ws://localhost:8000/ws/live'

type Source = 'websocket' | 'simulator'

interface TelemetryContextValue {
  frame: TelemetryFrame
  spectrumMode: SpectrumMode
  setSpectrumMode: (mode: SpectrumMode) => void
  connected: boolean
  source: Source
  live: boolean
  toggleLive: () => void
  history: ScanRecord[]
  saveScan: () => void
}

const TelemetryContext = createContext<TelemetryContextValue | null>(null)

const INITIAL_FRAME: TelemetryFrame = {
  ...SCENARIOS[0],
  timestamp: '2026-10-27 21:20:05',
  device: 'Vehicle-Pi4-Front',
  image_base64: null,
}

const jitter = (value: number, amount: number) => Math.round((value + (Math.random() - 0.5) * amount) * 10) / 10

export function TelemetryProvider({ children }: { children: React.ReactNode }) {
  const [frame, setFrame] = useState<TelemetryFrame>(INITIAL_FRAME)
  const [spectrumMode, setSpectrumModeState] = useState<SpectrumMode>('Visible')
  const [connected, setConnected] = useState(false)
  const [live, setLive] = useState(true)
  const [history, setHistory] = useState<ScanRecord[]>(SAMPLE_HISTORY)
  const socketRef = useRef<WebSocket | null>(null)
  const source: Source = connected ? 'websocket' : 'simulator'

  useEffect(() => {
    if (!live || typeof window === 'undefined') return
    let retry: ReturnType<typeof setTimeout>
    let closed = false

    const connect = () => {
      try {
        const ws = new WebSocket(WS_URL)
        socketRef.current = ws

        ws.onopen = () => {
          setConnected(true)
        }

        ws.onmessage = (event) => {
          try {
            const raw = JSON.parse(event.data)

            // Map backend packet format to TelemetryFrame
            const road_status: RoadStatus =
              raw.road_status ||
              (raw.road_condition === 'BLACK_ICE_HAZARD'
                ? 'BLACK_ICE_HAZARD'
                : raw.road_condition && raw.road_condition.includes('WET')
                  ? 'WET_ROAD_NO_ICE'
                  : 'ROAD_CLEAR')

            // If confidence is 0.0 - 1.0, convert to percentage 0 - 100
            let ice_confidence = raw.ice_confidence ?? 0
            if (ice_confidence <= 1.0 && ice_confidence > 0) {
              ice_confidence = Math.round(ice_confidence * 1000) / 10
            }

            const surface_temp = raw.surface_temp ?? raw.surface_temp_c ?? 0
            const lidar_distance = raw.lidar_distance ?? raw.estimated_distance_m ?? 0

            const verification_status: VerificationStatus =
              raw.verification_status ||
              (raw.uncertainty_status === 'CONFIRMED_HAZARD'
                ? 'CONFIRMED_HAZARD'
                : raw.uncertainty_status === 'WARM_SURFACE_FILTERED'
                  ? 'WARM_SURFACE_FILTERED'
                  : 'NO_DETECTION')

            // Map [x1, y1, x2, y2] to percentage [x, y, w, h]
            let bbox: BBox | null = raw.bbox ?? null
            if (!bbox && raw.patch_bbox && Array.isArray(raw.patch_bbox) && raw.patch_bbox.length === 4) {
              const [x1, y1, x2, y2] = raw.patch_bbox
              const bx = Math.max(0, Math.min(90, Math.round((x1 / 640) * 100)))
              const by = Math.max(0, Math.min(90, Math.round((y1 / 480) * 100)))
              const bw = Math.max(5, Math.min(100 - bx, Math.round(((x2 - x1) / 640) * 100)))
              const bh = Math.max(5, Math.min(100 - by, Math.round(((y2 - y1) / 480) * 100)))
              bbox = [bx, by, bw, bh]
            }

            if (raw.spectrum_mode) setSpectrumModeState(raw.spectrum_mode)

            setFrame((prev) => ({
              ...prev,
              road_status,
              ice_confidence,
              surface_temp,
              lidar_distance,
              verification_status,
              bbox,
              image_base64: raw.image_base64 ?? prev.image_base64,
              device: raw.device ?? raw.device_id ?? prev.device,
              timestamp: raw.timestamp ?? formatTimestamp(new Date()),
            }))
          } catch {
            // ignore malformed frames
          }
        }

        ws.onclose = () => {
          setConnected(false)
          if (!closed) retry = setTimeout(connect, 3000)
        }

        ws.onerror = () => {
          setConnected(false)
        }
      } catch {
        setConnected(false)
        if (!closed) retry = setTimeout(connect, 4000)
      }
    }

    connect()

    return () => {
      closed = true
      clearTimeout(retry)
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [live])

  // Built-in scenario simulator: active when live stream is not connected
  useEffect(() => {
    if (connected || !live) return
    let tick = 0
    let scenario = 0
    const id = setInterval(() => {
      tick += 1
      if (tick % 5 === 0) scenario = (scenario + 1) % SCENARIOS.length
      const base = SCENARIOS[scenario]
      setFrame((prev) => ({
        ...prev,
        ...base,
        ice_confidence: Math.max(0, Math.min(99.9, jitter(base.ice_confidence, 3))),
        surface_temp: jitter(base.surface_temp, 0.6),
        lidar_distance: Math.max(0.5, jitter(base.lidar_distance, 0.8)),
        timestamp: formatTimestamp(new Date()),
      }))
    }, 1500)
    return () => clearInterval(id)
  }, [connected, live])

  const setSpectrumMode = useCallback((mode: SpectrumMode) => {
    setSpectrumModeState(mode)
    const ws = socketRef.current
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'set_spectrum_mode', spectrum_mode: mode }))
    }
  }, [])

  const toggleLive = useCallback(() => {
    setLive((prev) => {
      const next = !prev
      if (!next) setConnected(false)
      return next
    })
  }, [])

  const saveScan = useCallback(() => {
    setHistory((prev) => [
      {
        id: `${Date.now()}`,
        timestamp: frame.timestamp,
        road_status: frame.road_status,
        ice_confidence: frame.ice_confidence,
        surface_temp: frame.surface_temp,
        lidar_distance: frame.lidar_distance,
        verification_status: frame.verification_status,
      },
      ...prev,
    ])
  }, [frame])

  const value = useMemo(
    () => ({ frame, spectrumMode, setSpectrumMode, connected, source, live, toggleLive, history, saveScan }),
    [frame, spectrumMode, setSpectrumMode, connected, source, live, toggleLive, history, saveScan],
  )

  return <TelemetryContext.Provider value={value}>{children}</TelemetryContext.Provider>
}

export function useTelemetry() {
  const ctx = useContext(TelemetryContext)
  if (!ctx) throw new Error('useTelemetry must be used within TelemetryProvider')
  return ctx
}
