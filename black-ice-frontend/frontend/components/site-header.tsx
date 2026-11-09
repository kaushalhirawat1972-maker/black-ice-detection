'use client'

import { motion } from 'framer-motion'
import { Radio, Snowflake } from 'lucide-react'
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
    <ul className={cn('flex items-center gap-1 rounded-full border border-frost/10 bg-navy/40 p-1', className)}>
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
                'relative z-10 flex items-baseline gap-2 rounded-full px-3.5 py-2 text-sm font-medium transition-colors duration-300',
                active ? 'text-snow' : 'text-silver hover:text-frost',
              )}
            >
              <span className="font-mono text-[10px] text-silver/70">{item.n}</span>
              {item.label}
            </a>
            {active && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-full border border-ice/25 bg-ice/10 shadow-[0_0_24px_-6px_rgba(56,189,248,0.5)]"
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
  const { connected } = useTelemetry()
  const { navigate } = useViewRouter()

  return (
    <motion.header
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
      className="fixed inset-x-0 top-0 z-30 w-full border-b border-frost/10 bg-navy/80 backdrop-blur-xl shadow-[0_4px_30px_rgba(1,8,20,0.5)]"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <a
          href="/"
          onClick={(e) => {
            e.preventDefault()
            navigate('home')
          }}
          className="flex items-center gap-3"
        >
          <span className="grid size-10 place-items-center rounded-xl border border-ice/30 bg-ice/10 text-ice shadow-[0_0_20px_-4px_rgba(56,189,248,0.6)]">
            <Snowflake className="size-5" aria-hidden />
          </span>
          <span className="flex flex-col leading-none">
            <span className="text-sm font-extrabold tracking-tight text-snow sm:text-base">BLACK ICE DETECTION</span>
            <span className="mt-1 font-mono text-[9px] font-semibold tracking-[0.2em] text-silver sm:text-[10px]">
              ROAD PERCEPTION INTELLIGENCE
            </span>
          </span>
        </a>

        <nav aria-label="Primary" className="hidden lg:block">
          <NavTabs layoutId="nav-active" />
        </nav>

        <div className="flex items-center gap-2">
          <span className="hidden items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-300 md:inline-flex">
            <span className="size-2 rounded-full bg-safe animate-pulse-ring" />
            Model Online
          </span>
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 font-mono text-[10px] font-bold tracking-wider',
              connected ? 'border-ice/30 bg-navy/50 text-frost' : 'border-warn/30 bg-warn/10 text-warn',
            )}
          >
            <Radio className={cn('size-3.5', connected ? 'text-ice' : 'text-warn')} aria-hidden />
            {connected ? 'LIVE STREAM' : 'PAUSED'}
          </span>
        </div>
      </div>

      <nav aria-label="Sections" className="mx-auto max-w-7xl px-4 pb-2.5 overflow-x-auto lg:hidden">
        <NavTabs layoutId="nav-active-mobile" className="w-max" />
      </nav>
    </motion.header>
  )
}
