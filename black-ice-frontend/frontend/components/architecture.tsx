'use client'

import { motion } from 'framer-motion'
import { Layers, Radar, ScanEye, Thermometer } from 'lucide-react'
import Image from 'next/image'
import { Reveal, TiltCard } from './motion-primitives'
import { SectionHeading } from './section-heading'

const STEPS = [
  {
    n: '01',
    icon: Layers,
    title: 'Spectral Ingestion',
    body: 'RGB video, the 32×24 thermal IR grid and 2D LiDAR planar sweeps are ingested on a shared clock so every frame is aligned.',
    chips: ['1080p RGB', '32×24 IR', 'LiDAR @ 30Hz'],
  },
  {
    n: '02',
    icon: Thermometer,
    title: 'Calibrated Thermal Screening',
    body: 'Surface temperature is emissivity-corrected and gated to the freeze window. Warm, wet asphalt is filtered out before inference ever runs.',
    chips: ['[-10°C, +3°C] window', 'ε = 0.95', 'WARM_SURFACE_FILTERED'],
  },
  {
    n: '03',
    icon: ScanEye,
    title: 'YOLOv8 Vision Inference',
    body: 'A YOLOv8 model fine-tuned on winter asphalt localizes glaze patches and outputs a per-box ice probability on the edge accelerator.',
    chips: ['YOLOv8n', 'P(ice) ≥ 0.80', '~38 ms'],
  },
  {
    n: '04',
    icon: Radar,
    title: 'LiDAR Specular Association',
    body: 'Smooth ice mirrors laser pulses away from the sensor. Zero-return sectors overlapping a vision box confirm the hazard and its exact range.',
    chips: ['Zero-return', 'Azimuth association', 'CONFIRMED_HAZARD'],
  },
]

export function Architecture() {
  return (
    <section className="relative min-h-svh px-5 pb-28 pt-40 sm:px-8 lg:pt-36">
      <div className="mx-auto max-w-7xl">
        <SectionHeading
          eyebrow="02 · SYSTEM ARCHITECTURE"
          title="Four layers of certainty before a single alert"
          description="Every hazard passes a thermal gate, a neural detector and a geometric LiDAR check. Only when all agree does the de-icing actuator fire."
        />

        <div className="mt-14 grid gap-8 lg:grid-cols-[0.85fr_1.4fr]">
          <Reveal>
            <div className="glass-dark rounded-[2rem] p-3 lg:sticky lg:top-28">
              <div className="group relative aspect-[16/10] overflow-hidden lg:aspect-[4/5] rounded-[1.6rem]">
                <Image
                  src="/images/black-ice-closeup.png"
                  alt="Close-up of transparent black ice glaze over dark asphalt"
                  fill
                  sizes="(min-width: 1024px) 36vw, 100vw"
                  className="object-cover transition-transform duration-[1.6s] ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-navy/80 via-navy/10 to-transparent" />
                <div className="absolute inset-x-4 bottom-4 rounded-2xl border border-frost/15 bg-navy/45 p-4 backdrop-blur-md">
                  <p className="font-mono text-[10px] font-bold tracking-[0.25em] text-ice">SPECULAR GLAZE</p>
                  <p className="mt-1.5 text-lg font-semibold text-snow">0.3 mm of ice, invisible to the eye</p>
                  <p className="mt-1 text-sm leading-relaxed text-silver">
                    Dark asphalt shows through — only multi-sensor fusion reveals it.
                  </p>
                </div>
              </div>
            </div>
          </Reveal>

          <div className="relative">
            <motion.div
              aria-hidden
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
              className="absolute bottom-8 left-[3.75rem] top-8 hidden w-px origin-top bg-gradient-to-b from-ice/0 via-ice/60 to-ice/0 sm:block"
            />
            <ol className="relative grid gap-5">
              {STEPS.map((s, i) => (
                <li key={s.n}>
                  <Reveal delay={i * 0.08}>
                    <TiltCard spot="ice" intensity={4} className="linen-card rounded-[2rem]">
                      <div className="flex gap-5 p-6 sm:p-7">
                        <span className="grid size-14 shrink-0 place-items-center rounded-full bg-navy-2 text-frost shadow-lg shadow-navy/30">
                          <s.icon className="size-5" aria-hidden />
                        </span>
                        <div className="min-w-0">
                          <p className="font-mono text-[11px] font-bold tracking-[0.2em] text-ice-deep">STEP {s.n}</p>
                          <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-navy-2 sm:text-2xl">{s.title}</h2>
                          <p className="mt-3 text-pretty text-sm leading-relaxed text-slate-600 sm:text-base">{s.body}</p>
                          <ul className="mt-5 flex flex-wrap gap-2">
                            {s.chips.map((c) => (
                              <li
                                key={c}
                                className="rounded-full border border-navy-2/15 bg-white/50 px-3 py-1 font-mono text-[11px] text-navy-2"
                              >
                                {c}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </TiltCard>
                  </Reveal>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </section>
  )
}
