import { Check, Loader2, ArrowRight, Lock, LockOpen, Circle, Sparkles } from 'lucide-react'

// Status is never colour alone: every state carries its own icon and label.
// Colour is rationed — green marks what is running or done (semantically active),
// amber marks the one gate that is waiting on you, everything else is neutral.
// A diagram of 26 nodes stops being readable the moment each one is tinted.
export const STATUS = {
  complete: {
    label: 'Complete', icon: Check,
    dot: 'text-brand',
    chip: 'bg-brand/10 text-brand',
    card: 'border-line',
  },
  in_progress: {
    label: 'In progress', icon: Loader2, spin: true,
    dot: 'text-brand',
    chip: 'bg-brand/10 text-brand',
    card: 'border-brand/45',
  },
  available: {
    label: 'Ready to start', icon: ArrowRight,
    dot: 'text-fg-muted',
    chip: 'bg-surface-3 text-fg-muted',
    card: 'border-line',
  },
  locked: {
    label: 'Locked', icon: Lock,
    dot: 'text-fg-subtle',
    chip: 'bg-surface-3 text-fg-subtle',
    card: 'border-line-subtle bg-surface-2',
  },
}

export const METHOD_META = {
  icon: Circle,
  dot: 'text-fg-subtle',
  card: 'border-line',
}

export default function WorkflowNode({
  node, live, isNext, gate, dimmed, focused, unlocking, delay, onSelect, onHover,
}) {
  const meta = live ? STATUS[node.status] || STATUS.available : METHOD_META
  const Icon = unlocking ? LockOpen : meta.icon
  const pending = live ? node.pending_decisions || 0 : 0
  const showProgress = live && node.progress > 0 && node.progress < 100
  const label = [
    node.label,
    live ? meta.label : null,
    live ? node.detail : node.description,
    pending ? `${pending} awaiting your decision` : null,
    gate ? `You decide: ${gate.label}` : null,
    isNext ? 'Next gate' : null,
  ].filter(Boolean).join('. ')

  return (
    <button
      type="button"
      data-node={node.key}
      aria-label={label}
      onClick={() => onSelect(node)}
      onMouseEnter={() => onHover(node.key)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(node.key)}
      onBlur={() => onHover(null)}
      className={`group absolute flex animate-fade-in-up items-start gap-2 rounded-lg border bg-surface px-2.5 py-2 text-left transition-[opacity,box-shadow,translate,border-color] duration-200 hover:border-line-strong focus:outline-none focus-visible:shadow-ring ${meta.card} ${
        isNext ? 'wf-glow' : ''
      } ${focused ? 'wf-focus border-brand/60' : ''} ${dimmed ? 'opacity-25' : 'opacity-100'}`}
      style={{ left: node.x, top: node.y, width: node.w, height: node.h, animationDelay: `${delay}ms` }}
    >
      <Icon
        size={13}
        className={`mt-px shrink-0 ${meta.dot} ${meta.spin && !unlocking ? 'animate-spin' : ''} ${unlocking ? 'wf-unlock' : ''}`}
      />
      <span className="min-w-0 flex-1">
        <span
          className="block overflow-hidden text-[12px] font-medium leading-[15px] tracking-[-0.004em] text-fg"
          style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}
        >
          {node.label}
        </span>
        <span className="mt-0.5 flex min-w-0 items-center gap-1 text-[10px] leading-[14px] text-fg-subtle">
          {/* The mark, not a chip: a filled spark means an AI agent drafts here. */}
          {node.ai && <Sparkles size={9} className="shrink-0 text-brand" />}
          <span className="truncate">{node.agent}</span>
        </span>
      </span>

      {isNext && (
        <span className="absolute -top-1.5 left-2.5 rounded bg-sev-med px-1 text-[9px] font-semibold uppercase leading-[14px] tracking-wide text-canvas">
          Next
        </span>
      )}
      {pending > 0 && (
        <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded bg-sev-med px-1 text-[10px] font-semibold tabular-nums leading-none text-canvas ring-2 ring-canvas">
          {pending}
        </span>
      )}
      {showProgress && (
        <span className="absolute inset-x-2.5 bottom-1 h-px overflow-hidden rounded-full bg-line">
          <span className="block h-full bg-brand transition-[width] duration-700" style={{ width: `${node.progress}%` }} />
        </span>
      )}
      {/* A human decision is an open diamond on the node's edge — the same mark the
          canvas draws on a gated edge, so the two read as one language. */}
      {gate && (
        <span
          title="You decide"
          className="absolute -bottom-1.5 right-2.5 h-2.5 w-2.5 rotate-45 border border-brand bg-surface"
        />
      )}
    </button>
  )
}
