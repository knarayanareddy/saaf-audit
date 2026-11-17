export default function ProgressRing({ value = 0, size = 36, stroke = 4 }) {
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (value / 100) * circumference
  // Theme-aware: the empty-track and label colours come from CSS tokens so the
  // percentage stays readable in both light and dark mode. The tokens are
  // space-separated RGB triples, so they must be wrapped in rgb(). Green/amber legible on both.
  const color = value === 100 ? '#10B981' : value > 0 ? '#F59E0B' : 'rgb(var(--line-strong))'

  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgb(var(--line))" strokeWidth={stroke} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.4s ease' }}
      />
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        className="rotate-90"
        style={{ transformOrigin: 'center', fontSize: size * 0.28, fill: 'rgb(var(--fg))', fontWeight: 600 }}
      >
        {value}
      </text>
    </svg>
  )
}
