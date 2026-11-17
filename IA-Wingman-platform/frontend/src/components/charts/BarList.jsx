// Horizontal bar list — animated widths, optional click-through.
// Every bar shares one colour on purpose: the length already encodes the value,
// so a hue per category would add noise without adding information.
export default function BarList({ items = [], onItemClick }) {
  const max = Math.max(1, ...items.map((i) => i.value))
  return (
    <ul className="space-y-2.5">
      {items.map((item) => {
        const pct = Math.round((item.value / max) * 100)
        const Row = onItemClick ? 'button' : 'div'
        return (
          <li key={item.key}>
            <Row
              onClick={onItemClick ? () => onItemClick(item.key) : undefined}
              className={`group flex w-full items-center gap-3 text-left ${onItemClick ? 'cursor-pointer' : ''}`}
            >
              <span className="w-28 shrink-0 truncate text-sm text-fg-muted group-hover:text-fg">{item.label}</span>
              <span className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-surface-3">
                <span
                  className="absolute inset-y-0 left-0 rounded-full transition-[width] duration-500 ease-out"
                  style={{ width: `${pct}%`, background: 'rgb(var(--chart-3))' }}
                />
              </span>
              <span className="w-6 shrink-0 text-right text-sm font-semibold tabular-nums text-fg">{item.value}</span>
            </Row>
          </li>
        )
      })}
    </ul>
  )
}
