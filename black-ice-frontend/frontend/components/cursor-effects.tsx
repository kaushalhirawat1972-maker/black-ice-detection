'use client'

import { useEffect, useRef } from 'react'

const ICE = '56, 189, 248'
const YELLOW = '255, 209, 102'
const SPOT_COLORS: Record<string, string> = { ice: ICE, warn: YELLOW, hazard: '245, 180, 60' }
const INTERACTIVE = 'a, button, [role="tab"], [data-interactive]'

export function CursorEffects() {
  const spotRef = useRef<HTMLDivElement>(null)
  const rippleLayerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const spot = spotRef.current
    const layer = rippleLayerRef.current
    if (!spot || !layer) return

    let frame = 0
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const el = e.target as HTMLElement | null
        const interactive = el?.closest(INTERACTIVE)
        const spotEl = el?.closest<HTMLElement>('[data-spot]')
        const color = interactive ? YELLOW : (SPOT_COLORS[spotEl?.dataset.spot ?? 'ice'] ?? ICE)
        const strength = interactive ? 0.14 : 0.09
        spot.style.background = `radial-gradient(520px circle at ${e.clientX}px ${e.clientY}px, rgba(${color}, ${strength}), transparent 70%)`
        spot.style.opacity = '1'
      })
    }

    const onLeave = () => {
      spot.style.opacity = '0'
    }

    const onClick = (e: MouseEvent) => {
      if (reduce) return
      const ripple = document.createElement('span')
      ripple.className = 'pointer-events-none fixed rounded-full'
      Object.assign(ripple.style, {
        left: `${e.clientX - 24}px`,
        top: `${e.clientY - 24}px`,
        width: '48px',
        height: '48px',
        border: '1px solid rgba(186, 230, 253, 0.8)',
        background: 'radial-gradient(circle, rgba(56,189,248,0.3) 0%, rgba(226,232,240,0.12) 45%, transparent 72%)',
        backdropFilter: 'blur(3px) saturate(180%)',
        transform: 'scale(0.2)',
        opacity: '1',
        transition: 'transform 0.6s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.6s ease',
      })
      layer.appendChild(ripple)
      requestAnimationFrame(() => {
        ripple.style.transform = 'scale(3.6)'
        ripple.style.opacity = '0'
      })
      setTimeout(() => ripple.remove(), 650)
    }

    window.addEventListener('pointermove', onMove, { passive: true })
    document.documentElement.addEventListener('pointerleave', onLeave)
    window.addEventListener('click', onClick)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('pointermove', onMove)
      document.documentElement.removeEventListener('pointerleave', onLeave)
      window.removeEventListener('click', onClick)
    }
  }, [])

  return (
    <>
      <div ref={spotRef} aria-hidden className="pointer-events-none fixed inset-0 z-40 opacity-0 transition-opacity duration-300" />
      <div ref={rippleLayerRef} aria-hidden className="pointer-events-none fixed inset-0 z-50" />
    </>
  )
}
