import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Sparkles, Check, ChevronRight, Target, AlertTriangle,
  ShieldCheck, FlaskConical, FileText, X, Scale, FileWarning, ArrowUpRight,
} from 'lucide-react'
import { getSpine, acceptNode, promoteTestToFinding, proposeControlTest, createNode } from '../api/racm'
import RecordHistory from '../components/ui/RecordHistory'
import { getEngagement } from '../api/engagements'
import { useStore } from '../store/useStore'
import { Card, SectionHeading } from '../components/ui/Card'
import ScopingEnginePanel from '../components/racm/ScopingEnginePanel'
import AuditMemoryPanel from '../components/racm/AuditMemoryPanel'
import Tooltip from '../components/ui/Tooltip'

// The five lanes of the matrix, left → right. Each knows its parent field so we
// can trace lineage across the whole chain from the flat lists the API returns.
const LANES = [
  { type: 'objectives', label: 'Objective', icon: Target, parent: null },
  { type: 'risks', label: 'Risk', icon: AlertTriangle, parent: 'objective_id', parentType: 'objectives' },
  { type: 'controls', label: 'Control', icon: ShieldCheck, parent: 'risk_id', parentType: 'risks' },
  { type: 'tests', label: 'Test', icon: FlaskConical, parent: 'control_id', parentType: 'controls' },
  { type: 'evidence', label: 'Evidence', icon: FileText, parent: 'test_id', parentType: 'tests' },
]

const key = (type, id) => `${type}:${id}`

