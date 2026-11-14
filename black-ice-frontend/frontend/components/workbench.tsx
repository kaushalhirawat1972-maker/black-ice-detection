'use client'

import { Pause, Play, Save } from 'lucide-react'
import { useState } from 'react'
import { Reveal } from './motion-primitives'
import { RoadViewport } from './road-viewport'
import { SectionHeading } from './section-heading'
import { ConfidenceGauge, DistanceTile, StatusBanner, TemperatureTile, VerificationTile } from './telemetry-tiles'
import { useTelemetry } from './telemetry-provider'

export function Workbench() {
  const { live, toggleLive, saveScan, source } = useTelemetry()
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    saveScan()
    setSaved(true)
    setTimeout(() => setSaved(false), 1600)
  }

  return (
    <section className="relative min-h-svh px-5 pb-28 pt-40 sm:px-8 lg:pt-36">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <SectionHeading
            eyebrow="Live workbench"
            title="Live road viewport"
            description="Forward camera feed with fused HUD overlays. Switch spectrum to inspect thermal anomalies or LiDAR specular dropout."
          />
          <Reveal className="flex gap-2" delay={0.1}>
            <button
              onClick={toggleLive}
              className="inline-flex items-center gap-2 rounded-sm border border-frost/15 bg-white/5 px-4 py-2.5 text-sm font-semibold text-frost backdrop-blur transition-all duration-300 hover:border-ice/50"
            >
              {live ? <Pause className="size-4" aria-hidden /> : <Play className="size-4" aria-hidden />}
              {live ? 'Pause stream' : 'Resume stream'}
              <span className="font-mono text-[10px] text-silver">{source === 'websocket' ? 'WS' : 'SIM'}</span>
            </button>
            <button
              onClick={handleSave}
              className="inline-flex items-center gap-2 rounded-sm bg-ice px-4 py-2.5 text-sm font-semibold text-navy transition-colors duration-200 hover:bg-ice-deep"
            >
              <Save className="size-4" aria-hidden />
              {saved ? 'Saved to history' : 'Save scan'}
            </button>
          </Reveal>
        </div>

        <div className="mt-10 grid gap-5 lg:grid-cols-12">
          <Reveal className="lg:col-span-8">
            <RoadViewport />
          </Reveal>
          <div className="grid gap-5 lg:col-span-4">
            <Reveal delay={0.1}>
              <StatusBanner />
            </Reveal>
            <Reveal delay={0.18}>
              <ConfidenceGauge />
            </Reveal>
          </div>
        </div>

        <div className="mt-5 grid gap-5 sm:grid-cols-3">
          <Reveal delay={0.05}>
            <TemperatureTile />
          </Reveal>
          <Reveal delay={0.12}>
            <DistanceTile />
          </Reveal>
          <Reveal delay={0.19}>
            <VerificationTile />
          </Reveal>
        </div>
      </div>
    </section>
  )
}
