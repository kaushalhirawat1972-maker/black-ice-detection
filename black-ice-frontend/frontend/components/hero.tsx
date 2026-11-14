'use client'

import { motion, useScroll, useSpring, useTransform } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { useRef } from 'react'
import { IceCube3D } from './ice-cube-3d'
import { Reveal } from './motion-primitives'
import { useViewRouter, type ViewId } from './view-router'

const EASE = [0.16, 1, 0.3, 1] as const

const MODULES: { id: ViewId; n: string; title: string; body: string }[] = [
  { id: 'workbench', n: '01', title: 'Workbench', body: 'Live road viewport with fused HUD and the decision matrix.' },
  { id: 'architecture', n: '02', title: 'Architecture', body: 'How four perception layers agree before an alert fires.' },
  { id: 'diagnostics', n: '03', title: 'Diagnostics', body: 'Calibration and signal health for every sensor channel.' },
  { id: 'history', n: '04', title: 'Scan History', body: 'Saved session snapshots with raw sensor readings.' },
]

export function Hero() {
  const ref = useRef<HTMLElement>(null)
  const { navigate } = useViewRouter()
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] })
  const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 30, mass: 0.4 })

  const textScale = useTransform(progress, [0, 1], [1, 1.28])
  const cubeScale = useTransform(progress, [0, 1], [1, 0.5])
  const cubeOpacity = useTransform(progress, [0, 1], [1, 0.35])
  const cubeY = useTransform(progress, [0, 1], ['0%', '-8%'])
  const detailOpacity = useTransform(progress, [0, 0.35], [1, 0])
  const detailY = useTransform(progress, [0, 0.35], [0, 40])

  return (
    <>
      <section ref={ref} aria-labelledby="hero-title" className="relative h-[230vh]">
        <div className="sticky top-0 flex h-svh flex-col overflow-hidden">
          <motion.div
            aria-hidden
            style={{ scale: cubeScale, opacity: cubeOpacity, y: cubeY }}
            className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center pt-20"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.75 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1.6, ease: EASE, delay: 0.1 }}
            >
              <IceCube3D />
            </motion.div>
          </motion.div>

          <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-1 flex-col px-5 pb-8 pt-36 sm:px-8 lg:pt-32">
            <div className="flex flex-1 items-center justify-center">
              <motion.h1
                id="hero-title"
                style={{ scale: textScale }}
                className="text-center text-[clamp(3rem,9.5vw,8.5rem)] font-semibold leading-[0.95] tracking-tight text-navy"
              >
                <motion.span
                  initial={{ opacity: 0, y: 40, filter: 'blur(12px)' }}
                  animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                  transition={{ duration: 1.2, ease: EASE, delay: 0.3 }}
                  className="block text-navy"
                >
                  See the invisible
                </motion.span>
                <motion.span
                  initial={{ opacity: 0, y: 40, filter: 'blur(12px)' }}
                  animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                  transition={{ duration: 1.2, ease: EASE, delay: 0.45 }}
                  className="block text-navy"
                >
                  black ice
                </motion.span>
              </motion.h1>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: EASE, delay: 0.7 }}
              style={{ opacity: detailOpacity, y: detailY }}
              className="flex justify-end"
            >
              <button
                onClick={() => navigate('workbench')}
                className="group inline-flex items-center gap-2 rounded-sm bg-ice px-6 py-3 text-sm font-semibold text-navy transition-colors duration-200 hover:bg-ice-deep"
              >
                Open Workbench
                <ArrowRight className="size-4 transition-transform duration-300 group-hover:translate-x-0.5" aria-hidden />
              </button>
            </motion.div>
          </div>
        </div>
      </section>

      <section aria-labelledby="modules-title" className="relative px-5 pb-32 pt-40 sm:px-8">
        <div className="mx-auto max-w-7xl">
          <Reveal className="max-w-2xl">
            <p className="text-sm font-medium text-ice">Explore the system</p>
            <h2 id="modules-title" className="mt-4 text-balance text-3xl font-semibold text-snow sm:text-4xl">
              Four modules, one confident decision
            </h2>
          </Reveal>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {MODULES.map((m, i) => (
              <Reveal key={m.id} delay={i * 0.08}>
                <div className="glass-dark h-full transition-colors duration-200 hover:border-ice/40">
                  <button onClick={() => navigate(m.id)} className="group flex h-full w-full flex-col p-6 text-left">
                    <div className="flex items-center justify-between">
                      <span className="font-display text-sm text-ice-deep">{m.n}</span>
                    </div>
                    <h3 className="mt-4 text-xl font-medium text-snow">{m.title}</h3>
                    <p className="mt-2 flex-1 text-sm leading-relaxed text-silver">{m.body}</p>
                    <span className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-ice">
                      Open
                      <ArrowRight className="size-4 transition-transform duration-300 group-hover:translate-x-1" aria-hidden />
                    </span>
                  </button>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