function Chip({ tone = 'neutral', children, className = '' }) {
  const tones = {
    neutral: 'bg-surface-3 text-fg-muted',
    brand: 'bg-brand-subtle text-brand',
    crit: 'bg-sev-high/10 text-sev-high',
    warn: 'bg-sev-med/10 text-sev-med',
    good: 'bg-sev-low/10 text-sev-low',
  }
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${tones[tone]} ${className}`}>
      {children}
    </span>
  )
}

const RATING_TONE = { high: 'crit', medium: 'warn', low: 'good' }
const RESULT_TONE = { pass: 'good', fail: 'crit', exceptions: 'warn', pending: 'neutral' }
const DESIGN_TONE = { effective: 'good', deficient: 'crit', not_assessed: 'neutral' }

// A one-line status summary per node type, shown on the card and inspector.
function nodeMeta(type, n) {
  if (type === 'risks' && n.inherent_rating)
    return { tone: RATING_TONE[n.inherent_rating] || 'neutral', label: `${n.inherent_rating} inherent` }
  if (type === 'controls' && n.design_conclusion)
    return { tone: DESIGN_TONE[n.design_conclusion] || 'neutral', label: n.design_conclusion.replace('_', ' ') }
  if (type === 'tests' && n.result) {
    const ex = n.exceptions_count
    const extra = ex != null && ex > 0 ? ` · ${ex} exc.` : ''
    return { tone: RESULT_TONE[n.result] || 'neutral', label: `${n.result}${extra}` }
  }
  if (type === 'evidence' && n.kind) return { tone: 'neutral', label: n.kind }
  return null
}

export default function RacmSpinePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const setActiveEngagement = useStore((s) => s.setActiveEngagement)
  const showToast = useStore((s) => s.showToast)
  const [selected, setSelected] = useState(null) // { type, id }
  const [promoted, setPromoted] = useState(null) // { finding_id, title, created } for the selected test

  const { data: eng } = useQuery({ queryKey: ['engagement', id], queryFn: () => getEngagement(id) })
  const { data: spine, isPending } = useQuery({ queryKey: ['racm', id], queryFn: () => getSpine(id) })

  useEffect(() => { if (eng) setActiveEngagement(eng) }, [eng, setActiveEngagement])

  const accept = useMutation({
    mutationFn: ({ type, nodeId }) => acceptNode(id, type, nodeId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['racm', id] }); showToast('Accepted — you now own this node') },
  })

  const promote = useMutation({
    mutationFn: (testId) => promoteTestToFinding(id, testId),
    onSuccess: (data) => {
      setPromoted(data)
      showToast(data.created ? '5C finding created from this test' : 'A finding already exists for this test')
    },
  })

  const proposeTest = useMutation({
    mutationFn: (controlId) => proposeControlTest(id, controlId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['racm', id] }); showToast('Test proposed under this control') },
  })

  // The only other producer of evidence needs is a work program regeneration,
  // which is refused once the program is signed. Without this, a signed
  // engagement can never record what a test needs, and the DRL's coverage
  // number for it stays at zero for good.
  const addNeed = useMutation({
    mutationFn: ({ testId, ...fields }) => createNode(id, 'evidence', {
      test_id: testId, origin: 'human', accepted: true, ...fields,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['racm', id] }); showToast('Evidence need recorded') },
  })

  // Reset the promote result whenever the selected node changes.
  useEffect(() => { setPromoted(null); promote.reset() }, [selected?.type, selected?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  // Index every node by composite key + build parent/children links once.
  const graph = useMemo(() => {
    const byKey = {}
    const childrenOf = {}
    const parentOf = {}
    if (!spine) return { byKey, childrenOf, parentOf }
    for (const lane of LANES) {
      for (const n of spine[lane.type] || []) {
        const k = key(lane.type, n.id)
        byKey[k] = { ...n, __type: lane.type }
        if (lane.parent && n[lane.parent]) {
          const pk = key(lane.parentType, n[lane.parent])
          parentOf[k] = pk
          ;(childrenOf[pk] ||= []).push(k)
        }
      }
    }
    return { byKey, childrenOf, parentOf }
  }, [spine])

  // Lineage of the selected node: itself + all ancestors + all descendants.
  const chain = useMemo(() => {
    if (!selected) return null
    const start = key(selected.type, selected.id)
    if (!graph.byKey[start]) return null
    const set = new Set([start])
    let up = graph.parentOf[start]
    while (up) { set.add(up); up = graph.parentOf[up] }
    const stack = [start]
    while (stack.length) {
      const cur = stack.pop()
      for (const c of graph.childrenOf[cur] || []) { if (!set.has(c)) { set.add(c); stack.push(c) } }
    }
    return set
  }, [selected, graph])

  // Every AI-proposed node still awaiting acceptance, in lane order — the list
  // the acceptance bar walks through.
  const pendingNodes = useMemo(() => {
    if (!spine) return []
    const out = []
    for (const lane of LANES) for (const node of spine[lane.type] || []) if (node.origin === 'ai' && !node.accepted) out.push({ type: lane.type, id: node.id })
    return out
  }, [spine])
  const awaiting = pendingNodes.length

  // Deterministic spine health — counts, governance acceptance, test outcomes and
  // the traceability gaps (a node in one lane with no child in the next). All
  // computed from the spine already loaded; no extra fetch, no AI.
  const health = useMemo(() => {
    if (!spine) return null
    const counts = {}
    let total = 0, accepted = 0
    for (const lane of LANES) {
      const rows = spine[lane.type] || []
      counts[lane.type] = rows.length
      for (const n of rows) { total++; if (n.accepted) accepted++ }
    }
    const outcomes = { pass: 0, exceptions: 0, fail: 0, pending: 0 }
    for (const t of spine.tests || []) {
      const r = t.result && t.result in outcomes ? t.result : 'pending'
      outcomes[r]++
    }
    // The offending nodes themselves (not just a count) so the gap chips can
    // navigate straight to them.
    const childless = (type, rows) => (rows || []).filter((n) => !(graph.childrenOf[key(type, n.id)] || []).length)
    const gaps = {
      objectivesNoRisk: childless('objectives', spine.objectives),
      risksNoControl: childless('risks', spine.risks),
      controlsNoTest: childless('controls', spine.controls),
      testsNoEvidence: childless('tests', spine.tests),
    }
    return {
      counts, total, accepted,
      acceptedPct: total ? Math.round((accepted / total) * 100) : 0,
      outcomes, gaps,
    }
  }, [spine, graph])

  // Select the next offending node for a traceability gap, cycling on repeat
  // clicks — opens the inspector and lights up its lineage.
  const focusGap = (laneType, nodes) => {
    if (!nodes?.length) return
    const curIdx = nodes.findIndex((n) => selected?.type === laneType && selected?.id === n.id)
    const next = nodes[(curIdx + 1) % nodes.length]
    setSelected({ type: laneType, id: next.id })
  }

  // Walk through the AI proposals still awaiting acceptance, cycling on repeat
  // clicks — opens each in the inspector so it can be accepted.
  const focusPending = () => {
    if (!pendingNodes.length) return
    const curIdx = pendingNodes.findIndex((n) => selected?.type === n.type && selected?.id === n.id)
    setSelected(pendingNodes[(curIdx + 1) % pendingNodes.length])
  }

  if (isPending) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-8 lg:px-8">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-surface-3" />
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-64 animate-pulse rounded-xl bg-surface-3" />)}
        </div>
      </div>
    )
  }

  const selectedNode = selected ? graph.byKey[key(selected.type, selected.id)] : null

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
      <button onClick={() => navigate(`/engagements/${id}/quality`)} className="mb-4 inline-flex items-center gap-1.5 text-sm text-fg-muted hover:text-brand">
        <ArrowLeft size={15} /> Back to quality
      </button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-h1 text-fg">Risk &amp; Control Matrix</h1>
          <p className="mt-1 max-w-2xl text-sm text-fg-muted">
            The traceable spine of the engagement: every objective links to the risks that threaten it,
            the controls that mitigate them, the tests that challenge those controls, and the evidence behind each test.
          </p>
        </div>
        <Chip tone="brand" className="mt-1 px-2.5 py-1 text-xs">
          <Sparkles size={13} /> AI proposes · you own
        </Chip>
      </div>

      {health && health.total > 0 && (
        <Card className="mt-5 p-0 overflow-hidden">
          <div className="grid grid-cols-2 divide-x divide-line sm:grid-cols-5">
            {LANES.map((lane) => {
              const Icon = lane.icon
              return (
                <div key={lane.type} className="flex items-center gap-2.5 px-4 py-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-fg-subtle">
                    <Icon size={15} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-lg font-semibold tabular-nums leading-none text-fg">{health.counts[lane.type]}</div>
                    <div className="mt-0.5 text-caption text-fg-subtle">{lane.label}{health.counts[lane.type] === 1 ? '' : 's'}</div>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="flex flex-col gap-4 border-t border-line px-4 py-3.5 lg:flex-row lg:items-center">
            {/* Governance acceptance — click to walk through the open proposals */}
            <button
              type="button"
              onClick={focusPending}
              disabled={!pendingNodes.length}
              title={pendingNodes.length ? 'Go to the next proposal awaiting your acceptance' : 'Every node is accepted'}
              className="group min-w-0 flex-1 rounded-lg text-left outline-none transition focus-visible:ring-2 focus-visible:ring-brand/40 disabled:cursor-default"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-caption font-medium uppercase tracking-wide text-fg-subtle">Owned by you</span>
                <span className="text-caption tabular-nums text-fg-muted">{health.accepted}/{health.total} · {health.acceptedPct}%</span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-3">
                <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${health.acceptedPct}%` }} />
              </div>
              {pendingNodes.length > 0 && (
                <span className="mt-1 inline-flex items-center gap-1 text-caption text-brand opacity-80 transition-opacity group-hover:opacity-100">
                  {pendingNodes.length} awaiting your acceptance <ArrowUpRight size={11} />
                </span>
              )}
            </button>

            {/* Test outcomes */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-0.5 text-caption font-medium uppercase tracking-wide text-fg-subtle">Tests</span>
              {health.outcomes.pass > 0 && <Chip tone="good"><Check size={11} /> {health.outcomes.pass} pass</Chip>}
              {health.outcomes.exceptions > 0 && <Chip tone="warn"><AlertTriangle size={11} /> {health.outcomes.exceptions} exceptions</Chip>}
              {health.outcomes.fail > 0 && <Chip tone="crit"><X size={11} /> {health.outcomes.fail} fail</Chip>}
              {health.outcomes.pending > 0 && <Chip tone="neutral">{health.outcomes.pending} pending</Chip>}
              {health.counts.tests === 0 && <span className="text-caption text-fg-subtle">none yet</span>}
            </div>

            {/* Traceability */}
            <div className="flex flex-wrap items-center gap-1.5 lg:border-l lg:border-line lg:pl-4">
              <span className="mr-0.5 text-caption font-medium uppercase tracking-wide text-fg-subtle">Traceability</span>
              {(() => {
                const g = health.gaps
                const items = [
                  [g.risksNoControl, 'risks', 'risk', 'no control'],
                  [g.controlsNoTest, 'controls', 'control', 'no test'],
                  [g.objectivesNoRisk, 'objectives', 'objective', 'no risk'],
                  [g.testsNoEvidence, 'tests', 'test', 'no evidence'],
                ].filter(([nodes]) => nodes.length > 0)
                if (items.length === 0) return <Chip tone="good"><Check size={11} /> Fully linked</Chip>
                return items.map(([nodes, laneType, noun, what], i) => (
                  <button
                    key={i}
                    onClick={() => focusGap(laneType, nodes)}
                    title={`Go to the ${nodes.length === 1 ? '' : 'next '}${noun} with ${what} in the matrix`}
                    className="rounded-full outline-none transition hover:brightness-95 focus-visible:ring-2 focus-visible:ring-brand/40 dark:hover:brightness-125"
                  >
                    <Chip tone="warn">
                      <FileWarning size={11} /> {nodes.length} {noun}{nodes.length === 1 ? '' : 's'} · {what}
                      <ArrowUpRight size={11} className="opacity-70" />
                    </Chip>
                  </button>
                ))
              })()}
            </div>
          </div>
        </Card>
      )}

      {awaiting > 0 && (
        <div className="mt-4 flex items-center gap-2 rounded-xl border border-brand/20 bg-brand-faint px-4 py-2.5 text-sm text-fg">
          <Sparkles size={15} className="text-brand" />
          <span><span className="font-semibold text-brand">{awaiting}</span> AI-proposed {awaiting === 1 ? 'node' : 'nodes'} awaiting your acceptance. Click one to review its provenance.</span>
        </div>
      )}

      <div className="mt-6">
        <ScopingEnginePanel engagementId={id} />
      </div>

      <div className="mt-6">
        <AuditMemoryPanel engagementId={id} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[1fr_340px]">
        {/* Lanes */}
        <div className="min-w-0 overflow-x-auto pb-2">
          <div className="flex min-w-[880px] gap-4">
            {LANES.map((lane) => {
              const Icon = lane.icon
              const nodes = spine[lane.type] || []
              return (
                <div key={lane.type} className="flex-1">
                  <div className="mb-3 flex items-center gap-2 border-b border-line pb-2">
                    <Icon size={15} className="text-fg-subtle" />
                    <span className="text-caption font-semibold uppercase tracking-wide text-fg-subtle">{lane.label}</span>
                    <span className="ml-auto text-caption tabular-nums text-fg-subtle">{nodes.length}</span>
                  </div>
                  <div className="flex flex-col gap-3">
                    {nodes.map((n) => {
                      const k = key(lane.type, n.id)
                      const inChain = chain?.has(k)
                      const dimmed = chain && !inChain
                      const isSel = selected?.type === lane.type && selected?.id === n.id
                      const meta = nodeMeta(lane.type, n)
                      const aiPending = n.origin === 'ai' && !n.accepted
                      return (
                        <button
                          key={n.id}
                          onClick={() => setSelected(isSel ? null : { type: lane.type, id: n.id })}
                          className={`rounded-lg border border-line bg-surface p-3 text-left transition
                            ${isSel ? 'border-brand ring-2 ring-brand/30' : inChain ? 'border-brand/50' : 'border-line hover:border-line-strong'}
                            ${dimmed ? 'opacity-40' : 'opacity-100'}`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="rounded bg-surface-3 px-1.5 py-0.5 text-[11px] font-semibold tabular-nums text-fg-muted">{n.ref || '—'}</span>
                            {aiPending
                              ? <Chip tone="brand"><Sparkles size={11} /> AI</Chip>
                              : n.accepted ? <Chip tone="good"><Check size={11} /> You</Chip> : null}
                          </div>
                          <div className="mt-2 text-sm font-medium leading-snug text-fg">{n.title || '—'}</div>
                          {meta && <div className="mt-2"><Chip tone={meta.tone}>{meta.label}</Chip></div>}
                        </button>
                      )
                    })}
                    {nodes.length === 0 && <div className="rounded-xl border border-dashed border-line px-3 py-6 text-center text-caption text-fg-subtle">None yet</div>}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Inspector */}
        <div className="xl:sticky xl:top-6 xl:self-start">
          {selectedNode ? (
            <Inspector
              node={selectedNode}
              graph={graph}
              onClose={() => setSelected(null)}
              onAccept={() => accept.mutate({ type: selectedNode.__type, nodeId: selectedNode.id })}
              accepting={accept.isPending}
              onPromote={() => promote.mutate(selectedNode.id)}
              promoting={promote.isPending}
              promoted={promoted}
              onViewReporting={() => navigate(`/engagements/${id}/reporting`)}
              onProposeTest={() => proposeTest.mutate(selectedNode.id)}
              proposingTest={proposeTest.isPending}
              onAddNeed={(fields) => addNeed.mutate({ testId: selectedNode.id, ...fields })}
              addingNeed={addNeed.isPending}
            />
          ) : (
            <Card className="p-5">
              <div className="flex h-40 flex-col items-center justify-center text-center">
                <ChevronRight size={22} className="text-fg-subtle" />
                <p className="mt-2 text-sm text-fg-muted">Select any node to trace its full lineage and review provenance.</p>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* The agents that fill this matrix now live on the Fieldwork page — point
          anyone who expects them here to where they moved. */}
      <button
        onClick={() => navigate(`/engagements/${id}/fieldwork`)}
        className="mt-10 flex w-full items-center gap-2 rounded-xl border border-line bg-surface px-4 py-3 text-left text-sm text-fg-muted transition-colors hover:border-brand hover:text-brand"
      >
        <Sparkles size={15} className="shrink-0 text-brand" />
        <span>
          <span className="font-medium text-fg">AI fieldwork agents</span> — the agents that write proposals into this matrix now run on the Fieldwork page.
        </span>
        <ArrowUpRight size={15} className="ml-auto shrink-0" />
      </button>

      {/* Scope decisions */}
      <div className="mt-10">
        <SectionHeading>Scope decisions</SectionHeading>
        <p className="mt-1 text-sm text-fg-muted">The governed calls — in/out of scope, materiality, reliance — that shape the matrix. Rationale and sponsor sign-off are recorded for every decision.</p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {(spine.scope_decisions || []).map((s) => (
            <Card key={s.id} className="p-4">
              <div className="flex items-center gap-2">
                <Scale size={14} className="text-fg-subtle" />
                <Chip tone={s.decision_type === 'out_of_scope' ? 'neutral' : s.decision_type === 'reliance' ? 'warn' : 'brand'}>{s.decision_type.replaceAll('_', ' ')}</Chip>
                <Chip tone={s.status === 'approved' ? 'good' : 'neutral'} className="ml-auto">{s.status}</Chip>
                {s.origin === 'ai' && !s.status && <Chip tone="brand"><Sparkles size={11} /> AI</Chip>}
              </div>
              <div className="mt-2 text-sm font-medium text-fg">{s.summary}</div>
              {s.rationale && <div className="mt-1 text-sm text-fg-muted">{s.rationale}</div>}
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-caption text-fg-subtle">
                {s.materiality && <span>Materiality: {s.materiality}</span>}
                {s.sponsor && <span>Sponsor: {s.sponsor}</span>}
              </div>
            </Card>
          ))}
          {(spine.scope_decisions || []).length === 0 && <div className="text-sm text-fg-subtle">No scope decisions recorded yet.</div>}
        </div>
      </div>
    </div>
  )
}

// Builds the "O1 › R2 › C2 › T2" breadcrumb from a node up to its root objective.
function breadcrumb(node, graph) {
  const refs = []
  let cur = key(node.__type, node.id)
  while (cur) { const n = graph.byKey[cur]; if (!n) break; refs.unshift(n.ref || '—'); cur = graph.parentOf[cur] }
  return refs
}

// What a test needs from the auditee, recorded against the test itself.
// `kind` decides whether it can ever become a document request: an interview is
// arranged and an observation is scheduled, so neither belongs on a DRL.
function EvidenceNeedForm({ onSubmit, busy }) {
  const [open, setOpen] = useState(false)
  const [f, setF] = useState({ title: '', kind: 'document', requested_from: '', period: '' })
  const field = (k, placeholder, extra = '') => (
    <input
      value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })}
      placeholder={placeholder}
      className={`w-full rounded-lg border border-line bg-surface px-2 py-1.5 text-sm text-fg outline-none transition placeholder:text-fg-subtle focus:border-brand ${extra}`}
    />
  )

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex w-full items-center justify-center gap-2 rounded-lg border border-brand/30 px-4 py-2 text-sm font-medium text-brand transition hover:bg-brand-faint"
      >
        <FileText size={15} /> Record what this test needs
      </button>
    )
  }
  return (
    <div className="space-y-2">
      {field('title', 'The document or extract, as the auditee would name it')}
      <div className="flex gap-2">
        <select
          value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}
          className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm text-fg outline-none focus:border-brand"
        >
          {['document', 'data', 'interview', 'observation'].map((k) => <option key={k} value={k}>{k}</option>)}
        </select>
        {field('requested_from', 'Department that holds it')}
      </div>
      {field('period', 'Period or population, if any')}
      {!['document', 'data'].includes(f.kind) && (
        <p className="text-caption text-fg-subtle">
          An {f.kind} is arranged rather than requested, so this will not appear on the document request list.
        </p>
      )}
      <div className="flex gap-2">
        <button
          onClick={() => { onSubmit(f); setOpen(false); setF({ title: '', kind: 'document', requested_from: '', period: '' }) }}
          disabled={busy || !f.title.trim()}
          className="flex-1 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-fg transition hover:opacity-90 disabled:opacity-60"
        >
          {busy ? 'Saving…' : 'Record it'}
        </button>
        <button onClick={() => setOpen(false)} className="rounded-lg border border-line px-3 py-2 text-sm text-fg-muted transition hover:text-fg">
          Cancel
        </button>
      </div>
    </div>
  )
}

