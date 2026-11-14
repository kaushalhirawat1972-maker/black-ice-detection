'use client'

import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { useTelemetry } from './telemetry-provider'
import { useViewRouter, type ViewId } from './view-router'

const NAV: { id: ViewId; n: string; label: string }[] = [
  { id: 'workbench', n: '01', label: 'Workbench' },
  { id: 'architecture', n: '02', label: 'Architecture' },
  { id: 'diagnostics', n: '03', label: 'Diagnostics' },
  { id: 'history', n: '04', label: 'Scan History' },
]

function NavTabs({ layoutId, className }: { layoutId: string; className?: string }) {
  const { view, navigate } = useViewRouter()
  return (
    <ul className={cn('flex items-center gap-7', className)}>
      {NAV.map((item) => {
        const active = view === item.id
        return (
          <li key={item.id} className="relative shrink-0">
            <a
              href={`#${item.id}`}
              aria-current={active ? 'page' : undefined}
              onClick={(e) => {
                e.preventDefault()
                navigate(item.id)
              }}
              className={cn(
                'relative z-10 flex items-baseline gap-2 rounded-sm px-3.5 py-2 text-sm font-medium transition-colors duration-300',
                active ? 'text-snow' : 'text-silver hover:text-frost',
              )}
            >
                            {item.label}
            </a>
            {active && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-x-0 bottom-0 h-0.5 bg-ice"
                transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              />
            )}
          </li>
        )
      })}
    </ul>
  )
}

export function SiteHeader() {
  const { connected, live } = useTelemetry()
  const { navigate } = useViewRouter()

  return (
    <motion.header
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
      className="glass-nav fixed inset-x-0 top-0 z-30"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-5 sm:px-8">
        <a
          href="/"
          onClick={(e) => {
            e.preventDefault()
            navigate('home')
          }}
          className="py-4 font-display text-base font-semibold text-snow"
        >
          Black Ice Detection
        </a>

        <nav aria-label="Primary" className="hidden lg:block">
          <NavTabs layoutId="nav-active" />
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <span
            className={cn(
              'size-2.5 rounded-full',
              !live ? 'bg-amber-500' : connected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'
            )}
          />
          <p className="text-xs font-medium text-navy/80">
            {!live ? 'Model Paused' : connected ? 'Model Active (Live Stream)' : 'Model Sample Demonstration'}
          </p>
        </div>
      </div>

      <nav aria-label="Sections" className="mx-auto max-w-7xl overflow-x-auto border-t border-white/5 px-5 lg:hidden">
        <NavTabs layoutId="nav-active-mobile" className="w-max" />
      </nav>
    </motion.header>
  )
}
