'use client'

import { motion } from 'framer-motion'
import Image from 'next/image'
import { Reveal } from './motion-primitives'
import { SectionHeading } from './section-heading'

const STEPS = [
  {
    n: '01',
    title: 'Spectral Ingestion',
    body: 'RGB video, the 32×24 thermal IR grid and 2D LiDAR planar sweeps are ingested on a shared clock so every frame is aligned.',
  },
  {
    n: '02',
    title: 'Calibrated Thermal Screening',
    body: 'Surface temperature is emissivity-corrected and gated to the freeze window. Warm, wet asphalt is filtered out before inference ever runs.',
  },
  {
    n: '03',
    title: 'YOLOv8 Vision Inference',
    body: 'A YOLOv8 model fine-tuned on winter asphalt localizes glaze patches and outputs a per-box ice probability on the edge accelerator.',
  },
  {
    n: '04',
    title: 'LiDAR Specular Association',
    body: 'Smooth ice mirrors laser pulses away from the sensor. Zero-return sectors overlapping a vision box confirm the hazard and its exact range.',
  },
]

export function Architecture() {
  return (
    <section className="relative min-h-svh px-5 pb-28 pt-40 sm:px-8 lg:pt-36">
      <div className="mx-auto max-w-7xl">
        <SectionHeading
          eyebrow="System architecture"
          title="Four layers of certainty before a single alert"
          description="Every hazard passes a thermal gate, a neural detector and a geometric LiDAR check. Only when all agree does the de-icing actuator fire."
        />

        <div className="mt-14 grid gap-8 lg:grid-cols-[0.85fr_1.4fr]">
          <Reveal>
            <div className="overflow-hidden rounded-sm lg:sticky lg:top-28 shadow-xl">
              <div className="group relative aspect-[16/10] overflow-hidden lg:aspect-[4/5] rounded-sm">
                <Image
                  src="/images/black-ice-closeup.png"
                  alt="Close-up of transparent black ice glaze over dark asphalt"
                  fill
                  sizes="(min-width: 1024px) 36vw, 100vw"
                  className="object-cover transition-transform duration-[1.6s] ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-navy/70 via-transparent to-transparent" />
              </div>
            </div>
          </Reveal>

          <div className="relative">
            <motion.div
              aria-hidden
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
              className="absolute bottom-0 left-0 top-0 w-px origin-top bg-navy/15"
            />
            <ol className="relative">
              {STEPS.map((s, i) => (
                <li key={s.n}>
                  <Reveal delay={i * 0.08}>
                    <div className="relative grid gap-2 border-b border-navy/15 py-7 pl-8 sm:grid-cols-[4rem_1fr] sm:gap-6">
                      <span className="font-display text-2xl font-medium text-ice-deep">{s.n}</span>
                      <div className="min-w-0">
                        <h2 className="text-xl font-medium text-snow sm:text-2xl">{s.title}</h2>
                        <p className="mt-2 max-w-xl text-pretty leading-relaxed text-silver">{s.body}</p>
                      </div>
                    </div>
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
