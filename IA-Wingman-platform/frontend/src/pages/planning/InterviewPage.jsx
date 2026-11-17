import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users, Sparkles, Loader2, MessageSquarePlus, Trash2, FileDown, Play,
  Target, ShieldCheck, Crosshair, ChevronRight, ShieldQuestion, Mic, Square,
} from 'lucide-react'
import { useSpeechDictation } from '../../lib/useSpeechDictation'
import { getEngagement } from '../../api/engagements'
import {
  getGuide, buildGuide, listSessions, createSession, updateSession,
  deleteSession, analyseSession, exportMinutes,
} from '../../api/interview'
import { useStore } from '../../store/useStore'
import PageContainer from '../../components/layout/PageContainer'
import { PageHeader } from '../../components/layout/PageHeader'
import { EntityBadge } from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { Card, SectionHeading } from '../../components/ui/Card'
import Segmented from '../../components/ui/Segmented'
import Collapsible from '../../components/ui/Collapsible'
import { SummaryCard, KeyPoints } from '../../components/ui/ReadableOutput'
import { ConfidenceBadge, SeverityTag } from '../../components/ui/Provenance'

const PERSONA_META = {
  sponsor: { label: 'Sponsor', icon: Target },
  process_owner: { label: 'Process owner', icon: Users },
  second_line: { label: 'Second line', icon: ShieldCheck },
  operator: { label: 'Operator', icon: Crosshair },
}

const TRACE_ICON = { risk: Crosshair, framework: ShieldCheck, scope: Target }

function TraceChip({ trace }) {
  if (!trace || !trace.ref) return null
  const Icon = TRACE_ICON[trace.type] || Crosshair
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-surface-3 px-1.5 py-0.5 text-[11px] font-medium text-fg-muted ring-1 ring-inset ring-line">
      <Icon size={11} /> {trace.type}: {trace.ref}
    </span>
  )
}

