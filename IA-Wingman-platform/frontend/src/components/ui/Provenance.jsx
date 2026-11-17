import { ShieldCheck, FileText, Globe, Brain, AlertTriangle, Lightbulb, Info } from 'lucide-react'
import Tooltip from './Tooltip'

// Provenance & severity chips — the visual vocabulary for trustworthy, scannable
// AI output. Used everywhere an agent shows a claim, finding, or suggestion.

// Each chip says on hover what it means and what to do with it. Confidence is
// the model's own estimate, and the hint says so: a chip that reads "High"
// without that invites more trust than a self-assessment has earned.
const CONFIDENCE = {
  high: { label: 'High', cls: 'text-sev-low bg-sev-low/12 ring-sev-low/25',
    hint: 'Confidence: high. The agent\'s own estimate that its sources support this well — a self-assessment, not a check. The source still decides.' },
  medium: { label: 'Medium', cls: 'text-sev-med bg-sev-med/12 ring-sev-med/25',
    hint: 'Confidence: medium. The agent found partial support in its sources. Read the source before relying on it.' },
  low: { label: 'Low', cls: 'text-sev-high bg-sev-high/12 ring-sev-high/25',
    hint: 'Confidence: low. The agent found little support for this. Treat it as a lead to verify, not a finding.' },
}

export function ConfidenceBadge({ level = 'medium', showLabel = true }) {
  const c = CONFIDENCE[level] || CONFIDENCE.medium
  return (
    <Tooltip label={c.hint} width="16rem">
      <span
        aria-label={showLabel ? undefined : `Confidence: ${c.label}`}
        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${c.cls}`}
      >
        <ShieldCheck size={11} />
        {showLabel && c.label}
      </span>
    </Tooltip>
  )
}

const SOURCE = {
  document: { label: 'Internal document', icon: FileText, cls: 'text-fg-muted bg-surface-3 ring-line',
    hint: 'From a document uploaded to this audit.' },
  web: { label: 'Web source', icon: Globe, cls: 'text-fg-muted bg-surface-3 ring-line',
    hint: 'From a web page found by live search. Open the link to check it says what is claimed.' },
  model: { label: 'Model knowledge', icon: Brain, cls: 'text-fg-muted bg-surface-3 ring-line',
    hint: 'From what the AI model learned in training, not checked against any source. It may be outdated — verify before relying on it.' },
}

export function SourceChip({ type = 'model', label }) {
  const s = SOURCE[type] || SOURCE.model
  const Icon = s.icon
  return (
    <Tooltip label={s.hint} width="16rem">
      <span
        className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${s.cls}`}
      >
        <Icon size={11} />
        {label || s.label}
      </span>
    </Tooltip>
  )
}

const SEVERITY = {
  must_fix: { label: 'Must fix', icon: AlertTriangle, cls: 'text-sev-high bg-sev-high/12 ring-sev-high/25',
    hint: 'Must fix: resolve this before the file is signed off.' },
  suggestion: { label: 'Suggestion', icon: Lightbulb, cls: 'text-sev-med bg-sev-med/12 ring-sev-med/25',
    hint: 'Suggestion: would improve the file. Your call.' },
  info: { label: 'Info', icon: Info, cls: 'text-fg-muted bg-surface-3 ring-line',
    hint: 'For information. No action needed.' },
}

export function SeverityTag({ level = 'info', children }) {
  const s = SEVERITY[level] || SEVERITY.info
  const Icon = s.icon
  return (
    <Tooltip label={s.hint} width="14rem">
      <span
        className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${s.cls}`}
      >
        <Icon size={11} />
        {children || s.label}
      </span>
    </Tooltip>
  )
}
