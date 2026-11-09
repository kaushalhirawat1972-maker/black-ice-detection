'use client'

import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'

const EASE = [0.16, 1, 0.3, 1] as const

export function Reveal({
  children,
  delay = 0,
  className,
  y = 28,
}: {
  children: React.ReactNode
  delay?: number
  className?: string
  y?: number
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y, filter: 'blur(8px)' }}
      whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.9, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  )
}

export function TiltCard({
  children,
  className,
  spot,
  intensity = 8,
}: {
  children: React.ReactNode
  className?: string
  spot?: 'warn' | 'hazard' | 'ice'
  intensity?: number
}) {
  const ref = useRef<HTMLDivElement>(null)
  const px = useMotionValue(0.5)
  const py = useMotionValue(0.5)
  const rotateX = useSpring(useTransform(py, [0, 1], [intensity, -intensity]), { stiffness: 180, damping: 18 })
  const rotateY = useSpring(useTransform(px, [0, 1], [-intensity, intensity]), { stiffness: 180, damping: 18 })
  const glareX = useTransform(px, (v) => `${v * 100}%`)
  const glareY = useTransform(py, (v) => `${v * 100}%`)
  const glare = useTransform(
    [glareX, glareY],
    ([x, y]) => `radial-gradient(420px circle at ${x} ${y}, rgba(186,230,253,0.12), transparent 60%)`,
  )

  const handleMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect) return
    px.set((e.clientX - rect.left) / rect.width)
    py.set((e.clientY - rect.top) / rect.height)
  }

  const reset = () => {
    px.set(0.5)
    py.set(0.5)
  }

  return (
    <div style={{ perspective: 1000 }} className="h-full">
      <motion.div
        ref={ref}
        data-spot={spot}
        onPointerMove={handleMove}
        onPointerLeave={reset}
        style={{ rotateX, rotateY, transformStyle: 'preserve-3d' }}
        whileHover={{ y: -4 }}
        transition={{ duration: 0.4, ease: EASE }}
        className={cn('relative h-full overflow-hidden', className)}
      >
        {children}
        <motion.div aria-hidden className="pointer-events-none absolute inset-0" style={{ background: glare }} />
      </motion.div>
    </div>
  )
}

export function AnimatedNumber({ value, decimals = 1, className }: { value: number; decimals?: number; className?: string }) {
  const spring = useSpring(value, { stiffness: 90, damping: 20 })
  const display = useTransform(spring, (v) => v.toFixed(decimals))

  useEffect(() => {
    spring.set(value)
  }, [spring, value])

  return <motion.span className={className}>{display}</motion.span>
}
