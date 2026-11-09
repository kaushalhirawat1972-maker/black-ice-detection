import { Reveal } from './motion-primitives'

export function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string
  title: string
  description: string
}) {
  return (
    <Reveal className="max-w-2xl">
      <p className="flex items-center gap-3 font-mono text-[11px] font-bold tracking-[0.2em] text-ice">
        <span className="h-px w-8 bg-ice" />
        {eyebrow}
      </p>
      <h1 className="mt-4 text-balance text-4xl font-semibold tracking-[-0.04em] text-snow sm:text-5xl">{title}</h1>
      <p className="mt-4 text-pretty leading-relaxed text-silver">{description}</p>
    </Reveal>
  )
}
