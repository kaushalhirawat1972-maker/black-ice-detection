export function SiteFooter() {
  return (
    <footer
      className="border-t border-white/30 px-5 py-8 sm:px-8"
      style={{ background: 'rgba(125, 195, 245, 0.45)', backdropFilter: 'blur(16px)' }}
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3 text-navy">
          <span className="font-display text-sm font-semibold">Black Ice Detection</span>
        </div>
        <p className="text-xs font-medium text-navy/70">YOLOv8 · MLX90640 · 2D LiDAR</p>
      </div>
    </footer>
  )
}
