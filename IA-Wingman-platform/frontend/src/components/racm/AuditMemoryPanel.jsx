import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  History, Loader2, Plus, Check, Sparkles, TriangleAlert, ShieldAlert, FileText, Scale,
} from 'lucide-react'
import { getRecall, adoptPrecedent, synthesizeMemory } from '../../api/memory'
import { Card } from '../ui/Card'
import ConfirmDialog from '../ui/ConfirmDialog'
import { useStore } from '../../store/useStore'

// Audit Memory — recalls topic-matched precedents from OTHER engagements so the
// auditor can reuse what prior audits found. Deterministic keyword recall; adopt
// writes a proposed node into the spine (propose, never decide).

const KIND = {
  risk: { label: 'Risk', Icon: TriangleAlert, cls: 'text-sev-high' },
  control: { label: 'Control', Icon: ShieldAlert, cls: 'text-sky-600 dark:text-sky-300' },
  finding: { label: 'Finding', Icon: FileText, cls: 'text-sev-med' },
  scope: { label: 'Scope', Icon: Scale, cls: 'text-violet-600 dark:text-violet-300' },
}

function PrecedentRow({ engagementId, item, onAdopted }) {
  const k = KIND[item.kind] || KIND.finding
  const Icon = k.Icon
  const [adopted, setAdopted] = useState(false)
  const adopt = useMutation({
    mutationFn: () => adoptPrecedent(engagementId, {
      ...item.adopt_payload,
      source_ref: `${item.source_engagement_name} · ${(item.kind || '').toUpperCase()}`,
    }),
    onSuccess: () => { setAdopted(true); onAdopted() },
  })

  return (
    <div className="flex items-start gap-3 rounded-lg border border-line px-3 py-2.5">
      <Icon size={15} className={`mt-0.5 shrink-0 ${k.cls}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-fg">{item.title}</span>
          {item.rating && <span className="rounded bg-surface-3 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-fg-muted">{item.rating}</span>}
        </div>
        {item.summary && <p className="mt-0.5 line-clamp-2 text-xs text-fg-muted">{item.summary}</p>}
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-fg-subtle">
          <span>from <span className="font-medium text-fg-muted">{item.source_engagement_name}</span> ({item.source_status?.replace(/_/g, ' ')})</span>
          <span>· match {item.score}</span>
          {item.shared?.length > 0 && <span>· {item.shared.join(', ')}</span>}
        </div>
      </div>
      {item.adoptable && (
        <button
          onClick={() => adopt.mutate()}
          disabled={adopt.isPending || adopted}
          className="mt-0.5 inline-flex shrink-0 items-center gap-1 rounded-lg border border-brand/30 px-2 py-1 text-xs font-medium text-brand transition hover:bg-brand-faint disabled:opacity-60"
        >
          {adopt.isPending ? <Loader2 size={12} className="animate-spin" /> : adopted ? <Check size={12} /> : <Plus size={12} />}
          {adopted ? 'Adopted' : 'Adopt'}
        </button>
      )}
    </div>
  )
}

export default function AuditMemoryPanel({ engagementId }) {
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [note, setNote] = useState(null)

  const { data, isPending } = useQuery({
    queryKey: ['memory-recall', engagementId],
    queryFn: () => getRecall(engagementId),
  })

  const synth = useMutation({
    mutationFn: () => synthesizeMemory(engagementId),
    onSuccess: (d) => { setConfirmOpen(false); setNote(d.summary) },
  })

  const onAdopted = () => {
    qc.invalidateQueries({ queryKey: ['racm', engagementId] })
    showToast('Precedent adopted as a proposal — review and accept it in the spine')
  }

  const items = data?.items || []

  return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-subtle text-brand">
          <History size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-fg">Audit Memory</h3>
            <span className="rounded-full bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-fg-muted">deterministic</span>
          </div>
          <p className="mt-0.5 text-sm text-fg-muted">
            What prior audits found on this topic — matched by keyword across your other engagements. Adopt a
            risk or control as a proposal; verify relevance before you accept it.
          </p>
        </div>
        {items.length > 0 && (
          <button
            onClick={() => setConfirmOpen(true)}
            disabled={synth.isPending}
            className="shrink-0 inline-flex items-center gap-1.5 rounded-lg border border-brand/30 px-3 py-1.5 text-sm font-medium text-brand transition hover:bg-brand-faint disabled:opacity-60"
          >
            {synth.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
            Summarise with AI
          </button>
        )}
      </div>

      {note && (
        <div className="mt-4 rounded-xl border border-brand/20 bg-brand-faint p-3 text-sm text-fg">
          <div className="mb-1 flex items-center gap-1.5 text-caption text-brand"><Sparkles size={12} /> Prior-audit summary</div>
          {note}
        </div>
      )}

      {isPending ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-fg-muted"><Loader2 size={14} className="animate-spin" /> Recalling precedents…</div>
      ) : items.length === 0 ? (
        <p className="mt-4 text-sm text-fg-muted">No prior-audit precedents matched this engagement's topic yet.</p>
      ) : (
        <div className="mt-4 space-y-2">
          {items.map((it, i) => (
            <PrecedentRow key={i} engagementId={engagementId} item={it} onAdopted={onAdopted} />
          ))}
        </div>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => synth.mutate()}
        title="Summarise prior audits with AI?"
        description="Writes a short note on what prior audits found on this topic, from the recalled precedents only. It uses AI budget and introduces no new facts."
        confirmLabel="Summarise — uses AI"
        loading={synth.isPending}
      />
    </Card>
  )
}
