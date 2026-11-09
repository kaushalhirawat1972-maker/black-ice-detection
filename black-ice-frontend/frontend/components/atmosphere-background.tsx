import Image from 'next/image'

export function AtmosphereBackground() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-navy">
      <Image src="/images/silk-bg.png" alt="" fill priority sizes="100vw" className="scale-110 object-cover opacity-30 mix-blend-luminosity" />
      <div className="absolute inset-0 bg-gradient-to-br from-navy/70 via-navy-2/80 to-navy/90" />
      <div className="absolute inset-0 bg-grid-ice [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_80%)]" />
      <div className="absolute -left-40 top-1/4 size-[520px] rounded-full bg-ice/10 blur-[140px]" />
      <div className="absolute -right-32 bottom-0 size-[480px] rounded-full bg-royal/60 blur-[140px]" />
    </div>
  )
}
