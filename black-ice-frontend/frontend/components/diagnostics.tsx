'use client'

import { motion } from 'framer-motion'
import { Reveal } from './motion-primitives'
import { SectionHeading } from './section-heading'

const SENSORS = [
  {
    name: '1080p RGB Camera',
    status: 'Online',
    spec: '1920×1080 @ 30 FPS · 65° FOV',
    health: 98,
    bars: [6, 8, 7, 9, 8, 9, 10, 9, 8, 9, 10, 9],
  },
  {
    name: 'MLX90640 Thermal Sensor',
    status: 'Calibrated',
    spec: '32×24 IR Array · emissivity 0.95',
    health: 94,
    bars: [5, 6, 7, 6, 8, 7, 8, 9, 8, 7, 8, 9],
  },
  {
    name: '2D Planar LiDAR',
    status: 'Tracking',
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
          eyebrow="Sensor diagnostics"
          title="Hardware health, in real time"
          description="Each perception channel reports calibration and signal integrity continuously, so a degraded sensor never silently weakens a decision."
        />

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {SENSORS.map((s, i) => (
            <Reveal key={s.name} delay={i * 0.12}>
              <div className="glass-dark h-full p-6">
                <p className="text-xs text-safe">{s.status}</p>
                <h2 className="mt-2 text-lg font-medium text-snow">{s.name}</h2>
                <p className="mt-1 font-mono text-xs text-silver">{s.spec}</p>

                <div className="mt-6 flex h-12 items-end gap-1" aria-hidden>
                  {s.bars.map((h, j) => (
                    <motion.span
                      key={j}
                      className="flex-1 bg-ice-deep/70"
                      initial={{ height: 0 }}
                      animate={{ height: `${h * 10}%` }}
                      transition={{ duration: 0.8, delay: 0.3 + j * 0.04, ease: [0.16, 1, 0.3, 1] }}
                    />
                  ))}
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-navy/15 pt-4">
                  <span className="text-xs text-silver">Signal health</span>
                  <span className="text-sm font-medium text-snow">{s.health}%</span>
                </div>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.3} className="mt-5">
          <dl className="linen-card grid grid-cols-2 gap-6 rounded-sm p-6 sm:grid-cols-4">
            {SUMMARY.map((item) => (
              <div key={item.label}>
                <dt className="text-xs text-silver">{item.label}</dt>
                <dd className="mt-1.5 text-2xl font-medium text-snow">{item.value}</dd>
              </div>
            ))}
          </dl>
        </Reveal>
      </div>
    </section>
  )
}
