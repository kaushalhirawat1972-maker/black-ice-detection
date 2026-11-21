'use client'

import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Image from 'next/image'
import { ExternalLink, Radio, Settings, Video } from 'lucide-react'
import { STATUS_META, TONE_STYLES, type SpectrumMode } from '@/lib/telemetry'
import { cn } from '@/lib/utils'
import { useTelemetry } from './telemetry-provider'

const DEFAULT_BASE_HOST = 'http://192.168.137.248:5003'
const DEFAULT_RGB_URL = 'http://192.168.137.248:5003/rgb_feed'
const DEFAULT_THERMAL_URL = 'http://192.168.137.248:5003/thermal_feed'

const MODES: { id: SpectrumMode; label: string; hint: string }[] = [
  { id: 'Visible', label: 'Visible', hint: 'RGB 1080p' },
  { id: 'Thermal', label: 'Thermal', hint: 'MLX90640' },
  { id: 'Edge', label: 'Edge View', hint: 'LiDAR fan' },
]

const MODE_FILTER: Record<SpectrumMode, string> = {
  Visible: 'none',
  Thermal: 'grayscale(1) contrast(1.4) brightness(1.1)',
  Edge: 'grayscale(1) contrast(3.2) brightness(0.55)',
}

function Reticles() {
  const base = 'absolute size-7 border-ice/90'
  return (
    <div aria-hidden className="pointer-events-none absolute inset-4 sm:inset-5">
      <span className={cn(base, 'left-0 top-0 rounded-tl-md border-l-2 border-t-2')} />
      <span className={cn(base, 'right-0 top-0 rounded-tr-md border-r-2 border-t-2')} />
      <span className={cn(base, 'bottom-0 left-0 rounded-bl-md border-b-2 border-l-2')} />
      <span className={cn(base, 'bottom-0 right-0 rounded-br-md border-b-2 border-r-2')} />
      <span className="absolute left-1/2 top-1/2 size-4 -translate-x-1/2 -translate-y-1/2">
        <span className="absolute left-1/2 top-0 h-full w-px bg-ice/60" />
        <span className="absolute left-0 top-1/2 h-px w-full bg-ice/60" />
      </span>
    </div>
  )
}

function LidarFan() {
  const rays = Array.from({ length: 19 }, (_, i) => -45 + i * 5)
  return (
    <svg aria-hidden viewBox="0 0 100 56.25" preserveAspectRatio="none" className="absolute inset-0 size-full">
      {rays.map((deg) => {
        const rad = (deg * Math.PI) / 180
        const len = 42
        return (
          <line
            key={deg}
            x1="50"
            y1="56.25"
            x2={50 + len * Math.sin(rad) * 1.2}
            y2={56.25 - len * Math.cos(rad)}
            stroke="#38bdf8"
            strokeOpacity={0.45}
            strokeWidth="0.15"
          />
        )
      })}
      {[14, 26, 38].map((r) => (
        <path
          key={r}
          d={`M ${50 - r * 0.85} ${56.25 - r * 0.7} Q 50 ${56.25 - r * 1.15} ${50 + r * 0.85} ${56.25 - r * 0.7}`}
          fill="none"
          stroke="#7dd3fc"
          strokeOpacity={0.35}
          strokeWidth="0.15"
          strokeDasharray="0.8 0.8"
        />
      ))}
    </svg>
  )
}

