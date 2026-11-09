'use client'

import { motion, useSpring } from 'framer-motion'
import { useEffect } from 'react'

const FACES = [
  'rotateY(0deg)',
  'rotateY(90deg)',
  'rotateY(180deg)',
  'rotateY(-90deg)',
  'rotateX(90deg)',
  'rotateX(-90deg)',
]

const OFFSETS = [-1, 0, 1]
const CELLS = OFFSETS.flatMap((x) => OFFSETS.flatMap((y) => OFFSETS.map((z) => ({ x, y, z })))).filter(
  (c) => !(c.x === 0 && c.y === 0 && c.z === 0),
)

function MiniCube({ x, y, z }: { x: number; y: number; z: number }) {
  const depth = (z + 1) / 2
  return (
    <div
      className="absolute left-1/2 top-1/2"
      style={{
        width: 'calc(var(--cube) * 0.17)',
        height: 'calc(var(--cube) * 0.17)',
        marginLeft: 'calc(var(--cube) * -0.085)',
        marginTop: 'calc(var(--cube) * -0.085)',
        transformStyle: 'preserve-3d',
        transform: `translate3d(calc(var(--cube) * ${0.25 * x}), calc(var(--cube) * ${0.25 * y}), calc(var(--cube) * ${0.25 * z}))`,
      }}
    >
      {FACES.map((rot, i) => (
        <span
          key={rot}
          className="absolute inset-0 rounded-[18%]"
          style={{
            transform: `${rot} translateZ(calc(var(--cube) * 0.085))`,
            background:
              i % 2 === 0
                ? `linear-gradient(145deg, rgba(125,211,252,${0.7 + depth * 0.2}), rgba(14,116,196,${0.62 + depth * 0.2}))`
                : `linear-gradient(145deg, rgba(56,189,248,${0.55 + depth * 0.2}), rgba(3,105,161,${0.6 + depth * 0.2}))`,
            boxShadow: 'inset 0 0 8px rgba(186,230,253,0.55)',
          }}
        />
      ))}
    </div>
  )
}

export function IceCube3D() {
  const tiltX = useSpring(0, { stiffness: 60, damping: 18 })
  const tiltY = useSpring(0, { stiffness: 60, damping: 18 })

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      tiltY.set((e.clientX / window.innerWidth - 0.5) * 30)
      tiltX.set(-(e.clientY / window.innerHeight - 0.5) * 22)
    }
    window.addEventListener('pointermove', onMove, { passive: true })
    return () => window.removeEventListener('pointermove', onMove)
  }, [tiltX, tiltY])

  return (
    <div
      className="relative animate-float [--cube:230px] sm:[--cube:340px] lg:[--cube:410px]"
      style={{ width: 'var(--cube)', height: 'var(--cube)', perspective: 1600 }}
      aria-hidden
    >
      <div
        className="absolute -inset-1/3 rounded-full blur-3xl"
        style={{ background: 'radial-gradient(circle, rgba(56,189,248,0.38), rgba(19,49,92,0.25) 50%, transparent 72%)' }}
      />
      <motion.div className="absolute inset-0" style={{ rotateX: tiltX, rotateY: tiltY, transformStyle: 'preserve-3d' }}>
        <div className="absolute inset-0" style={{ transformStyle: 'preserve-3d', animation: 'cube-spin 28s linear infinite' }}>
          {CELLS.map((c) => (
            <MiniCube key={`${c.x}${c.y}${c.z}`} {...c} />
          ))}
          {FACES.map((rot) => (
            <div
              key={rot}
              className="absolute inset-0 rounded-[24%]"
              style={{
                transform: `${rot} translateZ(calc(var(--cube) * 0.5))`,
                background:
                  'linear-gradient(150deg, rgba(186,230,253,0.26) 0%, rgba(56,189,248,0.08) 50%, rgba(186,230,253,0.18) 100%)',
                border: '1px solid rgba(186,230,253,0.4)',
                boxShadow:
                  'inset 0 0 50px rgba(186,230,253,0.22), inset 0 0 2px rgba(226,232,240,0.7), 0 0 40px rgba(56,189,248,0.15)',
              }}
            />
          ))}
        </div>
      </motion.div>
    </div>
  )
}
