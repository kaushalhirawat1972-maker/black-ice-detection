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
    <Reveal className="max-w-2xl border-l-2 border-ice-deep pl-5">
      <p className="text-sm font-medium text-ice">{eyebrow}</p>
      <h1 className="mt-2 text-balance text-3xl font-semibold text-snow sm:text-4xl">{title}</h1>
      <p className="mt-3 text-pretty leading-relaxed text-silver">{description}</p>
    </Reveal>
  )
}