function Inspector({ node, graph, onClose, onAccept, accepting, onPromote, promoting, promoted, onViewReporting, onProposeTest, proposingTest, onAddNeed, addingNeed }) {
  const crumbs = breadcrumb(node, graph)
  const prov = node.provenance || {}
  const aiPending = node.origin === 'ai' && !node.accepted
  const meta = nodeMeta(node.__type, node)
  const typeLabel = LANES.find((l) => l.type === node.__type)?.label || node.__type

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="rounded bg-surface-3 px-1.5 py-0.5 text-[11px] font-semibold text-fg-muted">{node.ref || '—'}</span>
          <span className="text-caption uppercase tracking-wide text-fg-subtle">{typeLabel}</span>
        </div>
        <Tooltip label="Close details" side="left">
          <button onClick={onClose} aria-label="Close details" className="text-fg-subtle hover:text-fg"><X size={16} /></button>
        </Tooltip>
      </div>

      <h3 className="mt-2 text-base font-semibold leading-snug text-fg">{node.title || '—'}</h3>

      {crumbs.length > 1 && (
        <div className="mt-2 flex flex-wrap items-center gap-1 text-caption text-fg-subtle">
          {crumbs.map((r, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <ChevronRight size={11} />}
              <span className={i === crumbs.length - 1 ? 'font-semibold text-brand' : ''}>{r}</span>
            </span>
          ))}
        </div>
      )}

      {node.description && <p className="mt-3 text-sm text-fg-muted">{node.description}</p>}
      {node.conclusion && <p className="mt-3 rounded-lg bg-surface-2 p-3 text-sm text-fg"><span className="font-medium">Conclusion:</span> {node.conclusion}</p>}

      <div className="mt-3 flex flex-wrap gap-2">
        {meta && <Chip tone={meta.tone}>{meta.label}</Chip>}
        {node.category && <Chip tone="neutral">{node.category}</Chip>}
        {node.method && <Chip tone="neutral">{node.method.replace('_', ' ')}</Chip>}
        {node.sample_size != null && node.sample_size > 0 && <Chip tone="neutral">n = {node.sample_size}</Chip>}
        {node.confidence && <Chip tone="neutral">confidence: {node.confidence}</Chip>}
      </div>

      {/* Provenance */}
      <div className="mt-4 border-t border-line pt-3">
        <div className="text-caption font-semibold uppercase tracking-wide text-fg-subtle">Provenance</div>
        <div className="mt-1.5 space-y-1 text-sm text-fg-muted">
          <div className="flex items-center gap-2">
            {aiPending ? <Chip tone="brand"><Sparkles size={11} /> AI proposed</Chip> : <Chip tone="good"><Check size={11} /> {node.origin === 'ai' ? 'AI · accepted' : 'Human'}</Chip>}
            {node.accepted_by && <span className="text-caption">by {node.accepted_by}</span>}
          </div>
          {prov.source_type && <div>Source: <span className="text-fg">{prov.source_type.replace('_', ' ')}</span>{prov.source_ref ? ` · ${prov.source_ref}` : ''}</div>}
          {prov.rationale && <div className="italic">“{prov.rationale}”</div>}
        </div>
      </div>

      <RecordHistory entity={`racm_${node.__type}`} entityId={node.id} />

      {aiPending && (
        <button
          onClick={onAccept}
          disabled={accepting}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-brand-fg transition hover:opacity-90 disabled:opacity-60"
        >
          <Check size={15} /> {accepting ? 'Accepting…' : 'Accept — I own this'}
        </button>
      )}

      {/* Control-Testing agent: propose a risk-based test for this control */}
      {node.__type === 'controls' && (
        <div className="mt-4 border-t border-line pt-3">
          <button
            onClick={onProposeTest}
            disabled={proposingTest}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-brand/30 px-4 py-2 text-sm font-medium text-brand transition hover:bg-brand-faint disabled:opacity-60"
          >
            <FlaskConical size={15} /> {proposingTest ? 'Proposing…' : 'Propose a control test'}
          </button>
        </div>
      )}

      {node.__type === 'tests' && (
        <div className="mt-4 border-t border-line pt-3">
          <EvidenceNeedForm onSubmit={onAddNeed} busy={addingNeed} />
        </div>
      )}

      {/* Close the loop: a test's exceptions become a traceable 5C finding */}
      {node.__type === 'tests' && (
        <div className="mt-4 border-t border-line pt-3">
          {promoted ? (
            <div className="rounded-lg bg-brand-faint p-3">
              <div className="flex items-center gap-2 text-sm font-medium text-fg">
                <FileWarning size={15} className="text-brand" />
                {promoted.created ? '5C finding created' : 'Finding already exists'}
              </div>
              <p className="mt-1 text-caption text-fg-muted">Traces back through this test to its control, risk and objective.</p>
              <button onClick={onViewReporting} className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-brand hover:underline">
                View in Reporting <ArrowUpRight size={14} />
              </button>
            </div>
          ) : (
            <button
              onClick={onPromote}
              disabled={promoting}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-brand/30 px-4 py-2 text-sm font-medium text-brand transition hover:bg-brand-faint disabled:opacity-60"
            >
              <FileWarning size={15} /> {promoting ? 'Creating…' : 'Promote to 5C finding'}
            </button>
          )}
        </div>
      )}
    </Card>
  )
}
