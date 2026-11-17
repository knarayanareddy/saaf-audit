import { Lock, LockOpen, UserCheck } from 'lucide-react'
import WorkflowNode from './WorkflowNode'
import NodeInspector from './NodeInspector'

// Theme tokens are RGB triples — they must be wrapped in rgb() inside SVG.
const STROKE = {
  lit: 'rgb(var(--brand))',
  done: 'rgb(var(--brand) / 0.5)',
  idle: 'rgb(var(--line-strong))',
  assist: 'rgb(var(--fg-subtle))',
}

export default function WorkflowCanvas({
  layout, wf, live, scale, activeKeys, highlightEdges, hoverKey, beat, particles, currentBand, onSelect, onHover,
}) {
  const gateByStage = Object.fromEntries((wf.human_gates || []).map((g) => [g.stage, g]))
  const focus = beat ? new Set(beat.focus) : null
  const unlocking = beat?.id === 'unlock'
  const hovered = !beat && hoverKey ? layout.byKey[hoverKey] : null
  const litEdges = layout.edges.filter((e) => highlightEdges?.has(e.id))

  return (
    <div className="relative mx-auto" style={{ width: layout.width * scale, height: layout.height * scale }}>
      <div
        className="absolute left-0 top-0 origin-top-left"
        style={{ width: layout.width, height: layout.height, transform: `scale(${scale})` }}
      >
        <svg
          className="absolute inset-0 overflow-visible"
          width={layout.width}
          height={layout.height}
          aria-hidden="true"
        >
          <defs>
            {[['wf-arrow', '--line-strong'], ['wf-arrow-lit', '--brand']].map(([id, token]) => (
              <marker key={id} id={id} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M0,0 L10,5 L0,10 z" style={{ fill: `rgb(var(${token}))` }} />
              </marker>
            ))}
          </defs>

          {layout.bands.map((b) => {
            const current = b.key === currentBand
            return (
              <rect
                key={b.key}
                x={b.x + 0.5}
                y={b.y + 0.5}
                width={b.w - 1}
                height={b.h - 1}
                rx="10"
                style={{
                  fill: current ? 'rgb(var(--brand-faint))' : 'rgb(var(--surface-2))',
                  stroke: current ? 'rgb(var(--brand) / 0.25)' : 'rgb(var(--line-subtle))',
                  transition: 'fill .3s, stroke .3s',
                }}
              />
            )
          })}

          {layout.edges.map((e) => {
            const lit = highlightEdges?.has(e.id)
            const from = layout.byKey[e.from]
            const to = layout.byKey[e.to]
            const done = live && from.status === 'complete' && to.status !== 'locked'
            const assist = e.kind === 'assist'
            const stroke = lit ? STROKE.lit : assist ? STROKE.assist : done ? STROKE.done : STROKE.idle
            return (
              <path
                key={e.id}
                d={e.path}
                fill="none"
                pathLength={assist ? undefined : 1}
                className={assist ? '' : 'wf-edge-draw'}
                markerEnd={assist ? undefined : `url(#${lit || done ? 'wf-arrow-lit' : 'wf-arrow'})`}
                style={{
                  stroke,
                  strokeWidth: lit ? 1.75 : e.kind === 'hard_gate' ? 1.5 : 1.25,
                  strokeDasharray: assist ? '4 4' : undefined,
                  opacity: activeKeys && !lit ? 0.2 : 1,
                  animationDelay: `${220 + to.bandIndex * 110}ms`,
                  transition: 'opacity .3s, stroke .3s, stroke-width .3s',
                }}
              />
            )
          })}

          {particles && litEdges.map((e, i) => (
            <g key={`${beat.id}-${e.id}`}>
              {[0, 0.9].map((offset) => (
                <circle key={offset} r="2.5" style={{ fill: 'rgb(var(--brand))', filter: 'drop-shadow(0 0 3px rgb(var(--brand) / 0.6))' }}>
                  {/* A negative begin starts mid-path, so a dot never flashes at the origin. */}
                  <animateMotion dur="1.8s" repeatCount="indefinite" begin={`-${(i * 0.23 + offset).toFixed(2)}s`} path={e.path} />
                </circle>
              ))}
            </g>
          ))}
        </svg>

        {layout.bands.map((b) => {
          const current = b.key === currentBand
          const bg = current ? 'bg-brand-faint' : 'bg-surface-2'
          return (
            <div
              key={b.key}
              className="pointer-events-none absolute flex max-w-full items-center gap-2"
              style={{ left: b.x + 20, top: b.y + 12, maxWidth: b.w - 40 }}
            >
              <span className={`pr-1.5 text-[10px] font-medium uppercase tracking-[0.07em] ${bg} ${current ? 'text-brand' : 'text-fg-muted'}`}>
                {b.label}
              </span>
              {current && (
                <span className="rounded bg-brand px-1 text-[9px] font-semibold uppercase leading-4 tracking-wide text-brand-fg">Current</span>
              )}
              {live && (
                <span className={`px-1 text-[10px] tabular-nums text-fg-subtle ${bg}`}>{b.done}/{b.total}</span>
              )}
              <span className={`truncate px-1 text-[10px] text-fg-subtle ${bg}`}>{b.summary}</span>
            </div>
          )
        })}

        {layout.edges.filter((e) => e.kind === 'hard_gate').map((e) => {
          const open = live && layout.byKey[e.to].status !== 'locked'
          const Icon = open || unlocking ? LockOpen : live ? Lock : UserCheck
          const tone = open || unlocking
            ? 'border-brand/35 bg-surface text-brand'
            : live
              ? 'border-sev-med/40 bg-surface text-sev-med'
              : 'border-line-strong bg-surface text-fg-muted'
          return (
            <div
              key={`gate-${e.id}`}
              className={`pointer-events-none absolute z-10 inline-flex h-5 -translate-x-1/2 -translate-y-1/2 items-center gap-1 whitespace-nowrap rounded border bg-surface px-1.5 text-[10px] font-medium transition-opacity duration-300 ${tone} ${
                activeKeys && !highlightEdges?.has(e.id) ? 'opacity-40' : ''
              }`}
              style={{ left: e.mid.x, top: e.mid.y }}
            >
              <Icon size={10} className={unlocking ? 'wf-unlock' : ''} />
              {open ? 'Signed off' : unlocking ? 'Unlocked by your sign-off' : 'Your sign-off'}
            </div>
          )
        })}

        {layout.nodes.map((n) => (
          <WorkflowNode
            key={n.key}
            node={n}
            live={live}
            isNext={live && wf.next_gate === n.key}
            gate={gateByStage[n.key]}
            dimmed={Boolean(activeKeys && !activeKeys.has(n.key))}
            focused={Boolean(focus?.has(n.key))}
            unlocking={unlocking && n.key === 'fieldwork'}
            delay={n.bandIndex * 110 + n.col * 40 + n.row * 15}
            onSelect={onSelect}
            onHover={onHover}
          />
        ))}

        {hovered && (
          <NodeInspector
            variant="popover"
            node={hovered}
            layout={layout}
            wf={wf}
            live={live}
            style={{
              left: hovered.x + hovered.w + 300 > layout.width ? hovered.x - 300 : hovered.x + hovered.w + 12,
              top: Math.max(0, hovered.y - 6),
            }}
          />
        )}
      </div>
    </div>
  )
}
