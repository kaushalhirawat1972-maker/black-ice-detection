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
const CLOUD_API = 'https://black-ice-detection-w33c.onrender.com'

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
  backendReady: boolean
}

const TelemetryContext = createContext<TelemetryContextValue | null>(null)

const INITIAL_FRAME: TelemetryFrame = {
  ...SCENARIOS[0],
  timestamp: formatTimestamp(new Date()),
  device: 'Vehicle-Edge-YOLOv8',
}

export function TelemetryProvider({ children }: { children: React.ReactNode }) {
  const [frame, setFrame] = useState<TelemetryFrame>(INITIAL_FRAME)
  const [spectrumMode, setSpectrumModeState] = useState<SpectrumMode>('Visible')
  const [connected, setConnected] = useState(false)
  const [live, setLive] = useState(true)
  const [history, setHistory] = useState<ScanRecord[]>(SAMPLE_HISTORY)
  const [scenarioIndex, setScenarioIndex] = useState(0)
  const [evaluating, setEvaluating] = useState(false)
  const [evalError, setEvalError] = useState<string | null>(null)
  const [backendReady, setBackendReady] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)
  const source: Source = connected ? 'websocket' : 'simulator'

  // ─── Ping Render on page load to wake the container before the user uploads ─────
  useEffect(() => {
    const ping = async () => {
      try {
        // fire-and-forget: just wake the container up, don't block the UI
        await fetch(`${CLOUD_API}/health`, { method: 'GET' })
        setBackendReady(true)
      } catch {
        // container might still be sleeping; that's fine — uploadCustomImage retries
        setBackendReady(false)
      }
    }
    ping()
    // ping every 4 minutes to keep Render from sleeping (free tier sleeps after 15 min idle)
    const keepAlive = setInterval(ping, 4 * 60 * 1000)
    return () => clearInterval(keepAlive)
  }, [])

  // ─── WebSocket connection (live telemetry from Raspberry Pi / dashboard.py) ─────
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

  // ─── Simulator / Demo fallback when no live WebSocket data ───────────────────────
  useEffect(() => {
    if (connected || !live) return
    const id = setInterval(() => {
      setScenarioIndex((prev) => {
        const next = (prev + 1) % SCENARIOS.length
        const base = SCENARIOS[next]
        setFrame((curr) => ({ ...curr, ...base, timestamp: formatTimestamp(new Date()) }))
        return next
      })
    }, 3200)
    return () => clearInterval(id)
  }, [connected, live])

  const nextSample = useCallback(() => {
    setScenarioIndex((prev) => {
      const next = (prev + 1) % SCENARIOS.length
      const base = SCENARIOS[next]
      setFrame((curr) => ({ ...curr, ...base, timestamp: formatTimestamp(new Date()) }))
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

  // ─── Upload a custom image and get real model prediction ─────────────────────────
  const uploadCustomImage = useCallback(async (dataUrl: string, fileName = 'Evaluator-Image') => {
    setLive(false)
    setEvaluating(true)
    setEvalError(null)

    // Show preview while waiting
    setFrame((prev) => ({
      ...prev,
      image_base64: dataUrl,
      road_status: 'WET_ROAD_NO_ICE',
      ice_confidence: 0,
      bbox: null,
      device: `Evaluating: ${fileName}`,
      timestamp: formatTimestamp(new Date()),
    }))

    const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:'

    // On HTTPS pages the browser blocks http:// requests (mixed content), so try cloud first
    const apiEndpoints = isHttps
      ? [`${CLOUD_API}/api/predict`, 'http://localhost:8000/api/predict']
      : ['http://localhost:8000/api/predict', `${CLOUD_API}/api/predict`]

    let evaluated = false
    let failureDetail: string | null = null

    for (const url of apiEndpoints) {
      // Skip the localhost URL when served over HTTPS (browser will block it anyway)
      if (isHttps && url.startsWith('http://')) continue

      const maxAttempts = 4
      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
          const controller = new AbortController()
          // 90 seconds per attempt — enough for Render cold-start
          const timer = setTimeout(() => controller.abort(), 90_000)

          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: dataUrl, conf_threshold: 0.25 }),
            signal: controller.signal,
          })
          clearTimeout(timer)

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
                bbox: data.bbox ?? null,
                image_base64: dataUrl,
                device: fileName,
                timestamp: data.timestamp || formatTimestamp(new Date()),
              }))
              evaluated = true
              break
            } else {
              failureDetail = data.error
            }
          } else {
            failureDetail = `Backend returned HTTP ${res.status}`
          }
        } catch (err: any) {
          if (err?.name === 'AbortError') {
            failureDetail = `Attempt ${attempt}/${maxAttempts} timed out. Render backend may be starting…`
          } else {
            failureDetail = err?.message ?? 'Network error'
          }
          if (attempt < maxAttempts) {
            // exponential back-off: 5s, 10s, 20s
            await new Promise((r) => setTimeout(r, 5_000 * attempt))
          }
        }
      }
      if (evaluated) break
    }

    setEvaluating(false)
    if (!evaluated) {
      setEvalError(
        failureDetail
          ? `Model service error: ${failureDetail}. Please wait ~30s for the server to wake up and try again.`
          : isHttps
          ? 'Cloud backend is offline. Please try again in 30 seconds.'
          : "Model backend offline. Run 'python run_backend.py' to evaluate images locally."
      )
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
      backendReady,
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
      backendReady,
    ]
  )

  return <TelemetryContext.Provider value={value}>{children}</TelemetryContext.Provider>
}

export function useTelemetry() {
  const ctx = useContext(TelemetryContext)
  if (!ctx) throw new Error('useTelemetry must be used within TelemetryProvider')
  return ctx
}
