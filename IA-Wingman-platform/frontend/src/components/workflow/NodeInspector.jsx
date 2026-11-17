import { X, Sparkles, Cpu, UserCheck, AlertTriangle, ArrowRight, Lock } from 'lucide-react'
import Button from '../ui/Button'
import { STATUS } from './WorkflowNode'
import { waitingOn } from '../../lib/workflowLayout'

function Agent({ node, compact }) {
  return (
    <div className={`flex items-center gap-2 ${compact ? 'text-xs' : 'text-sm'} text-fg`}>
      {node.ai
        ? <Sparkles size={compact ? 12 : 14} className="shrink-0 text-brand" />
        : <Cpu size={compact ? 12 : 14} className="shrink-0 text-fg-subtle" />}
      <span className="min-w-0">
        <span className="font-medium">{node.agent}</span>
        <span className="text-fg-muted">{node.ai ? ' · AI proposes' : ' · no AI'}</span>
      </span>
    </div>
  )
}

function Related({ title, nodes, live, onJump }) {
  if (!nodes.length) return null
  return (
    <div className="mt-4">
      <div className="text-caption text-fg-subtle">{title}</div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {nodes.map((n) => {
          const meta = live ? STATUS[n.status] : null
          const Icon = meta?.icon
          return (
            <button
              key={n.key}
              type="button"
              onClick={() => onJump(n.key)}
              className="inline-flex h-7 items-center gap-1.5 rounded-md border border-line bg-surface-2 px-2 text-xs text-fg transition-colors duration-150 hover:border-line-strong hover:bg-surface-3 focus:outline-none focus-visible:shadow-ring"
            >
              {Icon && <Icon size={11} className={meta.spin ? 'animate-spin' : ''} />}
              {n.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function NodeInspector({
  node, layout, wf, live, variant = 'panel', style, className = '', onOpen, onClose, onJump,
}) {
  const phase = wf.phases.find((p) => p.key === node.phase)
  const meta = live ? STATUS[node.status] : null
  const StatusIcon = meta?.icon
  const decisions = (wf.human_gates || []).filter((g) => g.stage === node.key)
  const waiting = live ? waitingOn(node, layout.byKey) : []
  const pending = live ? node.pending_decisions || 0 : 0
  const caption = `${phase?.label || ''}${node.companion ? ' · companion agent' : ''}`

  if (variant === 'popover') {
    return (
      <div
        role="tooltip"
        className="pointer-events-none absolute z-20 w-[288px] animate-scale-in rounded-xl border border-line bg-surface p-3.5 shadow-elevated"
        style={style}
      >
        <div className="text-caption text-fg-subtle">{caption}</div>
        <div className="mt-0.5 text-sm font-semibold text-fg">{node.label}</div>
        {meta && (
          <div className="mt-1.5 flex items-center gap-1.5 text-xs text-fg-muted">
            <StatusIcon size={12} className={meta.spin ? 'animate-spin' : ''} />
            <span className="font-medium text-fg">{meta.label}</span>
            {node.detail && <span className="truncate">· {node.detail}</span>}
          </div>
        )}
        <p className="mt-2 text-xs leading-5 text-fg-muted">{node.description}</p>
        <div className="mt-2.5 space-y-1.5 border-t border-line pt-2.5">
          <Agent node={node} compact />
          {decisions.map((d) => (
            <div key={d.key} className="flex items-center gap-2 text-xs text-brand">
              <UserCheck size={12} className="shrink-0" /> {d.label}
            </div>
          ))}
        </div>
        {pending > 0 && (
          <div className="mt-2 rounded-md bg-sev-med/10 px-2 py-1 text-xs font-medium text-sev-med">
            {pending} awaiting your decision
          </div>
        )}
        {waiting.length > 0 && (
          <div className="mt-2 text-xs text-fg-muted">Waiting on: <span className="font-medium text-fg">{waiting.join(', ')}</span></div>
        )}
        {live && node.status !== 'locked' && <div className="mt-2 text-[11px] text-fg-subtle">Click to open this step</div>}
      </div>
    )
  }

  const opensAfter = (node.gates || []).map((g) => layout.byKey[g.split(':')[0]]).filter(Boolean)
  const unlocks = layout.edges.filter((e) => e.from === node.key && e.kind !== 'assist').map((e) => layout.byKey[e.to])

  return (
    <div
      role="dialog"
      aria-labelledby="wf-inspector-title"
      className={`z-30 animate-scale-in rounded-2xl border border-line bg-surface p-5 shadow-elevated ${className}`}
      style={style}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-caption text-fg-subtle">{caption}</div>
          <h2 id="wf-inspector-title" className="mt-1 text-h3 text-fg">{node.label}</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close details"
          className="-mr-1 -mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-fg-subtle transition-colors duration-150 hover:bg-surface-3 hover:text-fg focus:outline-none focus-visible:shadow-ring"
        >
          <X size={15} />
        </button>
      </div>

      {meta && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className={`inline-flex h-5 items-center gap-1.5 rounded px-1.5 text-[11px] font-medium ${meta.chip}`}>
            <StatusIcon size={12} className={meta.spin ? 'animate-spin' : ''} /> {meta.label}
          </span>
          {node.detail && <span className="text-xs text-fg-muted">{node.detail}</span>}
        </div>
      )}

      <p className="mt-3 text-[13px] leading-6 text-fg-muted">{node.description}</p>

      <div className="mt-4 space-y-2 border-t border-line pt-4">
        <Agent node={node} />
        {decisions.map((d) => (
          <div key={d.key} className="flex items-start gap-2 text-[13px] text-fg-muted">
            <UserCheck size={14} className="mt-0.5 shrink-0" /> <span>{d.label}</span>
          </div>
        ))}
      </div>

      {pending > 0 && (
        <div className="mt-4 flex items-start gap-2 rounded-md bg-sev-med/10 px-2.5 py-2 text-[13px] text-sev-med">
          <AlertTriangle size={15} className="mt-0.5 shrink-0" />
          <span><span className="font-semibold">{pending}</span> AI proposal{pending === 1 ? '' : 's'} awaiting your decision</span>
        </div>
      )}
      {waiting.length > 0 && (
        <div className="mt-4 flex items-start gap-2 rounded-md bg-surface-3 px-2.5 py-2 text-[13px] text-fg-muted">
          <Lock size={15} className="mt-0.5 shrink-0" />
          <span>Waiting on <span className="font-medium text-fg">{waiting.join(', ')}</span></span>
        </div>
      )}

      <Related title="Opens after" nodes={opensAfter} live={live} onJump={onJump} />
      <Related title="Unlocks" nodes={unlocks} live={live} onJump={onJump} />

      <div className="mt-5">
        {live ? (
          node.status !== 'locked' ? (
            <Button className="w-full" onClick={() => onOpen(node)}>
              Open {node.label} <ArrowRight size={14} />
            </Button>
          ) : (
            <p className="text-xs text-fg-subtle">This step opens once what it waits on is done.</p>
          )
        ) : (
          <p className="text-xs text-fg-subtle">Choose an audit above to see its live status and open this step.</p>
        )}
      </div>
    </div>
  )
}
