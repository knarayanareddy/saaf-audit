import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles, Loader2, FileDown, AlertTriangle, ArrowUpRight } from 'lucide-react'
import { getBoardSummary, getBoardNarrative, draftBoardNarrative, exportBoard } from '../api/board'
import { useOrg } from '../lib/useOrg'
import {
  entityLabel, statusLabel, statusColor, statusToken, auditTypeLabel,
} from '../lib/entities'
import PageContainer from '../components/layout/PageContainer'
import { PageHeader } from '../components/layout/PageHeader'
import Section from '../components/ui/Section'
import MetricStrip from '../components/ui/MetricStrip'
import Button from '../components/ui/Button'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import DonutChart from '../components/charts/DonutChart'
import BarList from '../components/charts/BarList'
import { SkeletonCard } from '../components/ui/Skeleton'
import { useStore } from '../store/useStore'

// Severity tokens (--sev-*) instead of raw Tailwind hues: one class set that is
// legible in light AND dark, and the only colour on this page besides the brand
// ramp — which is what makes a board report read as a board report.
const SEV = {
  high: 'text-sev-high bg-sev-high/12 ring-sev-high/25',
  medium: 'text-sev-med bg-sev-med/12 ring-sev-med/25',
  low: 'text-sev-low bg-sev-low/12 ring-sev-low/25',
}
const OPINION = {
  satisfactory: { label: 'Satisfactory', cls: 'text-sev-low bg-sev-low/12' },
  needs_improvement: { label: 'Needs improvement', cls: 'text-sev-med bg-sev-med/12' },
  unsatisfactory: { label: 'Unsatisfactory', cls: 'text-sev-high bg-sev-high/12' },
}

// The rule above a findings number, instead of a filled severity tile.
const SEV_BAR = { high: 'bg-sev-high', medium: 'bg-sev-med', low: 'bg-sev-low' }

function SevChip({ level }) {
  return <span className={`inline-flex h-5 shrink-0 items-center rounded px-1.5 text-[11px] font-medium uppercase ring-1 ring-inset ${SEV[level] || SEV.low}`}>{level}</span>
}

