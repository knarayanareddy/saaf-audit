// Hand-built radial gauge for a finding's grounding strength (0–100).
// Measures how much TRACEABLE SUPPORT exists — deliberately NOT whether the
// finding is correct. Theme-aware via rgb(var(--token)); colour tracks the band.

const BANDS = [
  { min: 70, stroke: 'rgb(var(--sev-low))', tint: 'rgb(var(--sev-low) / 0.12)' },
  { min: 40, stroke: 'rgb(var(--sev-med))', tint: 'rgb(var(--sev-med) / 0.12)' },
  { min: 0, stroke: 'rgb(var(--sev-high))', tint: 'rgb(var(--sev-high) / 0.12)' },
]

export default function DefensibilityMeter({ score = 0, label = '', size = 92, thickness = 9 }) {
  const clamped = Math.max(0, Math.min(100, score))
  const band = BANDS.find((b) => clamped >= b.min) || BANDS[BANDS.length - 1]
  const r = (size - thickness) / 2
  const c = 2 * Math.PI * r
  const len = (clamped / 100) * c

  return (
    <div className="flex flex-col items-center gap-1">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
        role="img"
        aria-label={`Grounding strength ${clamped} out of 100, ${label}`}
      >
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgb(var(--surface-3))" strokeWidth={thickness} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={band.stroke}
          strokeWidth={thickness}
          strokeDasharray={`${len} ${c - len}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 500ms cubic-bezier(0.4,0,0.2,1)' }}
        />
        <text x="50%" y="50%" className="rotate-90" style={{ transformOrigin: 'center' }} textAnchor="middle" dominantBaseline="central">
          <tspan x="50%" dy="-0.05em" style={{ fontSize: size * 0.3, fontWeight: 700, fill: 'rgb(var(--fg))' }}>{clamped}</tspan>
          <tspan x="50%" dy="1.35em" style={{ fontSize: size * 0.13, fill: 'rgb(var(--fg-subtle))', letterSpacing: '0.05em' }}>/ 100</tspan>
        </text>
      </svg>
      {label && (
        <span
          className="rounded-full px-2 py-0.5 text-[11px] font-semibold"
          style={{ color: band.stroke, background: band.tint }}
        >
          {label}
        </span>
      )}
    </div>
  )
}
