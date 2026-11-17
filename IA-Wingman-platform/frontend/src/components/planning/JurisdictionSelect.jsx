import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Globe } from 'lucide-react'
import { getEngagement, updateEngagement } from '../../api/engagements'

// Audit-wide jurisdictions. One source of truth on the engagement, read by Topic
// Intelligence and both Frameworks apps. Keep in sync with backend VALID_JURISDICTIONS.
export const JURISDICTIONS = ['NL', 'BE', 'UK', 'ES', 'EU']

export default function JurisdictionSelect({ engagementId, compact = false }) {
  const qc = useQueryClient()
  const { data: eng } = useQuery({
    queryKey: ['engagement', engagementId],
    queryFn: () => getEngagement(engagementId),
    staleTime: 60_000,
  })
  const selected = eng?.jurisdictions || []

  const save = useMutation({
    mutationFn: (next) => updateEngagement(engagementId, { jurisdictions: next }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['engagement', engagementId] }),
  })

  const toggle = (code) => {
    const next = selected.includes(code)
      ? selected.filter((c) => c !== code)
      : [...selected, code]
    save.mutate(next)
  }

  return (
    <div>
      {!compact && (
        <div className="mb-2 flex items-center gap-2">
          <Globe size={14} className="text-brand" />
          <h2 className="text-xs font-semibold uppercase tracking-wide text-fg-muted">Jurisdictions</h2>
          <span className="text-xs text-fg-subtle">— which countries this audit covers</span>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {JURISDICTIONS.map((code) => {
          const active = selected.includes(code)
          return (
            <button
              key={code}
              type="button"
              onClick={() => toggle(code)}
              disabled={save.isPending}
              className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset transition disabled:opacity-60 ${
                active
                  ? 'bg-brand text-white ring-brand'
                  : 'bg-surface text-fg-muted ring-line hover:ring-brand/40'
              }`}
            >
              {code}
            </button>
          )
        })}
      </div>
      {selected.length === 0 && !compact && (
        <p className="mt-1.5 text-xs text-fg-subtle">
          None selected — the scan falls back to NL + EU. Pick the countries in scope for sharper results.
        </p>
      )}
    </div>
  )
}
