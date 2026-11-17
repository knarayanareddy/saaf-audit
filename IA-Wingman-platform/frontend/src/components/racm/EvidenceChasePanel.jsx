import { useQuery } from '@tanstack/react-query'
import { FolderSearch, Check, Clock } from 'lucide-react'
import { getEvidenceChase } from '../../api/racm'
import { Card } from '../ui/Card'

// Evidence / DRL chaser. Deterministic: matches each Document Request List item to
// the evidence captured in the spine and flags what is still outstanding, with a
// draft follow-up. No AI — it reads the DRL and evidence and compares them.
export default function EvidenceChasePanel({ engagementId }) {
  const { data, isPending } = useQuery({
    queryKey: ['evidence-chase', engagementId],
    queryFn: () => getEvidenceChase(engagementId),
  })

  const items = data?.items || []

  return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-subtle text-brand">
          <FolderSearch size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-fg">Evidence / DRL chaser</h3>
            <span className="rounded-full bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-fg-muted">deterministic</span>
          </div>
          <p className="mt-0.5 text-sm text-fg-muted">
            Matches every document request to the evidence in the matrix and flags what is still outstanding,
            with a draft follow-up for each gap.
          </p>
        </div>
        {data && (
          <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${data.outstanding > 0 ? 'bg-sev-med/10 text-sev-med' : 'bg-sev-low/10 text-sev-low'}`}>
            {data.outstanding} of {data.total} outstanding
          </span>
        )}
      </div>

      {isPending && <div className="mt-4 h-16 animate-pulse rounded-lg bg-surface-3" />}

      {data && (
        <div className="mt-4 space-y-2 border-t border-line pt-4">
          {items.map((it, i) => (
            <div key={i} className="flex items-start gap-2 rounded-lg bg-surface-2 px-3 py-2">
              <span className={`mt-0.5 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${it.outstanding ? 'bg-sev-med/10 text-sev-med' : 'bg-sev-low/10 text-sev-low'}`}>
                {it.outstanding ? <Clock size={11} /> : <Check size={11} />}
                {it.outstanding ? 'outstanding' : 'received'}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-sm text-fg">{it.document}</div>
                {it.matched_evidence && (
                  <div className="mt-0.5 text-caption text-fg-muted">
                    Matched to evidence {it.matched_evidence}
                    {/* A guess and a reference read the same on screen unless
                        one of them says so. The request records which needs it
                        settles, so most rows are the second kind. */}
                    {it.matched_by === 'keyword' && (
                      <span className="ml-1 rounded-full bg-sev-med/10 px-1.5 py-0.5 text-[10px] font-medium text-sev-med">
                        on shared words — check it
                      </span>
                    )}
                  </div>
                )}
                {it.followup && <div className="mt-0.5 text-caption italic text-fg-muted">{it.followup}</div>}
              </div>
            </div>
          ))}
          {items.length === 0 && <div className="text-sm text-fg-subtle">No document request list found for this engagement.</div>}
        </div>
      )}
    </Card>
  )
}
