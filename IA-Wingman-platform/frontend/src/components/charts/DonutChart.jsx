// Hand-built SVG donut with a legend. Segments are clickable and accessible.
// Each segment brings its own `color` as a CSS colour string — pass a theme
// token (rgb(var(--chart-2))) rather than a hex so it follows light/dark.
export default function DonutChart({
  segments = [],
  size = 168,
  thickness = 18,
  centerValue,
  centerLabel,
  onSegmentClick,
}) {
  const total = segments.reduce((s, seg) => s + seg.value, 0) || 1
  const r = (size - thickness) / 2
  const c = 2 * Math.PI * r
  let offset = 0

  return (
    <div className="flex items-center gap-5">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0 -rotate-90" role="img" aria-label="Distribution">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgb(var(--surface-3))" strokeWidth={thickness} />
        {segments.map((seg) => {
          const frac = seg.value / total
          const len = frac * c
          const el = (
            <circle
              key={seg.key}
              cx={size / 2}
              cy={size / 2}
              r={r}
              fill="none"
              stroke={seg.color}
              strokeWidth={thickness}
              strokeDasharray={`${len} ${c - len}`}
              strokeDashoffset={-offset}
              strokeLinecap="butt"
              className={onSegmentClick ? 'cursor-pointer transition-[stroke-width] hover:[stroke-width:22]' : ''}
              onClick={onSegmentClick ? () => onSegmentClick(seg.key) : undefined}
            >
              <title>{`${seg.label}: ${seg.value}`}</title>
            </circle>
          )
          offset += len
          return el
        })}
        {centerValue !== undefined && (
          <text x="50%" y="50%" className="rotate-90" style={{ transformOrigin: 'center' }} textAnchor="middle" dominantBaseline="central">
            <tspan x="50%" dy="-0.1em" style={{ fontSize: size * 0.24, fontWeight: 700, fill: 'rgb(var(--fg))' }}>{centerValue}</tspan>
            {centerLabel && <tspan x="50%" dy="1.35em" style={{ fontSize: size * 0.09, fill: 'rgb(var(--fg-muted))' }}>{centerLabel}</tspan>}
          </text>
        )}
      </svg>

      <ul className="min-w-0 flex-1 space-y-1.5">
        {segments.map((seg) => (
          <li key={seg.key}>
            <button
              onClick={onSegmentClick ? () => onSegmentClick(seg.key) : undefined}
              className={`flex w-full items-center gap-2 rounded-md px-1.5 py-1 text-left text-sm ${onSegmentClick ? 'transition hover:bg-surface-3' : 'cursor-default'}`}
            >
              <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: seg.color }} />
              <span className="flex-1 truncate text-fg-muted">{seg.label}</span>
              <span className="font-semibold tabular-nums text-fg">{seg.value}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