export default function BoardReportPage() {
  const navigate = useNavigate()
  const org = useOrg()
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [drafting, setDrafting] = useState(false)

  const { data: board, isPending } = useQuery({ queryKey: ['board-summary'], queryFn: getBoardSummary })
  const { data: narrative } = useQuery({
    queryKey: ['board-narrative'],
    queryFn: getBoardNarrative,
    refetchInterval: drafting ? 2000 : false,
  })

  const draft = useMutation({
    mutationFn: draftBoardNarrative,
    onSuccess: () => { setConfirmOpen(false); setDrafting(true) },
  })

  // Stop polling once an AI narrative lands.
  useEffect(() => {
    if (drafting && narrative?.generated_by === 'ai') {
      setDrafting(false)
      showToast('Board narrative drafted by AI')
    }
  }, [drafting, narrative?.generated_by, showToast])

  if (isPending || !board) {
    return (
      <PageContainer width="wide">
        <PageHeader title="Board report" subtitle={org.name} />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
          <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
      </PageContainer>
    )
  }

  const p = board.portfolio
  const f = board.findings
  const c = board.controls
  const hotspots = board.hotspots || []
  const ws = board.coverage?.entity_whitespace || []

  // exec summary: prefer a saved (AI or deterministic) narrative, else the deterministic fallback
  const summary = (narrative && narrative.exec_summary) ? narrative : board.deterministic_summary
  const opinion = OPINION[summary?.overall_opinion] || null

  const statusSegments = p.by_status
    .map((s) => ({ key: s.key, label: statusLabel(s.key), value: s.value, color: statusColor(s.key) }))
    .filter((s) => s.value > 0)
  const entityBars = p.by_entity
    .map((e) => ({ key: e.key, label: entityLabel(e.key), value: e.value }))
    .sort((a, b) => b.value - a.value)
  const typeBars = p.by_audit_type
    .map((t) => ({ key: t.key, label: auditTypeLabel(t.key), value: t.value }))
    .slice(0, 6)

  return (
    <PageContainer width="wide">
      <PageHeader
        title="Board report"
        subtitle={`${org.name} · Internal Audit portfolio · ${p.total} engagements`}
        actions={
          <>
            <Button variant="secondary" onClick={() => setConfirmOpen(true)} disabled={drafting}>
              {drafting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
              {drafting ? 'Drafting…' : 'Draft with AI'}
            </Button>
            <Button variant="secondary" onClick={exportBoard}><FileDown size={15} /> Word</Button>
          </>
        }
      />

      {/* Executive summary — an editorial block, not a tile. A narrow measure and
          a generous line height are what make prose read as a board document. */}
      <section className="border-t border-line pt-4">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-caption">Executive summary</h2>
          {opinion && (
            <span className={`inline-flex h-5 items-center rounded px-1.5 text-[11px] font-medium ${opinion.cls}`}>
              Portfolio opinion — {opinion.label}
            </span>
          )}
        </div>
        <p className="mt-3 max-w-[68ch] text-[15px] leading-7 text-fg">{summary?.exec_summary}</p>
        {summary?.key_messages?.length > 0 && (
          <ul className="mt-4 max-w-[68ch] space-y-1.5">
            {summary.key_messages.map((m, i) => (
              <li key={i} className="flex gap-2.5 text-[13px] leading-6 text-fg-muted">
                <span className="mt-2.5 h-px w-3 shrink-0 bg-line-strong" />
                <span>{m}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-meta">
          {summary?.generated_by === 'ai'
            ? 'AI-drafted from the portfolio aggregates; the auditor reviews and signs.'
            : 'Deterministically assembled from the portfolio data. Draft with AI for board-ready prose.'}
        </p>
        {summary?.generated_by === 'ai' && summary?.stale && (
          <p className="mt-1 flex items-center gap-1.5 text-[11px] font-medium text-sev-med">
            <AlertTriangle size={12} /> The portfolio has changed since this summary was drafted — re-draft to refresh the figures.
          </p>
        )}
      </section>

      {/* The four numbers a board asks for, read left to right in one line. */}
      <MetricStrip
        className="mt-6"
        items={[
          { key: 'total', value: p.total, label: 'Engagements', hint: `${p.active} active · ${p.closed} closed`, accent: statusToken('in_fieldwork'), onClick: () => navigate('/engagements') },
          { key: 'active', value: p.active, label: 'Active audits', accent: statusToken('in_planning'), onClick: () => navigate('/engagements?status=active') },
          { key: 'high', value: f.by_rating?.high ?? 0, label: 'High findings', hint: `${f.total} across ${f.engagements_with_findings} audits`, accent: '--sev-high' },
          { key: 'hotspots', value: hotspots.length, label: 'Risk hotspots', hint: 'High risk × weak control', accent: '--sev-med' },
        ]}
      />

      {/* Distribution: one frame, three columns, hairlines between. */}
      <div className="mt-6 rounded-lg border border-line bg-surface">
        <div className="grid grid-cols-1 divide-y divide-line-subtle lg:grid-cols-3 lg:divide-x lg:divide-y-0">
          <div className="min-w-0 p-4">
            <h2 className="text-caption mb-3">By status</h2>
            <DonutChart segments={statusSegments} size={132} thickness={14} centerValue={p.total} centerLabel="audits" onSegmentClick={(k) => navigate(`/engagements?status=${k}`)} />
          </div>
          <div className="min-w-0 p-4">
            <h2 className="text-caption mb-3">By entity</h2>
            <BarList items={entityBars} onItemClick={(k) => navigate(`/engagements?entity=${k}`)} />
          </div>
          <div className="min-w-0 p-4">
            <h2 className="text-caption mb-3">By audit type</h2>
            <BarList items={typeBars} onItemClick={(k) => navigate(`/engagements?type=${k}`)} />
          </div>
        </div>
      </div>

      {/* Hotspots — the flagship section */}
      <Section
        className="mt-6"
        title="Risk & control hotspots"
        action={<span className="text-meta">{hotspots.length} candidate{hotspots.length === 1 ? '' : 's'}</span>}
      >
        <p className="py-2 text-meta">
          Lines where a high inherent risk meets a weak, missing or failing control — across the whole portfolio. Verify before acting.
        </p>
        {hotspots.length === 0 ? (
          <p className="py-4 text-[13px] text-fg-muted">No candidate hotspots in the current data.</p>
        ) : (
          hotspots.map((h, i) => (
            <button
              key={i}
              onClick={() => navigate(`/engagements/${h.engagement_id}/racm`)}
              className="group flex w-full items-center gap-3 px-1 py-2 text-left transition-colors duration-150 hover:bg-surface-2"
            >
              <SevChip level={h.severity} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[13px] font-medium text-fg">{h.reason}</span>
                <span className="block truncate text-meta">
                  {h.engagement_name}
                  {(h.risk_ref || h.control_ref) && ` · ${[h.risk_ref, h.control_ref].filter(Boolean).join(' / ')}`}
                  {h.risk_title && ` · ${h.risk_title}`}
                </span>
              </span>
              <ArrowUpRight size={14} className="shrink-0 text-fg-subtle opacity-0 transition-opacity duration-150 group-hover:opacity-100" />
            </button>
          ))
        )}
      </Section>

      {/* Findings + coverage */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section title="Findings across the portfolio" divided={false}>
          <div className="flex gap-4 py-3">
            {['high', 'medium', 'low'].map((lvl) => (
              <div key={lvl} className="flex-1">
                <div className={`h-0.5 w-full rounded-full ${SEV_BAR[lvl]}`} />
                <div className="mt-2 text-metric text-fg">{f.by_rating?.[lvl] ?? 0}</div>
                <div className="text-caption">{lvl}</div>
              </div>
            ))}
          </div>
          <div className="border-t border-line-subtle pt-3">
            <BarList
              items={(f.by_entity || []).map((e) => ({ key: e.key, label: entityLabel(e.key), value: e.value }))}
              onItemClick={(k) => navigate(`/engagements?entity=${k}`)}
            />
          </div>
        </Section>

        <Section title="Assurance coverage" divided={false}>
          {ws.length === 0 ? (
            <p className="py-3 text-[13px] text-fg-muted">
              Every organisational unit has at least one audit on record.
            </p>
          ) : (
            <div className="py-3">
              <p className="text-[13px] text-fg-muted">No audit is recorded for these units — an assurance-coverage gap:</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {ws.map((code) => (
                  <span key={code} className="inline-flex h-5 items-center rounded bg-sev-med/12 px-1.5 text-[11px] font-medium text-sev-med ring-1 ring-inset ring-sev-med/25">
                    {entityLabel(code)}
                  </span>
                ))}
              </div>
            </div>
          )}
          <dl className="divide-y divide-line-subtle border-t border-line-subtle text-[13px]">
            <div className="flex items-center justify-between py-2">
              <dt className="text-fg-muted">Controls assessed effective</dt>
              <dd className="font-medium tabular-nums text-sev-low">{c.effective}</dd>
            </div>
            <div className="flex items-center justify-between py-2">
              <dt className="text-fg-muted">Controls design-deficient</dt>
              <dd className="font-medium tabular-nums text-sev-high">{c.deficient}</dd>
            </div>
            <div className="flex items-center justify-between py-2">
              <dt className="text-fg-muted">Not yet assessed</dt>
              <dd className="font-medium tabular-nums text-fg">{c.not_assessed}</dd>
            </div>
          </dl>
        </Section>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => draft.mutate()}
        title="Draft the board narrative with AI?"
        description="Writes an audit-committee executive summary from the portfolio aggregates. It uses AI budget and introduces no new figures — only interprets the data. Falls back to the deterministic summary on failure."
        confirmLabel="Draft — uses AI"
        loading={draft.isPending}
      />
    </PageContainer>
  )
}
