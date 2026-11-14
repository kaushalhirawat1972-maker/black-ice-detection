'use client'

import { AnimatePresence, motion } from 'framer-motion'
import Image from 'next/image'
import { STATUS_META, TONE_STYLES, type SpectrumMode } from '@/lib/telemetry'
import { cn } from '@/lib/utils'
import { useTelemetry } from './telemetry-provider'

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
  const meta = STATUS_META[frame.road_status]
  const tone = TONE_STYLES[meta.tone]
  const src = frame.image_base64
    ? (frame.image_base64.startsWith('data:') || frame.image_base64.startsWith('/') || frame.image_base64.startsWith('http'))
      ? frame.image_base64
      : `data:image/jpeg;base64,${frame.image_base64}`
    : '/images/road-feed.jpg'

  return (
    <div className="glass-dark rounded-sm p-3 sm:p-4" data-spot={meta.tone === 'safe' ? 'ice' : meta.tone}>
      <div className="relative aspect-video overflow-hidden rounded-sm bg-slate-900">
        <AnimatePresence mode="sync">
          <motion.div
            key={spectrumMode}
            initial={{ opacity: 0, scale: 1.04 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="absolute inset-0"
          >
            <Image
              src={src || '/placeholder.svg'}
              alt="Live forward road camera feed on a frosted highway at dusk"
              fill
              sizes="(min-width: 1024px) 66vw, 100vw"
              className="object-cover"
              style={{ filter: MODE_FILTER[spectrumMode] }}
              unoptimized={Boolean(frame.image_base64)}
              priority
            />
            {spectrumMode === 'Thermal' && (
              <>
                <div
                  className="absolute inset-0 mix-blend-color"
                  style={{ background: 'linear-gradient(to top, #fff3c4 0%, #ffd166 22%, #a7f3d0 45%, #38bdf8 70%, #0f172a 100%)' }}
                />
                {frame.bbox && (
                  <div
                    className="absolute rounded-[40%] blur-2xl"
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
                <div className="absolute inset-0 bg-ice/40 mix-blend-screen" />
                <div className="absolute inset-0 bg-slate-900/30" />
                <LidarFan />
              </>
            )}
          </motion.div>
        </AnimatePresence>

        <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[10%] animate-scan bg-gradient-to-b from-transparent via-ice/10 to-transparent" />
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-gradient-to-t from-slate-950/60 via-transparent to-slate-950/20" />
        <Reticles />

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
              className="absolute rounded-sm border-2"
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

        <div className="absolute left-5 top-5 flex items-center gap-2 sm:left-7 sm:top-7">
          <span className="inline-flex items-center gap-1.5 rounded-sm bg-warn/90 px-2 py-1 font-mono text-[10px] font-bold tracking-wider text-navy">
            <span className="size-1.5 animate-pulse rounded-full bg-snow" />
            REC
          </span>
          <span className="rounded-sm border border-ice/30 bg-slate-900/70 px-2 py-1 font-mono text-[10px] font-semibold tracking-wider text-ice backdrop-blur">
            {spectrumMode.toUpperCase()} · 30 FPS
          </span>
        </div>

        <div className="absolute inset-x-0 bottom-0 flex flex-wrap items-center justify-between gap-2 px-5 pb-4 font-mono text-[10px] tracking-wide text-snow/75 sm:px-7 sm:pb-5 sm:text-[11px]">
          <span>
            Timestamp: <span className="text-snow">{frame.timestamp}</span>
          </span>
          <span>
            Device: <span className="text-snow">{frame.device}</span>
          </span>
        </div>
      </div>

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
