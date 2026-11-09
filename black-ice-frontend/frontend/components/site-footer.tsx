import { Snowflake } from 'lucide-react'

export function SiteFooter() {
  return (
    <footer className="border-t border-frost/10 bg-navy/60 px-5 py-10 backdrop-blur sm:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3 text-frost">
          <Snowflake className="size-5 text-ice" aria-hidden />
          <span className="text-sm font-semibold">BLACK ICE DETECTION</span>
          <span className="font-mono text-[10px] tracking-[0.16em] text-silver">ROAD PERCEPTION INTELLIGENCE</span>
        </div>
        <p className="font-mono text-[11px] text-silver">YOLOv8 · MLX90640 · 2D LiDAR · Precision De-icing</p>
      </div>
    </footer>
  )
}
