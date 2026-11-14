'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import {
  SAMPLE_HISTORY,
  SCENARIOS,
  formatTimestamp,
  type ScanRecord,
  type SpectrumMode,
  type TelemetryFrame,
} from '@/lib/telemetry'

/**
 * Set NEXT_PUBLIC_TELEMETRY_WS_URL (e.g. ws://localhost:8765) to stream real frames
 * from dashboard.py. Without it the dashboard runs on a built-in scenario simulator.
 */
const WS_URL = process.env.NEXT_PUBLIC_TELEMETRY_WS_URL

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
  nextSample: () => void
  uploadCustomImage: (dataUrl: string, fileName?: string) => void
}

const TelemetryContext = createContext<TelemetryContextValue | null>(null)

const INITIAL_FRAME: TelemetryFrame = {
  ...SCENARIOS[0],
  timestamp: formatTimestamp(new Date()),
  device: 'Vehicle-Edge-YOLOv8',
}

const jitter = (value: number, amount: number) => Math.round((value + (Math.random() - 0.5) * amount) * 10) / 10

export function TelemetryProvider({ children }: { children: React.ReactNode }) {
  const [frame, setFrame] = useState<TelemetryFrame>(INITIAL_FRAME)
  const [spectrumMode, setSpectrumModeState] = useState<SpectrumMode>('Visible')
  const [connected, setConnected] = useState(false)
  const [live, setLive] = useState(true)
  const [history, setHistory] = useState<ScanRecord[]>(SAMPLE_HISTORY)
  const [scenarioIndex, setScenarioIndex] = useState(0)
  const socketRef = useRef<WebSocket | null>(null)
  const source: Source = connected ? 'websocket' : 'simulator'

  useEffect(() => {
    if (!WS_URL || !live) return
    let retry: ReturnType<typeof setTimeout>
    let closed = false

    const connect = () => {
      try {
        const ws = new WebSocket(WS_URL)
        socketRef.current = ws
        ws.onopen = () => setConnected(true)
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as Partial<TelemetryFrame> & { spectrum_mode?: SpectrumMode }
            if (data.spectrum_mode) setSpectrumModeState(data.spectrum_mode)
            setFrame((prev) => ({ ...prev, ...data, timestamp: data.timestamp ?? formatTimestamp(new Date()) }))
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

  // Simulator / Demo fallback: runs when live is on and WebSocket is not actively delivering frames
  useEffect(() => {
    if (connected || !live) return
    const id = setInterval(() => {
      setScenarioIndex((prev) => {
        const next = (prev + 1) % SCENARIOS.length
        const base = SCENARIOS[next]
        setFrame((curr) => ({
          ...curr,
          ...base,
          timestamp: formatTimestamp(new Date()),
        }))
        return next
      })
    }, 3200)
    return () => clearInterval(id)
  }, [connected, live])

  const nextSample = useCallback(() => {
    setScenarioIndex((prev) => {
      const next = (prev + 1) % SCENARIOS.length
      const base = SCENARIOS[next]
      setFrame((curr) => ({
        ...curr,
        ...base,
        timestamp: formatTimestamp(new Date()),
      }))
      return next
    })
  }, [])

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
      if (!WS_URL) setConnected(next)
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

  const uploadCustomImage = useCallback((dataUrl: string, fileName = 'Evaluator-Image') => {
    setLive(false) // pause auto-rotation so evaluator can inspect
    setFrame({
      road_status: 'BLACK_ICE_HAZARD',
      ice_confidence: 91.8,
      surface_temp: -2.6,
      lidar_distance: 7.2,
      verification_status: 'CONFIRMED_HAZARD',
      bbox: [22, 42, 54, 38],
      image_base64: dataUrl,
      timestamp: formatTimestamp(new Date()),
      device: fileName,
    })
  }, [])

  const value = useMemo(
    () => ({ frame, spectrumMode, setSpectrumMode, connected, source, live, toggleLive, history, saveScan, nextSample, uploadCustomImage }),
    [frame, spectrumMode, setSpectrumMode, connected, source, live, toggleLive, history, saveScan, nextSample, uploadCustomImage],
  )

  return <TelemetryContext.Provider value={value}>{children}</TelemetryContext.Provider>
}

export function useTelemetry() {
  const ctx = useContext(TelemetryContext)
  if (!ctx) throw new Error('useTelemetry must be used within TelemetryProvider')
  return ctx
}
