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
  uploadCustomImage: (dataUrl: string, fileName?: string) => Promise<void>
  evaluating: boolean
  evalError: string | null
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
  const [evaluating, setEvaluating] = useState(false)
  const [evalError, setEvalError] = useState<string | null>(null)
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

  const uploadCustomImage = useCallback(async (dataUrl: string, fileName = 'Evaluator-Image') => {
    setLive(false) // pause auto-rotation
    setEvaluating(true)
    setEvalError(null)

    // Set preview image with scanning state (confidence 0 until model returns)
    setFrame((prev) => ({
      ...prev,
      image_base64: dataUrl,
      road_status: 'WET_ROAD_NO_ICE',
      ice_confidence: 0,
      bbox: null,
      device: `Evaluating: ${fileName}`,
      timestamp: formatTimestamp(new Date()),
    }))

    // Candidate API URLs: local backend first, then cloud backend
    const apiEndpoints = [
      'http://localhost:8000/api/predict',
      'https://black-ice-detection-w33c.onrender.com/api/predict',
    ]

    let evaluated = false

    for (const url of apiEndpoints) {
      try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 8000)
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_base64: dataUrl, conf_threshold: 0.25 }),
          signal: controller.signal,
        })
        clearTimeout(timeout)

        if (res.ok) {
          const data = await res.json()
          if (!data.error) {
            setFrame((prev) => ({
              ...prev,
              road_status: data.road_status,
              ice_confidence: data.ice_confidence,
              surface_temp: data.surface_temp,
              lidar_distance: data.lidar_distance,
              verification_status: data.verification_status,
              bbox: data.bbox,
              image_base64: dataUrl,
              device: fileName,
              timestamp: data.timestamp || formatTimestamp(new Date()),
            }))
            evaluated = true
            break
          }
        }
      } catch {
        // Try next endpoint
      }
    }

    setEvaluating(false)
    if (!evaluated) {
      setEvalError("Model backend offline. Run 'python run_backend.py' in your terminal to evaluate custom images live.")
    }
  }, [])

  const value = useMemo(
    () => ({
      frame,
      spectrumMode,
      setSpectrumMode,
      connected,
      source,
      live,
      toggleLive,
      history,
      saveScan,
      nextSample,
      uploadCustomImage,
      evaluating,
      evalError,
    }),
    [
      frame,
      spectrumMode,
      setSpectrumMode,
      connected,
      source,
      live,
      toggleLive,
      history,
      saveScan,
      nextSample,
      uploadCustomImage,
      evaluating,
      evalError,
    ],
  )

  return <TelemetryContext.Provider value={value}>{children}</TelemetryContext.Provider>
}

export function useTelemetry() {
  const ctx = useContext(TelemetryContext)
  if (!ctx) throw new Error('useTelemetry must be used within TelemetryProvider')
  return ctx
}
