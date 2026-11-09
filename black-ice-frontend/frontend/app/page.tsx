import { Architecture } from '@/components/architecture'
import { AtmosphereBackground } from '@/components/atmosphere-background'
import { CursorEffects } from '@/components/cursor-effects'
import { Diagnostics } from '@/components/diagnostics'
import { Hero } from '@/components/hero'
import { ScanHistory } from '@/components/scan-history'
import { SiteFooter } from '@/components/site-footer'
import { SiteHeader } from '@/components/site-header'
import { TelemetryProvider } from '@/components/telemetry-provider'
import { ViewRouterProvider, ViewStage } from '@/components/view-router'
import { Workbench } from '@/components/workbench'

export default function Page() {
  return (
    <TelemetryProvider>
      <ViewRouterProvider>
        <AtmosphereBackground />
        <CursorEffects />
        <SiteHeader />
        <main className="overflow-x-clip">
          <ViewStage
            views={{
              home: <Hero />,
              workbench: <Workbench />,
              architecture: <Architecture />,
              diagnostics: <Diagnostics />,
              history: <ScanHistory />,
            }}
          />
        </main>
        <SiteFooter />
      </ViewRouterProvider>
    </TelemetryProvider>
  )
}
