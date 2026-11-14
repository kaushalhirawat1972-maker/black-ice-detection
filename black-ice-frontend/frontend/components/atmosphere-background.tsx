export function AtmosphereBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10"
      style={{
        backgroundImage: "url('/images/sky-bg.png')",
        backgroundSize: 'cover',
        backgroundPosition: 'center top',
        backgroundRepeat: 'no-repeat',
      }}
    >
      {/* soft white overlay so text stays readable */}
      <div className="absolute inset-0" style={{ background: 'rgba(255,255,255,0.18)' }} />
    </div>
  )
}