// ── Persona guide ────────────────────────────────────────────────────────────
function PersonaGuide({ engagementId }) {
  const qc = useQueryClient()
  const [active, setActive] = useState(null)

  const { data } = useQuery({
    queryKey: ['interview-guide', engagementId],
    queryFn: () => getGuide(engagementId),
    refetchInterval: (q) => (q.state.data?.status === 'running' ? 2500 : false),
  })
  const build = useMutation({
    mutationFn: () => buildGuide(engagementId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['interview-guide', engagementId] }),
  })

  const status = data?.status
  const running = status === 'running' || build.isPending
  const personas = data?.personas || []
  const coverage = data?.coverage
  const activePersona = personas.find((p) => p.persona === active) || personas[0]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-fg">
          <Sparkles size={16} className="text-brand" /> Persona interview guide
        </div>
        <Button onClick={() => build.mutate()} disabled={running}>
          {running ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
          {running ? 'Building…' : status === 'ready' ? 'Rebuild guide' : 'Build guide'}
        </Button>
      </div>

      {status === 'no_data' && (
        <p className="text-sm text-fg-muted">{coverage?.summary || 'No planning context yet — run Topic Intelligence and Scope first.'}</p>
      )}
      {status === 'failed' && <p className="text-sm text-sev-high">{coverage?.summary || 'Guide generation failed.'}</p>}
      {!status || status === 'not_started' ? (
        <p className="text-sm text-fg-muted">
          Generate a persona-based guide grounded in this engagement's risks, frameworks and scope. Each question is traceable and comes with follow-ups.
        </p>
      ) : null}

      {status === 'ready' && personas.length > 0 && (
        <>
          {coverage && (
            <SummaryCard title="Coverage check" icon={ShieldCheck}>
              <div>{coverage.summary}</div>
              {coverage.gaps?.length > 0 && (
                <div className="mt-2">
                  <KeyPoints sign="gap" items={coverage.gaps.map((g) => ({ text: g, sign: 'gap' }))} />
                </div>
              )}
            </SummaryCard>
          )}

          <Segmented
            options={personas.map((p) => ({
              value: p.persona,
              label: PERSONA_META[p.persona]?.label || p.role_label || p.persona,
              icon: PERSONA_META[p.persona]?.icon,
            }))}
            value={activePersona?.persona}
            onChange={setActive}
            size="sm"
          />

          {activePersona && (
            <div className="space-y-3">
              <div className="rounded-xl border border-line bg-surface-2 p-3">
                <div className="text-xs font-medium uppercase tracking-wide text-fg-subtle">{activePersona.role_label}</div>
                <div className="mt-1 text-sm text-fg">{activePersona.goal}</div>
                {activePersona.opening && (
                  <div className="mt-2 rounded-lg bg-brand-faint px-3 py-2 text-sm italic text-fg-muted">"{activePersona.opening}"</div>
                )}
              </div>
              {(activePersona.questions || []).map((q, i) => (
                <Collapsible
                  key={i}
                  title={q.text}
                  badge={<TraceChip trace={q.traceability} />}
                >
                  {q.follow_ups?.length > 0 ? (
                    <div>
                      <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-fg-subtle">Follow-ups</div>
                      <KeyPoints sign="check" items={q.follow_ups.map((f) => ({ text: f, sign: 'check' }))} />
                    </div>
                  ) : (
                    <p className="text-sm text-fg-muted">No follow-ups.</p>
                  )}
                </Collapsible>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ── Live companion ─────────────────────────────────────────────────────────────
const DICTATE_LANGS = [
  { value: 'en-US', label: 'EN' },
  { value: 'nl-NL', label: 'NL' },
]

function SessionCard({ engagementId, session }) {
  const qc = useQueryClient()
  const [notes, setNotes] = useState(session.notes || '')
  const [dirty, setDirty] = useState(false)
  const [dictLang, setDictLang] = useState(DICTATE_LANGS[0].value)
  const invalidate = () => qc.invalidateQueries({ queryKey: ['interview-sessions', engagementId] })

  // Voice capture — appends each finalised phrase to the notes. Free, in-browser,
  // audio never leaves the device; the companion flow below is unchanged.
  const dictation = useSpeechDictation({
    lang: dictLang,
    onFinal: (phrase) => {
      setNotes((n) => (n.trim() ? `${n.trim()} ${phrase}` : phrase))
      setDirty(true)
    },
  })

  const save = useMutation({
    mutationFn: () => updateSession(engagementId, session.id, { notes }),
    onSuccess: () => { setDirty(false); invalidate() },
  })
  const analyse = useMutation({
    mutationFn: async () => { await updateSession(engagementId, session.id, { notes }); return analyseSession(engagementId, session.id) },
    onSuccess: () => { setDirty(false); invalidate() },
  })
  const remove = useMutation({ mutationFn: () => deleteSession(engagementId, session.id), onSuccess: invalidate })

  const a = session.analysis
  const analysing = session.status === 'analysing'
  const meta = PERSONA_META[session.persona]

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-fg">
          {meta?.icon ? <meta.icon size={15} className="text-brand" /> : <Users size={15} className="text-brand" />}
          {session.label || meta?.label || session.persona || 'Interview'}
        </div>
        <button onClick={() => remove.mutate()} className="rounded-lg p-1.5 text-fg-subtle transition hover:bg-surface-3 hover:text-sev-high" title="Delete session">
          <Trash2 size={15} />
        </button>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2">
        <div className="text-xs font-medium uppercase tracking-wide text-fg-subtle">Interviewee answers</div>
        {dictation.supported && (
          <div className="flex items-center gap-1.5">
            <div className="flex overflow-hidden rounded-md border border-line" role="group" aria-label="Dictation language">
              {DICTATE_LANGS.map((l) => (
                <button
                  key={l.value}
                  onClick={() => setDictLang(l.value)}
                  disabled={dictation.listening}
                  className={`px-1.5 py-0.5 text-[11px] font-medium transition disabled:opacity-50 ${dictLang === l.value ? 'bg-brand text-brand-fg' : 'bg-surface text-fg-muted hover:bg-surface-3'}`}
                >
                  {l.label}
                </button>
              ))}
            </div>
            <button
              onClick={dictation.toggle}
              className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium transition ${dictation.listening ? 'bg-sev-high/10 text-sev-high ring-1 ring-inset ring-sev-high/30' : 'bg-surface-3 text-fg-muted hover:text-brand'}`}
              title={dictation.listening ? 'Stop dictation' : 'Dictate the answers'}
            >
              {dictation.listening
                ? <><Square size={12} className="animate-pulse fill-current" /> Recording…</>
                : <><Mic size={13} /> Dictate</>}
            </button>
          </div>
        )}
      </div>

      <textarea
        value={notes}
        onChange={(e) => { setNotes(e.target.value); setDirty(true) }}
        placeholder="Type, paste or dictate the interviewee's answers here (no names — use roles). The companion proposes follow-ups, observations and candidate control gaps."
        rows={5}
        className="mt-1.5 w-full resize-y rounded-lg border border-line bg-surface px-3 py-2 text-sm text-fg outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
      />

      {dictation.listening && (
        <div className="mt-1.5 flex items-start gap-2 rounded-lg bg-brand-faint px-3 py-2 text-sm text-fg-muted">
          <Mic size={14} className="mt-0.5 shrink-0 text-brand" />
          <span className="min-w-0 flex-1">
            {dictation.interim || 'Listening — speak the answers; each phrase is added above.'}
          </span>
        </div>
      )}
      {dictation.error === 'not-allowed' && (
        <p className="mt-1.5 text-xs text-sev-high">Microphone access was blocked. Allow it in the browser to dictate, or type instead.</p>
      )}
      {!dictation.supported && (
        <p className="mt-1.5 text-xs text-fg-subtle">Voice input isn’t available in this browser — type or paste the answers.</p>
      )}

      <div className="mt-2 flex items-center gap-2">
        <Button onClick={() => { dictation.stop(); analyse.mutate() }} disabled={analysing || !notes.trim()}>
          {analysing ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {analysing ? 'Analysing…' : 'Run companion'}
        </Button>
        {dirty && (
          <Button variant="secondary" onClick={() => save.mutate()} disabled={save.isPending}>Save notes</Button>
        )}
        {a && (
          <Button variant="secondary" onClick={() => exportMinutes(engagementId, session.id)}>
            <FileDown size={15} /> Minutes
          </Button>
        )}
      </div>

      {a && (
        <div className="mt-4 space-y-3">
          {a.summary && <SummaryCard title="Companion summary">{a.summary}</SummaryCard>}
          {a.control_gaps?.length > 0 && (
            <Collapsible title="Candidate control gaps" count={a.control_gaps.length} icon={ShieldQuestion} defaultOpen>
              <ul className="space-y-2">
                {a.control_gaps.map((g, i) => (
                  <li key={i} className="rounded-lg border border-line bg-surface p-2.5">
                    <div className="flex items-start gap-2">
                      <SeverityTag level="must_fix">Verify</SeverityTag>
                      <div className="min-w-0 text-sm text-fg">{g.text || g}</div>
                    </div>
                    {g.verify && <div className="mt-1 text-xs text-fg-muted">How to verify: {g.verify}</div>}
                  </li>
                ))}
              </ul>
            </Collapsible>
          )}
          {a.observations?.length > 0 && (
            <Collapsible title="Observations" count={a.observations.length}>
              <ul className="space-y-1.5">
                {a.observations.map((o, i) => (
                  <li key={i} className="flex items-center justify-between gap-2 text-sm text-fg-muted">
                    <span className="min-w-0 flex-1">{o.text || o}</span>
                    {o.confidence && <ConfidenceBadge level={o.confidence} />}
                  </li>
                ))}
              </ul>
            </Collapsible>
          )}
          {a.follow_ups?.length > 0 && (
            <Collapsible title="Suggested follow-ups" count={a.follow_ups.length}>
              <KeyPoints sign="check" items={a.follow_ups.map((f) => ({ text: f, sign: 'check' }))} />
            </Collapsible>
          )}
          {a.minutes?.length > 0 && (
            <Collapsible title="Draft minutes" count={a.minutes.length}>
              <KeyPoints sign="info" items={a.minutes.map((m) => ({ text: m }))} />
            </Collapsible>
          )}
        </div>
      )}
    </Card>
  )
}

function CompanionPanel({ engagementId }) {
  const qc = useQueryClient()
  const [persona, setPersona] = useState('process_owner')
  const { data: sessions = [] } = useQuery({
    queryKey: ['interview-sessions', engagementId],
    queryFn: () => listSessions(engagementId),
    refetchInterval: (q) => (q.state.data?.some((s) => s.status === 'analysing') ? 2500 : false),
  })
  const create = useMutation({
    mutationFn: () => createSession(engagementId, { persona, label: `${PERSONA_META[persona]?.label || persona} interview` }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['interview-sessions', engagementId] }),
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-fg">
          <MessageSquarePlus size={16} className="text-brand" /> Live companion
        </div>
        <div className="flex items-center gap-2">
          <Segmented
            options={Object.entries(PERSONA_META).map(([value, m]) => ({ value, label: m.label, icon: m.icon }))}
            value={persona}
            onChange={setPersona}
            size="sm"
          />
          <Button onClick={() => create.mutate()} disabled={create.isPending}>
            <MessageSquarePlus size={15} /> New session
          </Button>
        </div>
      </div>
      <p className="text-xs text-fg-subtle">
        Privacy-first: type, paste or dictate answers — voice is transcribed on your device and never leaves the browser. Use roles not names. The companion proposes — you decide. Candidate control gaps are hypotheses to verify.
      </p>

      {sessions.length === 0 ? (
        <p className="text-sm text-fg-muted">No sessions yet. Start one to capture answers and get live follow-ups.</p>
      ) : (
        <div className="space-y-4">
          {sessions.map((s) => <SessionCard key={s.id} engagementId={engagementId} session={s} />)}
        </div>
      )}
    </div>
  )
}

export default function InterviewPage() {
  const { id } = useParams()
  const setActiveEngagement = useStore((s) => s.setActiveEngagement)
  const { data: eng } = useQuery({ queryKey: ['engagement', id], queryFn: () => getEngagement(id) })
  useEffect(() => { if (eng) setActiveEngagement(eng) }, [eng, setActiveEngagement])

  return (
    <PageContainer>
      <PageHeader
        back={{ to: `/engagements/${id}/planning`, label: 'Planning' }}
        badges={eng && <EntityBadge entity={eng.entity} />}
        title="Interview studio"
        subtitle={eng?.name}
      />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card className="p-5"><PersonaGuide engagementId={id} /></Card>
        <div>
          <SectionHeading>Companion & minutes</SectionHeading>
          <div className="mt-3"><CompanionPanel engagementId={id} /></div>
        </div>
      </div>
    </PageContainer>
  )
}