export function RoadViewport() {
  const { frame, spectrumMode, setSpectrumMode } = useTelemetry()
  const [rgbUrl, setRgbUrl] = useState(DEFAULT_RGB_URL)
  const [thermalUrl, setThermalUrl] = useState(DEFAULT_THERMAL_URL)
  const [viewMode, setViewMode] = useState<'camera' | 'sample'>('camera')
  const [isEditingIp, setIsEditingIp] = useState(false)
  const [inputBaseHost, setInputBaseHost] = useState(DEFAULT_BASE_HOST)
  const [inputRgbUrl, setInputRgbUrl] = useState(DEFAULT_RGB_URL)
  const [inputThermalUrl, setInputThermalUrl] = useState(DEFAULT_THERMAL_URL)
  const [isHttps, setIsHttps] = useState(false)
  const [imgLoadError, setImgLoadError] = useState(false)

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsHttps(window.location.protocol === 'https:')
      const savedRgb = localStorage.getItem('black_ice_rgb_url')
      const savedThermal = localStorage.getItem('black_ice_thermal_url')
      const savedHost = localStorage.getItem('black_ice_base_host')

      if (savedRgb) {
        setRgbUrl(savedRgb)
        setInputRgbUrl(savedRgb)
      }
      if (savedThermal) {
        setThermalUrl(savedThermal)
        setInputThermalUrl(savedThermal)
      }
      if (savedHost) {
        setInputBaseHost(savedHost)
      }
    }
  }, [])

  // Active stream switches automatically based on chosen spectrum mode
  const activeStreamUrl = spectrumMode === 'Thermal' ? thermalUrl : rgbUrl

  useEffect(() => {
    setImgLoadError(false)
  }, [activeStreamUrl])

  // Automatically switch to sample view when user uploads an image for evaluation
  useEffect(() => {
    if (frame.image_base64 && frame.image_base64.startsWith('data:')) {
      setViewMode('sample')
    }
  }, [frame.image_base64])

  const saveCameraIp = (e: React.FormEvent) => {
    e.preventDefault()
    let host = inputBaseHost.trim().replace(/\/$/, '')
    if (host && !host.startsWith('http://') && !host.startsWith('https://')) {
      host = `http://${host}`
    }

    let rgb = inputRgbUrl.trim()
    if (!rgb) rgb = `${host}/rgb_feed`
    else if (!rgb.startsWith('http://') && !rgb.startsWith('https://')) rgb = `http://${rgb}`

    let thermal = inputThermalUrl.trim()
    if (!thermal) thermal = `${host}/thermal_feed`
    else if (!thermal.startsWith('http://') && !thermal.startsWith('https://')) thermal = `http://${thermal}`

    setRgbUrl(rgb)
    setThermalUrl(thermal)

    if (typeof window !== 'undefined') {
      localStorage.setItem('black_ice_base_host', host)
      localStorage.setItem('black_ice_rgb_url', rgb)
      localStorage.setItem('black_ice_thermal_url', thermal)
    }
    setIsEditingIp(false)
  }

  const meta = STATUS_META[frame.road_status]
  const tone = TONE_STYLES[meta.tone]
  const src = frame.image_base64
    ? (frame.image_base64.startsWith('data:') || frame.image_base64.startsWith('/') || frame.image_base64.startsWith('http'))
      ? frame.image_base64
      : `data:image/jpeg;base64,${frame.image_base64}`
    : '/images/road-feed.jpg'

  // Show live bot camera feed when in 'camera' mode and no custom file was just uploaded
  const showLiveStream = viewMode === 'camera' && (!frame.image_base64 || !frame.image_base64.startsWith('data:'))

  return (
    <div className="glass-dark rounded-sm p-3 sm:p-4" data-spot={meta.tone === 'safe' ? 'ice' : meta.tone}>
      <div className="relative aspect-video overflow-hidden rounded-sm bg-slate-900">
        <AnimatePresence mode="sync">
          <motion.div
            key={spectrumMode + (showLiveStream ? '-live' : '-sample')}
            initial={{ opacity: 0, scale: 1.02 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="absolute inset-0"
          >
            {showLiveStream ? (
              !imgLoadError ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={activeStreamUrl}
                  alt={`Live ${spectrumMode} Bot Stream`}
                  className="size-full object-cover"
                  style={{
                    filter: spectrumMode === 'Thermal' ? 'none' : MODE_FILTER[spectrumMode],
                  }}
                  onError={() => setImgLoadError(true)}
                />
              ) : (
                <iframe
                  src={activeStreamUrl}
                  title={`Live ${spectrumMode} Bot Feed`}
                  className="size-full border-0 object-cover"
                  style={{
                    filter: spectrumMode === 'Thermal' ? 'none' : MODE_FILTER[spectrumMode],
                  }}
                  allow="autoplay; fullscreen"
                />
              )
            ) : (
              <Image
                src={src || '/placeholder.svg'}
                alt="Forward road camera feed on a frosted highway at dusk"
                fill
                sizes="(min-width: 1024px) 66vw, 100vw"
                className="object-cover"
                style={{ filter: MODE_FILTER[spectrumMode] }}
                unoptimized={Boolean(frame.image_base64)}
                priority
              />
            )}

            {/* Synthetic Thermal gradient is ONLY applied on static test samples, never overriding the real thermal camera */}
            {spectrumMode === 'Thermal' && !showLiveStream && (
              <>
                <div
                  className="pointer-events-none absolute inset-0 mix-blend-color"
                  style={{ background: 'linear-gradient(to top, #fff3c4 0%, #ffd166 22%, #a7f3d0 45%, #38bdf8 70%, #0f172a 100%)' }}
                />
                {frame.bbox && (
                  <div
                    className="pointer-events-none absolute rounded-[40%] blur-2xl"
                    style={{
                      left: `${frame.bbox[0] - 4}%`,
                      top: `${frame.bbox[1] - 4}%`,
                      width: `${frame.bbox[2] + 8}%`,
                      height: `${frame.bbox[3] + 8}%`,
                      background: 'radial-gradient(circle, rgba(56,189,248,0.85), rgba(19,49,92,0.5) 60%, transparent)',
                    }}
                  />
                )}
              </>
            )}

            {spectrumMode === 'Edge' && (
              <>
                <div className="pointer-events-none absolute inset-0 bg-ice/40 mix-blend-screen" />
                <div className="pointer-events-none absolute inset-0 bg-slate-900/30" />
                <LidarFan />
              </>
            )}
          </motion.div>
        </AnimatePresence>

        <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[10%] animate-scan bg-gradient-to-b from-transparent via-ice/10 to-transparent" />
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-gradient-to-t from-slate-950/60 via-transparent to-slate-950/20" />
        <Reticles />

        {/* Hazard Bounding Box Overlay */}
        <AnimatePresence>
          {frame.bbox && meta.tone !== 'safe' && (
            <motion.div
              key={frame.road_status}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{
                opacity: 1,
                scale: 1,
                left: `${frame.bbox[0]}%`,
                top: `${frame.bbox[1]}%`,
                width: `${frame.bbox[2]}%`,
                height: `${frame.bbox[3]}%`,
              }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className="pointer-events-none absolute rounded-sm border-2"
              style={{
                borderColor: tone.hex,
                boxShadow: `0 0 20px ${tone.hex}66, inset 0 0 16px ${tone.hex}33`,
                background: `${tone.hex}12`,
              }}
            >
              <span
                className="absolute -top-7 left-0 whitespace-nowrap rounded-sm px-2 py-1 font-mono text-[10px] font-bold tracking-wide text-navy sm:text-[11px]"
                style={{ background: tone.hex }}
              >
                {meta.tone === 'hazard' ? 'BLACK ICE HAZARD' : 'WET SURFACE'} {frame.ice_confidence.toFixed(1)}% ·{' '}
                {frame.lidar_distance.toFixed(1)}m
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Top-Left Status & Stream Indicator */}
        <div className="absolute left-4 top-4 flex flex-wrap items-center gap-2 sm:left-6 sm:top-6 z-20">
          <span className={cn(
            "inline-flex items-center gap-1.5 rounded-sm px-2 py-1 font-mono text-[10px] font-bold tracking-wider",
            showLiveStream ? "bg-emerald-500/90 text-slate-950" : "bg-amber-400/90 text-slate-950"
          )}>
            <span className="size-1.5 animate-pulse rounded-full bg-white" />
            {showLiveStream ? (spectrumMode === 'Thermal' ? 'LIVE THERMAL' : 'LIVE RGB') : 'TEST SAMPLE'}
          </span>
          <span className="rounded-sm border border-ice/30 bg-slate-900/70 px-2 py-1 font-mono text-[10px] font-semibold tracking-wider text-ice backdrop-blur">
            {spectrumMode.toUpperCase()} · 30 FPS
          </span>
          {showLiveStream && (
            <div className="flex items-center gap-1 rounded-sm border border-white/20 bg-slate-950/70 px-2 py-1 font-mono text-[10px] text-snow backdrop-blur">
              <span className="text-silver">{spectrumMode === 'Thermal' ? 'THERMAL:' : 'RGB:'}</span>
              <span className="text-sky font-semibold truncate max-w-[140px] sm:max-w-[200px]" title={activeStreamUrl}>
                {activeStreamUrl.replace(/^https?:\/\//, '')}
              </span>
              <button
                type="button"
                onClick={() => setIsEditingIp(true)}
                className="ml-1 text-silver hover:text-white transition-colors p-0.5"
                title="Configure Stream Endpoints"
              >
                <Settings className="size-3" />
              </button>
              <a
                href={activeStreamUrl}
                target="_blank"
                rel="noreferrer"
                className="ml-0.5 text-silver hover:text-sky transition-colors p-0.5"
                title="Open Active Feed in Direct Tab"
              >
                <ExternalLink className="size-3" />
              </a>
            </div>
          )}
        </div>

        {/* Top-Right Toggle: Live Camera vs Sample Demo */}
        <div className="absolute right-4 top-4 z-20 flex items-center gap-1 rounded-sm border border-white/15 bg-slate-950/70 p-0.5 backdrop-blur">
          <button
            type="button"
            onClick={() => setViewMode('camera')}
            className={cn(
              'flex items-center gap-1 rounded-xs px-2 py-1 font-mono text-[10px] font-semibold transition-all',
              viewMode === 'camera' ? 'bg-ice text-white shadow-sm' : 'text-silver hover:text-snow'
            )}
            title="Switch to live IP camera feed"
          >
            <Video className="size-3" />
            Live Bot Feed
          </button>
          <button
            type="button"
            onClick={() => setViewMode('sample')}
            className={cn(
              'flex items-center gap-1 rounded-xs px-2 py-1 font-mono text-[10px] font-semibold transition-all',
              viewMode === 'sample' ? 'bg-ice text-white shadow-sm' : 'text-silver hover:text-snow'
            )}
            title="Switch to evaluated test sample images"
          >
            <Radio className="size-3" />
            Test Samples
          </button>
        </div>

        {/* HTTPS Mixed-Content Info Banner */}
        {isHttps && showLiveStream && (
          <div className="pointer-events-auto absolute top-14 left-4 right-4 sm:left-6 sm:right-auto z-20 flex items-center gap-2 rounded bg-amber-500/15 border border-amber-500/30 px-2.5 py-1 text-[10px] text-amber-200 backdrop-blur">
            <span>Browser HTTPS may block local HTTP stream.</span>
            <a href={activeStreamUrl} target="_blank" rel="noreferrer" className="underline font-semibold hover:text-white flex items-center gap-0.5">
              Open stream directly <ExternalLink className="size-2.5" />
            </a>
          </div>
        )}

        {/* IP & Stream Configuration Modal */}
        {isEditingIp && (
          <div className="absolute inset-0 z-30 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
            <form onSubmit={saveCameraIp} className="w-full max-w-md rounded-md border border-ice/40 bg-slate-900 p-5 shadow-2xl space-y-3">
              <div>
                <h4 className="font-semibold text-snow text-sm flex items-center gap-2">
                  <Video className="size-4 text-ice" />
                  Configure Stream Endpoints
                </h4>
                <p className="text-xs text-silver mt-1">
                  Specify host and camera stream endpoints (saved in browser):
                </p>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-silver mb-1">
                  Base Host Address:
                </label>
                <input
                  type="text"
                  value={inputBaseHost}
                  onChange={(e) => {
                    const h = e.target.value
                    setInputBaseHost(h)
                    const clean = h.trim().replace(/\/$/, '')
                    setInputRgbUrl(`${clean}/rgb_feed`)
                    setInputThermalUrl(`${clean}/thermal_feed`)
                  }}
                  placeholder="http://192.168.137.248:5003"
                  className="w-full rounded border border-white/20 bg-slate-950 px-3 py-1.5 text-xs font-mono text-snow focus:border-ice focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-mono text-silver mb-1">
                    RGB Stream URL:
                  </label>
                  <input
                    type="text"
                    value={inputRgbUrl}
                    onChange={(e) => setInputRgbUrl(e.target.value)}
                    placeholder="http://192.168.137.248:5003/rgb_feed"
                    className="w-full rounded border border-white/20 bg-slate-950 px-3 py-1.5 text-xs font-mono text-snow focus:border-ice focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-silver mb-1">
                    Thermal Stream URL:
                  </label>
                  <input
                    type="text"
                    value={inputThermalUrl}
                    onChange={(e) => setInputThermalUrl(e.target.value)}
                    placeholder="http://192.168.137.248:5003/thermal_feed"
                    className="w-full rounded border border-white/20 bg-slate-950 px-3 py-1.5 text-xs font-mono text-snow focus:border-ice focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-between items-center pt-2 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => {
                    setInputBaseHost(DEFAULT_BASE_HOST)
                    setInputRgbUrl(DEFAULT_RGB_URL)
                    setInputThermalUrl(DEFAULT_THERMAL_URL)
                  }}
                  className="text-[11px] text-sky hover:underline font-mono"
                >
                  Reset to default (192.168.137.248:5003)
                </button>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setIsEditingIp(false)}
                    className="rounded px-3 py-1.5 text-xs font-semibold text-silver hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="rounded bg-ice px-4 py-1.5 text-xs font-semibold text-white hover:bg-ice-deep"
                  >
                    Save & Connect
                  </button>
                </div>
              </div>
            </form>
          </div>
        )}

        {/* Bottom Telemetry Timestamp & Device Info */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-wrap items-center justify-between gap-2 px-5 pb-4 font-mono text-[10px] tracking-wide text-snow/75 sm:px-7 sm:pb-5 sm:text-[11px]">
          <span>
            Timestamp: <span className="text-snow">{frame.timestamp}</span>
          </span>
          <span>
            Device: <span className="text-snow">{showLiveStream ? `Bot Camera (${spectrumMode === 'Thermal' ? 'Thermal Feed' : 'RGB Feed'})` : frame.device}</span>
          </span>
        </div>
      </div>

      {/* Spectrum Mode Tabs */}
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div role="tablist" aria-label="Spectrum mode" className="relative flex rounded-sm border border-white/10 bg-white/5 p-1">
          {MODES.map((m) => {
            const selected = spectrumMode === m.id
            return (
              <button
                key={m.id}
                role="tab"
                aria-selected={selected}
                onClick={() => setSpectrumMode(m.id)}
                className={cn(
                  'relative flex-1 rounded-sm px-4 py-2 text-left transition-colors duration-300 sm:flex-none',
                  selected ? 'text-snow' : 'text-silver hover:text-frost',
                )}
              >
                {selected && (
                  <motion.span
                    layoutId="spectrum-pill"
                    className="absolute inset-0 rounded-sm border border-ice/30 bg-ice/15"
                    transition={{ type: 'spring', stiffness: 400, damping: 34 }}
                  />
                )}
                <span className="relative block text-sm font-semibold">{m.label}</span>
                <span className={cn('relative block font-mono text-[9px] tracking-wider', selected ? 'text-ice' : 'text-silver/70')}>
                  {m.hint}
                </span>
              </button>
            )
          })}
        </div>
        <p className="font-mono text-[10px] tracking-wider text-silver">{'Thermal envelope [-10°C, +3°C] · ε = 0.95'}</p>
      </div>
    </div>
  )
}
