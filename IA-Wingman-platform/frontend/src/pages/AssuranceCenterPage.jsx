import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ShieldCheck, ShieldAlert, Shield, PlayCircle, Loader2, FlaskConical,
  FileWarning, Info, CircleCheck, CircleAlert, MinusCircle,
  Search, AlertTriangle, ChevronDown, X,
} from 'lucide-react'
import { getPosture, getRuns, getRunDetail, getDocumentFlags, runSuite, LIVE_CONFIRM_TOKEN } from '../api/assurance'
import PageContainer from '../components/layout/PageContainer'
import { PageHeader } from '../components/layout/PageHeader'
import Button from '../components/ui/Button'
import { SectionHeading } from '../components/ui/Card'
import { SummaryCard } from '../components/ui/ReadableOutput'
import ConfirmDialog from '../components/ui/ConfirmDialog'

const STATUS = {
  implemented: { label: 'Implemented', icon: CircleCheck, cls: 'text-sev-low bg-sev-low/12 ring-sev-low/25' },
  partial: { label: 'Partial', icon: CircleAlert, cls: 'text-sev-med bg-sev-med/12 ring-sev-med/25' },
  residual: { label: 'Residual risk', icon: ShieldAlert, cls: 'text-sev-high bg-sev-high/12 ring-sev-high/25' },
  not_applicable: { label: 'N/A', icon: MinusCircle, cls: 'text-fg-subtle bg-surface-3 ring-line' },
}

function StatusPill({ status }) {
  const s = STATUS[status] || STATUS.not_applicable
  const Icon = s.icon
  return (
    <span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${s.cls}`}>
      <Icon size={11} /> {s.label}
    </span>
  )
}

function ControlCard({ c }) {
  return (
    <div className="flex flex-col rounded-xl border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="text-sm font-semibold text-fg">{c.name}</div>
        <StatusPill status={c.status} />
      </div>
      <p className="mt-1 text-xs text-fg-muted">{c.defends}</p>
      <p className="mt-2 flex items-start gap-1.5 text-xs text-fg-subtle">
        <CircleCheck size={12} className="mt-0.5 shrink-0 text-sev-low" />
        <span>{c.evidence}</span>
      </p>
      {c.residual && (
        <p className="mt-1.5 flex items-start gap-1.5 text-xs text-fg-subtle">
          <ShieldAlert size={12} className="mt-0.5 shrink-0 text-sev-med" />
          <span>{c.residual}</span>
        </p>
      )}
    </div>
  )
}

function SuiteResultBar({ passed, total }) {
  const pct = total ? Math.round((100 * passed) / total) : 0
  const allPass = total > 0 && passed === total
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-3">
        <div className={`h-full rounded-full ${allPass ? 'bg-sev-low/100' : 'bg-sev-med/100'}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="shrink-0 text-sm font-semibold text-fg">{passed}/{total}</span>
    </div>
  )
}

const VERDICT = {
  resisted: { label: 'Resisted', icon: CircleCheck, cls: 'text-sev-low bg-sev-low/12 ring-sev-low/25' },
  verified: { label: 'Verified', icon: CircleCheck, cls: 'text-sev-low bg-sev-low/12 ring-sev-low/25' },
  needs_verify: { label: 'To verify', icon: Search, cls: 'text-sev-med bg-sev-med/12 ring-sev-med/25' },
  leaked: { label: 'System-prompt leak', icon: AlertTriangle, cls: 'text-sev-high bg-sev-high/12 ring-sev-high/25' },
  gap: { label: 'Gap', icon: CircleAlert, cls: 'text-sev-high bg-sev-high/12 ring-sev-high/25' },
  error: { label: 'Run error', icon: MinusCircle, cls: 'text-fg-subtle bg-surface-3 ring-line' },
}

