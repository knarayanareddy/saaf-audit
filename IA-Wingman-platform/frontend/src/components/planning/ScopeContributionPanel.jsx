/**
 * ScopeContributionPanel — reusable panel that appears at the bottom of planning
 * modules (BRA, Kickoff) to publish scope items → Scope & Objectives.
 *
 * Props:
 *   engagementId: string
 *   generateFn: () => Promise<{scope_items, key_questions}>
 *   getStoredFn: () => Promise<{scope_items, key_questions}>
 *   publishFn: (payload) => Promise<{scope_items_added, questions_added}>
 *   onPublished: () => void   (optional, called after successful publish)
 */
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Sparkles, Check, ChevronRight } from 'lucide-react'
import { useStore } from '../../store/useStore'

const TYPE_BADGE = {
  in_scope: 'bg-sev-low/10 text-sev-low border-sev-low/25',
  out_of_scope: 'bg-sev-high/10 text-sev-high border-sev-high/25',
  key_question: 'bg-blue-50 text-blue-700 border-blue-200',
}
const TYPE_LABEL = {
  in_scope: 'IN SCOPE',
  out_of_scope: 'OUT OF SCOPE',
  key_question: 'KEY Q',
}

function ContributionItem({ item, type, selected, onToggle }) {
  const badge = TYPE_BADGE[type] || TYPE_BADGE.in_scope
  const label = TYPE_LABEL[type] || type.toUpperCase()
  const text = item.description || item.question_text || ''
  const basis = item.rationale || item.regulatory_basis || ''

  return (
    <div
      className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition-opacity ${
        selected ? 'border-line bg-surface' : 'border-line bg-surface-3 opacity-50'
      }`}
      onClick={onToggle}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={onToggle}
        onClick={(e) => e.stopPropagation()}
        className="mt-0.5 h-4 w-4 rounded border-line-strong text-brand"
      />
      <div className="flex-1 min-w-0">
        <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${badge} mb-1`}>
          {label}
        </span>
        <p className="text-sm text-fg">{text}</p>
        {basis && <p className="mt-0.5 text-xs text-fg-subtle">{basis}</p>}
      </div>
    </div>
  )
}

export default function ScopeContributionPanel({
  engagementId,
  generateFn,
  getStoredFn,
  publishFn,
  onPublished,
  queryKey,
}) {
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [contribution, setContribution] = useState(null)
  const [selections, setSelections] = useState({})
  const [published, setPublished] = useState(false)

  // Load any previously generated contribution
  const { data: stored } = useQuery({
    queryKey: [queryKey, engagementId],
    queryFn: getStoredFn,
    enabled: !!getStoredFn,
  })

  const activeContrib = contribution || stored
  const hasContent = (activeContrib?.scope_items?.length || 0) + (activeContrib?.key_questions?.length || 0) > 0

  const generateMutation = useMutation({
    mutationFn: generateFn,
    onSuccess: (data) => {
      setContribution(data)
      // Default: all selected
      const sel = {}
      data.scope_items?.forEach((_, i) => { sel[`si_${i}`] = true })
      data.key_questions?.forEach((_, i) => { sel[`kq_${i}`] = true })
      setSelections(sel)
      setPublished(false)
    },
    onError: () => showToast('Could not generate scope contribution', 'error'),
  })

  const publishMutation = useMutation({
    mutationFn: () => {
      const items = (activeContrib.scope_items || []).map((item, i) => ({
        ...item,
        selected: selections[`si_${i}`] !== false,
      }))
      const questions = (activeContrib.key_questions || []).map((q, i) => ({
        ...q,
        selected: selections[`kq_${i}`] !== false,
      }))
      return publishFn({ scope_items: items, key_questions: questions })
    },
    onSuccess: (data) => {
      showToast(`Published ${data.scope_items_added} items + ${data.questions_added} questions to Scope`)
      setPublished(true)
      onPublished?.()
      qc.invalidateQueries({ queryKey: ['scope', engagementId] })
    },
    onError: () => showToast('Could not publish scope items', 'error'),
  })

  const toggleSi = (i) => setSelections((s) => ({ ...s, [`si_${i}`]: !s[`si_${i}`] }))
  const toggleKq = (i) => setSelections((s) => ({ ...s, [`kq_${i}`]: !s[`kq_${i}`] }))

  const selectedCount =
    (activeContrib?.scope_items || []).filter((_, i) => selections[`si_${i}`] !== false).length +
    (activeContrib?.key_questions || []).filter((_, i) => selections[`kq_${i}`] !== false).length

  return (
    <div className="mt-6 rounded-xl border border-brand/20 bg-brand-subtle/40 p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-fg">Scope &amp; Objectives contribution</h3>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="flex items-center gap-1 text-xs text-brand hover:underline disabled:opacity-40"
        >
          <Sparkles size={12} />
          {generateMutation.isPending ? 'Generating…' : hasContent ? 'Regenerate' : 'Generate'}
        </button>
      </div>

      {!hasContent && !generateMutation.isPending && (
        <p className="mt-3 text-xs text-fg-subtle">
          Click "Generate" to derive scope items and key questions from this module's content.
        </p>
      )}

      {hasContent && (
        <>
          <div className="mt-4 space-y-2">
            {(activeContrib.scope_items || []).map((item, i) => (
              <ContributionItem
                key={i}
                item={item}
                type={item.item_type || 'in_scope'}
                selected={selections[`si_${i}`] !== false}
                onToggle={() => toggleSi(i)}
              />
            ))}
            {(activeContrib.key_questions || []).map((q, i) => (
              <ContributionItem
                key={i}
                item={q}
                type="key_question"
                selected={selections[`kq_${i}`] !== false}
                onToggle={() => toggleKq(i)}
              />
            ))}
          </div>

          <div className="mt-4 flex items-center gap-3">
            {published ? (
              <div className="flex items-center gap-1 text-xs font-medium text-sev-low">
                <Check size={14} /> Published to Scope &amp; Objectives
              </div>
            ) : (
              <button
                onClick={() => publishMutation.mutate()}
                disabled={publishMutation.isPending || selectedCount === 0}
                className="flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white hover:bg-brand-hover disabled:opacity-60"
              >
                <ChevronRight size={14} />
                {publishMutation.isPending
                  ? 'Publishing…'
                  : `Publish ${selectedCount} → Scope & Objectives`}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}
