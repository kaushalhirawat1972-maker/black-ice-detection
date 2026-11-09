'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, Droplets, Radar, ShieldCheck, Thermometer } from 'lucide-react'
import { STATUS_META, TONE_STYLES, VERIFICATION_TONE } from '@/lib/telemetry'
import { cn } from '@/lib/utils'
import { AnimatedNumber, TiltCard } from './motion-primitives'
import { useTelemetry } from './telemetry-provider'

const STATUS_ICON = { hazard: AlertTriangle, warn: Droplets, safe: CheckCircle2 }

function TileLabel({ children }: { children: React.ReactNode }) {
  return <p className="font-mono text-[10px] font-bold tracking-[0.14em] text-silver">{children}</p>
}

export function StatusBanner() {
  const { frame } = useTelemetry()
  const meta = STATUS_META[frame.road_status]
  const tone = TONE_STYLES[meta.tone]
  const Icon = STATUS_ICON[meta.tone]

  return (
    <TiltCard spot={meta.tone === 'safe' ? 'ice' : meta.tone} intensity={5} className="rounded-3xl">
      <motion.div
        animate={{ background: `linear-gradient(140deg, ${tone.hex}24 0%, rgba(19,49,92,0.55) 55%, rgba(7,23,44,0.7) 100%)` }}
        transition={{ duration: 0.8 }}
        className="relative h-full rounded-3xl border border-frost/10 p-5 shadow-[0_30px_60px_-28px_rgba(1,8,20,0.7)] backdrop-blur-xl"
      >
        <div className="flex items-center justify-between">
          <TileLabel>ROAD STATUS</TileLabel>
          <span className="relative flex size-3">
            <span className="absolute inset-0 animate-ping rounded-full opacity-60" style={{ background: tone.hex }} />
            <span className="relative size-3 rounded-full" style={{ background: tone.hex }} />
          </span>
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={frame.road_status}
            initial={{ opacity: 0, y: 12, filter: 'blur(6px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: -12, filter: 'blur(6px)' }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="mt-4"
          >
            <div className="flex items-center gap-3">
              <span
                className="grid size-11 shrink-0 place-items-center rounded-2xl text-navy"
                style={{ background: tone.hex, boxShadow: `0 10px 30px ${tone.hex}44` }}
              >
                <Icon className="size-5" aria-hidden />
              </span>
              <p className={cn('font-mono text-lg font-bold tracking-tight sm:text-xl', tone.text)}>{meta.label}</p>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-silver">{meta.description}</p>
          </motion.div>
        </AnimatePresence>
      </motion.div>
    </TiltCard>
  )
}

export function ConfidenceGauge() {
  const { frame } = useTelemetry()
  const tone = TONE_STYLES[STATUS_META[frame.road_status].tone]
  return (
    <TiltCard
      spot={frame.ice_confidence > 70 ? 'hazard' : frame.ice_confidence > 30 ? 'warn' : 'ice'}
      className="glass-dark rounded-3xl p-5"
    >
      <TileLabel>ICE CONFIDENCE</TileLabel>
      <div className="relative mx-auto mt-2 w-full max-w-[200px]">
        <svg viewBox="0 0 120 68" className="w-full" aria-hidden>
          <path d="M 10 62 A 50 50 0 0 1 110 62" fill="none" stroke="rgba(226,232,240,0.1)" strokeWidth="9" strokeLinecap="round" />
          <motion.path
            d="M 10 62 A 50 50 0 0 1 110 62"
            fill="none"
            strokeWidth="9"
            strokeLinecap="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: frame.ice_confidence / 100, stroke: tone.hex }}
            transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          />
        </svg>
        <div className="absolute inset-x-0 bottom-0 text-center">
          <p className="text-3xl font-extrabold tracking-tight text-snow">
            <AnimatedNumber value={frame.ice_confidence} />
            <span className="text-lg text-silver">%</span>
          </p>
        </div>
      </div>
      <p className="mt-2 text-center font-mono text-[10px] tracking-wider text-silver">YOLOv8 · P(ice)</p>
    </TiltCard>
  )
}

export function TemperatureTile() {
  const { frame } = useTelemetry()
  const inEnvelope = frame.surface_temp >= -10 && frame.surface_temp <= 3
  const pct = Math.min(100, Math.max(0, ((frame.surface_temp + 15) / 30) * 100))
  return (
    <TiltCard spot={inEnvelope ? 'warn' : 'ice'} className="glass-dark rounded-3xl p-5">
      <div className="flex items-center justify-between">
        <TileLabel>SURFACE TEMP</TileLabel>
        <Thermometer className="size-4 text-ice" aria-hidden />
      </div>
      <p className="mt-3 text-3xl font-extrabold tracking-tight text-snow">
        <AnimatedNumber value={frame.surface_temp} />
        <span className="ml-1 text-lg text-silver">°C</span>
      </p>
      <div className="relative mt-4 h-2 rounded-full bg-gradient-to-r from-sky-700 via-sky-300 to-warn">
        <div className="absolute inset-y-0 rounded-full border border-dashed border-frost/50" style={{ left: '16.7%', width: '43.3%' }} />
        <motion.span
          className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-frost bg-navy-2 shadow"
          animate={{ left: `${pct}%` }}
          transition={{ type: 'spring', stiffness: 120, damping: 18 }}
        />
      </div>
      <p className="mt-3 font-mono text-[10px] tracking-wider text-silver">
        {inEnvelope ? 'IN FREEZE ENVELOPE' : 'OUTSIDE ENVELOPE'} · MLX90640
      </p>
    </TiltCard>
  )
}

export function DistanceTile() {
  const { frame } = useTelemetry()
  const pct = Math.min(100, (frame.lidar_distance / 40) * 100)
  return (
    <TiltCard className="glass-dark rounded-3xl p-5" spot="ice">
      <div className="flex items-center justify-between">
        <TileLabel>LIDAR DISTANCE</TileLabel>
        <Radar className="size-4 text-ice" aria-hidden />
      </div>
      <p className="mt-3 text-3xl font-extrabold tracking-tight text-snow">
        <AnimatedNumber value={frame.lidar_distance} />
        <span className="ml-1 text-lg text-silver">m</span>
      </p>
      <div className="relative mt-4 h-6">
        <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-[repeating-linear-gradient(90deg,#475569_0_4px,transparent_4px_10px)]" />
        <span className="absolute left-0 top-1/2 size-2.5 -translate-y-1/2 rounded-full bg-frost" />
        <motion.div
          className="absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full bg-gradient-to-r from-ice-deep to-ice"
          animate={{ width: `${pct}%` }}
          transition={{ type: 'spring', stiffness: 100, damping: 20 }}
        />
        <motion.span
          className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ice shadow-[0_0_12px_#38bdf8]"
          animate={{ left: `${pct}%` }}
          transition={{ type: 'spring', stiffness: 100, damping: 20 }}
        />
      </div>
      <p className="mt-2 font-mono text-[10px] tracking-wider text-silver">0m — 40m MAX RANGE</p>
    </TiltCard>
  )
}

export function VerificationTile() {
  const { frame } = useTelemetry()
  const vTone = VERIFICATION_TONE[frame.verification_status]
  const tone = TONE_STYLES[vTone]
  return (
    <TiltCard spot={vTone === 'safe' ? 'ice' : vTone} className="glass-dark rounded-3xl p-5">
      <div className="flex items-center justify-between">
        <TileLabel>VERIFICATION</TileLabel>
        <ShieldCheck className="size-4 text-ice" aria-hidden />
      </div>
      <AnimatePresence mode="wait">
        <motion.span
          key={frame.verification_status}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ duration: 0.35 }}
          className={cn('mt-4 inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-mono text-[11px] font-bold', tone.bg, tone.border, tone.text)}
        >
          <span className={cn('size-1.5 rounded-full', tone.dot)} />
          {frame.verification_status}
        </motion.span>
      </AnimatePresence>
      <ul className="mt-4 grid grid-cols-2 gap-1.5">
        {['RGB', 'LiDAR'].map((s) => (
          <li key={s} className="rounded-lg border border-mint/15 bg-mint/10 py-1.5 text-center font-mono text-[10px] font-semibold text-mint">
            {s} ✓
          </li>
        ))}
      </ul>
    </TiltCard>
  )
}