function VerdictPill({ verdict }) {
  const v = VERDICT[verdict] || VERDICT.error
  const Icon = v.icon
  return (
    <span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${v.cls}`}>
      <Icon size={11} /> {v.label}
    </span>
  )
}

function ReportPanel({ report, onClose }) {
  if (!report) return null
  const results = report.results || []
  const isLive = report.mode === 'live'
  const v = report.verdicts || {}
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-fg">
          {isLive ? <ShieldCheck size={16} className="text-brand" /> : <FlaskConical size={16} className="text-brand" />}
          {isLive ? 'Live red-team report' : 'Control-coverage report'}
          <span className={`rounded px-1.5 py-0.5 text-caption font-semibold ${isLive ? 'bg-sev-med/12 text-sev-med' : 'bg-surface-3 text-fg-subtle'}`}>{report.mode}</span>
        </div>
        {onClose && (
          <button onClick={onClose} className="rounded p-1 text-fg-subtle hover:bg-surface-3 hover:text-fg" aria-label="Close report">
            <X size={15} />
          </button>
        )}
      </div>

      {report.headline && <p className="mt-2 text-sm font-medium text-fg">{report.headline}</p>}

      <div className="mt-2 flex flex-wrap gap-1.5">
        {Object.entries(v).map(([verdict, n]) => (
          <span key={verdict} className="inline-flex items-center gap-1 text-caption">
            <VerdictPill verdict={verdict} /> <span className="text-fg-subtle">×{n}</span>
          </span>
        ))}
      </div>

      <ul className="mt-3 divide-y divide-line">
        {results.map((r) => (
          <li key={r.id} className="flex flex-col gap-1 py-2.5 sm:flex-row sm:items-start sm:gap-3">
            <div className="flex min-w-0 flex-1 flex-col">
              <div className="flex items-center gap-2">
                <span className="text-caption font-medium uppercase tracking-wide text-fg-subtle">{r.category_label || r.category}</span>
              </div>
              <span className="text-sm text-fg">{r.title || r.id}</span>
              {r.detail && <span className="mt-0.5 text-xs text-fg-muted">{r.detail}</span>}
              {!isLive && r.proves && <span className="mt-0.5 text-xs text-fg-subtle">Proves: {r.proves}</span>}
            </div>
            <div className="shrink-0"><VerdictPill verdict={r.verdict} /></div>
          </li>
        ))}
      </ul>

      {report.note && (
        <p className="mt-3 flex items-start gap-1.5 rounded-lg bg-surface-2 px-3 py-2 text-xs text-fg-subtle">
          <Info size={13} className="mt-0.5 shrink-0" /> <span>{report.note}</span>
        </p>
      )}
    </div>
  )
}

export default function AssuranceCenterPage() {
  const qc = useQueryClient()
  const { data: posture } = useQuery({ queryKey: ['assurance-posture'], queryFn: getPosture })
  const { data: runsData } = useQuery({ queryKey: ['assurance-runs'], queryFn: getRuns })
  const { data: flagsData } = useQuery({ queryKey: ['assurance-flags'], queryFn: getDocumentFlags })
  const [confirmLive, setConfirmLive] = useState(false)
  const [notice, setNotice] = useState(null)
  const [report, setReport] = useState(null)

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['assurance-posture'] })
    qc.invalidateQueries({ queryKey: ['assurance-runs'] })
  }

  const staticRun = useMutation({
    mutationFn: () => runSuite('static'),
    onSuccess: (r) => { setReport(r); setNotice({ tone: 'ok', text: `Injection test-suite: ${r.passed}/${r.total} controls verified.` }); refresh() },
    onError: () => setNotice({ tone: 'err', text: 'Could not run the injection test-suite.' }),
  })

  const liveRun = useMutation({
    mutationFn: () => runSuite('live', LIVE_CONFIRM_TOKEN),
    onSuccess: (r) => { setReport(r); setNotice({ tone: 'ok', text: r.headline || `Live red-team: ${r.passed}/${r.total} resisted.` }); refresh() },
    onError: (e) => setNotice({ tone: 'err', text: e?.response?.data?.detail || 'Live red-team run failed.' }),
  })

  const openRun = async (id) => {
    try { setReport(await getRunDetail(id)) } catch { setNotice({ tone: 'err', text: 'Could not load that run.' }) }
  }

  const controls = posture?.controls || []
  const counts = posture?.counts || {}
  const coverage = posture?.coverage
  const resistance = posture?.resistance
  const flagged = flagsData?.documents || []

  return (
    <PageContainer>
      <PageHeader
        title="AI Assurance Center"
        subtitle="Security posture, injection defenses & red-team"
        badges={<span className="inline-flex items-center gap-1 rounded-full bg-brand-faint px-2 py-0.5 text-caption text-brand"><Shield size={12} /> Trust layer</span>}
      />

      <SummaryCard title="How to read this" icon={Info}>
        Injection isolation is <strong>defense-in-depth, not a guarantee</strong>. This page separates{' '}
        <strong>control coverage</strong> (deterministic — are the defenses wired up) from{' '}
        <strong>empirical resistance</strong> (a live red-team that actually tests the model). Residual
        risks are shown, not hidden — the dashboard is itself auditable.
      </SummaryCard>

      {notice && (
        <div className={`mt-4 rounded-lg border px-3 py-2 text-sm ${
          notice.tone === 'ok' ? 'border-sev-low/30 bg-sev-low/10 text-sev-low'
            : 'border-sev-high/30 bg-sev-high/10 text-sev-high'}`}>
          {notice.text}
        </div>
      )}

      {!posture ? (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-32 animate-pulse rounded-xl bg-surface-3" />)}
        </div>
      ) : (
        <div className="mt-6 space-y-8">
          {/* Coverage vs resistance */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-line bg-surface p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-fg">
                <FlaskConical size={16} className="text-brand" /> Control coverage
                <span className="ml-auto text-caption font-normal text-fg-subtle">deterministic · free</span>
              </div>
              {coverage && <div className="mt-3"><SuiteResultBar passed={coverage.passed} total={coverage.total} /></div>}
              <p className="mt-2 text-xs text-fg-subtle">{coverage?.note}</p>
              <Button variant="secondary" className="mt-3" onClick={() => staticRun.mutate()} disabled={staticRun.isPending}>
                {staticRun.isPending ? <Loader2 size={15} className="animate-spin" /> : <PlayCircle size={15} />} Run injection test-suite
              </Button>
            </div>

            <div className="rounded-xl border border-line bg-surface p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-fg">
                <ShieldCheck size={16} className="text-brand" /> Empirical resistance
                <span className="ml-auto text-caption font-normal text-sev-med">live · uses AI budget</span>
              </div>
              {resistance ? (
                <>
                  <div className="mt-3"><SuiteResultBar passed={resistance.passed} total={resistance.total} /></div>
                  {resistance.headline && <p className="mt-2 text-xs font-medium text-fg">{resistance.headline}</p>}
                  <p className="mt-1 text-xs text-fg-subtle">
                    Last run {resistance.at ? new Date(resistance.at).toLocaleString() : ''}. {resistance.note}
                  </p>
                </>
              ) : (
                <p className="mt-3 text-xs text-fg-subtle">No live red-team run yet. This is the only measure of whether the model actually resists injection — it spends AI budget, so it is opt-in.</p>
              )}
              <Button variant="secondary" className="mt-3" onClick={() => setConfirmLive(true)} disabled={liveRun.isPending}>
                {liveRun.isPending ? <Loader2 size={15} className="animate-spin" /> : <PlayCircle size={15} />} Run live red-team
              </Button>
            </div>
          </div>

          {/* Last-run report (readable drill-down) */}
          {report && <ReportPanel report={report} onClose={() => setReport(null)} />}

          {/* Control checklist */}
          <div>
            <div className="flex items-center gap-3">
              <SectionHeading>Security controls</SectionHeading>
              <div className="flex gap-1.5 text-caption">
                {counts.implemented ? <span className="rounded-full bg-sev-low/12 px-2 py-0.5 text-sev-low">{counts.implemented} implemented</span> : null}
                {counts.partial ? <span className="rounded-full bg-sev-med/12 px-2 py-0.5 text-sev-med">{counts.partial} partial</span> : null}
                {counts.residual ? <span className="rounded-full bg-sev-high/12 px-2 py-0.5 text-sev-high">{counts.residual} residual</span> : null}
              </div>
            </div>
            <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {controls.map((c) => <ControlCard key={c.id} c={c} />)}
            </div>
          </div>

          {/* Flagged documents */}
          <div>
            <SectionHeading>Flagged documents</SectionHeading>
            {flagged.length === 0 ? (
              <p className="mt-2 flex items-center gap-1.5 text-sm text-fg-subtle">
                <CircleCheck size={14} className="text-sev-low" /> No uploaded documents show suspected injection payloads.
              </p>
            ) : (
              <ul className="mt-3 space-y-2">
                {flagged.map((d) => (
                  <li key={d.id} className="flex items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2 text-sm">
                    <FileWarning size={16} className="shrink-0 text-sev-med" />
                    <span className="min-w-0 flex-1 truncate text-fg">{d.filename}</span>
                    <span className="shrink-0 text-xs text-fg-subtle">{d.flag_count} signal{d.flag_count === 1 ? '' : 's'} · verify</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Run history */}
          {runsData?.runs?.length > 0 && (
            <div>
              <SectionHeading>Recent runs</SectionHeading>
              <ul className="mt-3 space-y-1.5">
                {runsData.runs.slice(0, 8).map((r) => (
                  <li key={r.id}>
                    <button
                      onClick={() => openRun(r.id)}
                      className="flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left text-xs text-fg-muted hover:bg-surface-3"
                    >
                      <span className={`shrink-0 rounded px-1.5 py-0.5 font-semibold ${r.mode === 'live' ? 'bg-sev-med/12 text-sev-med' : 'bg-surface-3 text-fg-subtle'}`}>{r.mode}</span>
                      <span className="min-w-0 flex-1 truncate">{r.headline || `${r.passed}/${r.total} passed`}</span>
                      <span className="shrink-0 text-fg-subtle">{r.started_at ? new Date(r.started_at).toLocaleString() : ''}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        open={confirmLive}
        onClose={() => setConfirmLive(false)}
        onConfirm={() => { setConfirmLive(false); liveRun.mutate() }}
        title="Run live red-team?"
        description="This sends crafted injection payloads to the real model and consumes AI budget. It is the only test of empirical resistance. Rate-limited to once per minute."
        confirmLabel="Run live red-team"
        loading={liveRun.isPending}
      />
    </PageContainer>
  )
}
