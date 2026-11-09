'use client'

import { motion } from 'framer-motion'
import { Camera, Radar, Thermometer } from 'lucide-react'
import { Reveal, TiltCard } from './motion-primitives'
import { SectionHeading } from './section-heading'

const SENSORS = [
  {
    icon: Camera,
    name: '1080p RGB Camera',
    status: 'ONLINE',
    spec: '1920×1080 @ 30 FPS · 65° FOV',
    health: 98,
    bars: [6, 8, 7, 9, 8, 9, 10, 9, 8, 9, 10, 9],
  },
  {
    icon: Thermometer,
    name: 'MLX90640 Thermal Sensor',
    status: 'CALIBRATED',
    spec: '32×24 IR Array · Emissivity ε = 0.95',
    health: 94,
    bars: [5, 6, 7, 6, 8, 7, 8, 9, 8, 7, 8, 9],
  },
  {
    icon: Radar,
    name: '2D Planar LiDAR',
    status: 'TRACKING',
    spec: '120° Sector · 40m Max Range',
    health: 96,
    bars: [7, 9, 8, 6, 9, 10, 8, 9, 7, 10, 9, 8],
  },
]

const SUMMARY = [
  { label: 'Fusion uptime', value: '99.7%' },
  { label: 'Sync drift', value: '< 2 ms' },
  { label: 'Edge temp', value: '41 °C' },
  { label: 'Last calibration', value: '06:12' },
]

export function Diagnostics() {
  return (
    <section className="relative min-h-svh px-5 pb-28 pt-40 sm:px-8 lg:pt-36">
      <div className="mx-auto max-w-7xl">
        <SectionHeading
          eyebrow="03 · SENSOR DIAGNOSTICS"
          title="Hardware health, in real time"
          description="Each perception channel reports calibration and signal integrity continuously, so a degraded sensor never silently weakens a decision."
        />

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {SENSORS.map((s, i) => (
            <Reveal key={s.name} delay={i * 0.12}>
              <TiltCard spot="ice" className="glass-dark rounded-3xl p-6">
                <div className="flex items-start justify-between">
                  <span className="grid size-12 place-items-center rounded-2xl border border-ice/30 bg-ice/10 text-ice">
                    <s.icon className="size-5" aria-hidden />
                  </span>
                  <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 font-mono text-[10px] font-bold tracking-wider text-emerald-300">
                    <span className="size-1.5 rounded-full bg-safe animate-pulse-ring" />
                    {s.status}
                  </span>
                </div>
                <h2 className="mt-6 text-lg font-semibold text-snow">{s.name}</h2>
                <p className="mt-1 font-mono text-xs text-silver">{s.spec}</p>

                <div className="mt-6 flex h-12 items-end gap-1" aria-hidden>
                  {s.bars.map((h, j) => (
                    <motion.span
                      key={j}
                      className="flex-1 rounded-sm bg-gradient-to-t from-ice/30 to-ice"
                      initial={{ height: 0 }}
                      animate={{ height: `${h * 10}%` }}
                      transition={{ duration: 0.8, delay: 0.3 + j * 0.04, ease: [0.16, 1, 0.3, 1] }}
                    />
                  ))}
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-frost/10 pt-4">
                  <span className="font-mono text-[10px] tracking-[0.14em] text-silver">SIGNAL HEALTH</span>
                  <span className="text-sm font-bold text-mint">{s.health}%</span>
                </div>
              </TiltCard>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.3} className="mt-5">
          <dl className="linen-card grid grid-cols-2 gap-6 rounded-3xl p-6 sm:grid-cols-4">
            {SUMMARY.map((item) => (
              <div key={item.label}>
                <dt className="font-mono text-[10px] font-bold tracking-[0.16em] text-ice-deep">{item.label.toUpperCase()}</dt>
                <dd className="mt-1.5 text-2xl font-semibold tracking-tight text-navy-2">{item.value}</dd>
              </div>
            ))}
          </dl>
        </Reveal>
      </div>
    </section>
  )
}
