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
  const [connected, setConnected] = useState(!WS_URL)
  const [live, setLive] = useState(true)
  const [history, setHistory] = useState<ScanRecord[]>(SAMPLE_HISTORY)
  const socketRef = useRef<WebSocket | null>(null)
  const source: Source = WS_URL ? 'websocket' : 'simulator'

  useEffect(() => {
    if (!WS_URL || !live) return
    let retry: ReturnType<typeof setTimeout>
    let closed = false

    const connect = () => {
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
        if (!closed) retry = setTimeout(connect, 2500)
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

  useEffect(() => {
    if (WS_URL || !live) return
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
    }, 1400)
    return () => clearInterval(id)
  }, [live])

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
