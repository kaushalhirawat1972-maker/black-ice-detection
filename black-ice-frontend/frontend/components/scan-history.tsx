'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { STATUS_META, TONE_STYLES, VERIFICATION_TONE, readable } from '@/lib/telemetry'
import { cn } from '@/lib/utils'
import { Reveal } from './motion-primitives'
import { SectionHeading } from './section-heading'
import { useTelemetry } from './telemetry-provider'

export function ScanHistory() {
  const { history } = useTelemetry()

  return (
    <section className="relative min-h-svh px-5 pb-28 pt-40 sm:px-8 lg:pt-36">
      <div className="mx-auto max-w-7xl">
        <SectionHeading
          eyebrow="Scan history"
          title="Saved session scans"
          description="Every snapshot captured from the workbench, with the fused decision and raw sensor readings that produced it."
        />

        <Reveal delay={0.1} className="mt-10">
          <div className="glass-dark overflow-hidden rounded-sm">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead>
                  <tr className="border-b border-white/10 bg-frost/5 text-xs text-silver">
                    {['Time', 'Road condition', 'Confidence', 'Surface temp', 'Distance', 'Status'].map((h) => (
                      <th key={h} scope="col" className="px-6 py-3 font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence initial={false}>
                    {history.map((row) => {
                      const meta = STATUS_META[row.road_status]
                      const tone = TONE_STYLES[meta.tone]
                      const vTone = TONE_STYLES[VERIFICATION_TONE[row.verification_status]]
                      return (
                        <motion.tr
                          key={row.id}
                          layout
                          initial={{ opacity: 0, backgroundColor: 'rgba(143,180,216,0.12)' }}
                          animate={{ opacity: 1, backgroundColor: 'rgba(143,180,216,0)' }}
                          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
                          data-spot={meta.tone === 'safe' ? 'ice' : meta.tone}
                          className="border-b border-frost/5 transition-colors duration-300 last:border-0 hover:!bg-ice/5"
                        >
                          <td className="px-6 py-4 font-mono text-xs text-frost">{row.timestamp}</td>
                          <td className="px-6 py-4">
                            <span className={cn('inline-flex items-center gap-2 text-sm', tone.text)}>
                              <span className={cn('size-1.5 rounded-full', tone.dot)} />
                              {meta.short}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <div className="h-1.5 w-20 overflow-hidden rounded-full bg-frost/10">
                                <div className="h-full rounded-full" style={{ width: `${row.ice_confidence}%`, background: tone.hex }} />
                              </div>
                              <span className="font-mono text-xs font-semibold text-frost">{row.ice_confidence.toFixed(1)}%</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 font-mono text-xs text-frost">{row.surface_temp.toFixed(1)} °C</td>
                          <td className="px-6 py-4 font-mono text-xs text-frost">{row.lidar_distance.toFixed(1)} m</td>
                          <td className="px-6 py-4">
                            <span className={cn('text-sm', vTone.text)}>{readable(row.verification_status)}</span>
                          </td>
                        </motion.tr>
                      )
                    })}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
