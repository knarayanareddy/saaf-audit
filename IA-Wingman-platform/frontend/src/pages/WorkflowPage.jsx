import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Play, Square, Sparkles, UserCheck, Check, Loader2, ArrowRight, Lock, AlertTriangle, RefreshCw,
} from 'lucide-react'
import PageContainer from '../components/layout/PageContainer'
import { PageHeader } from '../components/layout/PageHeader'
import Button from '../components/ui/Button'
import { fieldClass } from '../components/ui/Field'
import { narrate, cancelSpeech, speechSupported } from '../lib/speech'
import { useStore } from '../store/useStore'
import { EntityBadge } from '../components/ui/Badge'
import { getEngagements } from '../api/engagements'
import { getWorkflowMethod, getEngagementWorkflow } from '../api/workflow'
import { buildLayout, chainOf, tourFor, beatEdges, panGroups } from '../lib/workflowLayout'
import WorkflowCanvas from '../components/workflow/WorkflowCanvas'
import WorkflowList from '../components/workflow/WorkflowList'
import StatusRail from '../components/workflow/StatusRail'
import NodeInspector from '../components/workflow/NodeInspector'
import ShowcaseTour from '../components/workflow/ShowcaseTour'

// The map never collapses just because the window is a little narrow — losing the
// connections and the Play tour is a bigger loss than a little sideways scrolling.
// So it shrinks to a readability floor and then scrolls horizontally instead.
// MIN_SCALE is that floor (0.76 x the 1156px layout = the old 880px cut-off).
const MIN_SCALE = 0.76
// Only a genuinely small screen — a phone, a tablet in portrait — gets the
// per-phase timeline, where a vertical list really is the better shape.
const LIST_MAX_WIDTH = 620
const BAND_OF_STATUS = { in_planning: 'planning', in_fieldwork: 'fieldwork', in_reporting: 'reporting' }
const IDLE_TOUR = { playing: false, paused: false, index: 0 }
// Roughly what the floating caption bar covers at the bottom of the page. The
// tour scrolls its focus into the space ABOVE it, because a card centred in the
// window is a card sitting behind the sentence explaining it.
const CAPTION_SPACE = 104

// Whatever actually scrolls above this element — the page in the normal layout,
// an inner pane when the shell is given one. Found rather than assumed, so a
// later layout change cannot quietly break the tour's aim.
function scrollParentOf(el) {
  for (let n = el?.parentElement; n; n = n.parentElement) {
    const { overflowY } = getComputedStyle(n)
    if ((overflowY === 'auto' || overflowY === 'scroll') && n.scrollHeight > n.clientHeight) return n
  }
  return document.scrollingElement || document.documentElement
}

const LEGEND_LIVE = [
  { icon: Check, label: 'Complete', cls: 'text-brand' },
  { icon: Loader2, label: 'In progress', cls: 'text-brand' },
  { icon: ArrowRight, label: 'Ready', cls: 'text-sev-med' },
  { icon: Lock, label: 'Locked', cls: 'text-fg-subtle' },
]
const LEGEND_ALWAYS = [
  { icon: Sparkles, label: 'AI proposes', cls: 'text-brand' },
  { icon: UserCheck, label: 'You decide', cls: 'text-brand' },
]

function useReducedMotion() {
  const query = '(prefers-reduced-motion: reduce)'
  const [reduced, setReduced] = useState(() => typeof window !== 'undefined' && Boolean(window.matchMedia?.(query).matches))
  useEffect(() => {
    const mq = window.matchMedia?.(query)
    if (!mq) return undefined
    const onChange = (e) => setReduced(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return reduced
}

function useElementWidth(ref) {
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(el)
    return () => observer.disconnect()
  }, [ref])
  return width
}

export default function WorkflowPage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const engagementId = params.get('engagement') || ''
  const reducedMotion = useReducedMotion()
  const wrapRef = useRef(null)
  const railRef = useRef(null)
  const width = useElementWidth(wrapRef)

  const { data: engagements = [] } = useQuery({ queryKey: ['engagements'], queryFn: getEngagements })
  const methodQuery = useQuery({
    queryKey: ['workflow', 'method'],
    queryFn: getWorkflowMethod,
    staleTime: Infinity,
    enabled: !engagementId,
  })
  const liveQuery = useQuery({
    queryKey: ['workflow', 'engagement', engagementId],
    queryFn: () => getEngagementWorkflow(engagementId),
    enabled: Boolean(engagementId),
    retry: (count, err) => err?.response?.status !== 404 && count < 2,
    refetchInterval: (q) => (q.state.data?.nodes?.some((n) => n.status === 'in_progress') ? 3000 : false),
  })
  const query = engagementId ? liveQuery : methodQuery
  const wf = query.data
  const live = Boolean(engagementId && wf?.engagement)
  const layout = useMemo(() => (wf ? buildLayout(wf) : null), [wf])
  const beats = useMemo(() => (wf ? tourFor(wf) : []), [wf])

  const [hoverKey, setHoverKey] = useState(null)
  const [selectedKey, setSelectedKey] = useState(null)
  const [pendingOnly, setPendingOnly] = useState(false)
  const [tour, setTour] = useState(IDLE_TOUR)
  const tourVoice = useStore((s) => s.tourVoice)
  const setTourVoice = useStore((s) => s.setTourVoice)
  const voiceOn = tourVoice && speechSupported()
  const beat = tour.playing ? beats[tour.index] : null
  const mapMode = width > LIST_MAX_WIDTH
  const scale = layout && width ? Math.min(1, Math.max(MIN_SCALE, width / layout.width)) : 1

  const stopTour = useCallback(() => setTour(IDLE_TOUR), [])
  // Stepping is always a resume: asking for the next beat while paused and then
  // watching nothing happen is the kind of dead control that makes people stop
  // trusting a UI. It also keeps the model simple — a beat only ever *starts*
  // while running, so the effect below never has to ask whether it is paused.
  const goTo = useCallback(
    (i) => setTour((t) => ({ ...t, paused: false, index: Math.max(0, Math.min(beats.length - 1, i)) })),
    [beats.length],
  )

  useEffect(() => {
    setSelectedKey(null)
    setHoverKey(null)
    setPendingOnly(false)
    setTour(IDLE_TOUR)
  }, [engagementId])

  // The tour narrates itself, and the spoken line is what decides when to move
  // on — a stopwatch running underneath a voice always drifts out of step with
  // it. With the voice muted (or unsupported) the derived duration takes over.
  //
  // Pause is a real pause, not a restart. That is why the clock lives in a ref
  // and the beat is started by one effect but suspended by another: freezing
  // keeps what is left of the timer instead of throwing it away, and the
  // browser's own speech pause holds the sentence where it stands. Resume picks
  // it up mid-word, which is the entire point of a pause button during a demo.
  const clock = useRef({ id: null, left: 0, at: 0 })
  const voice = useRef(null)
  // Held in a ref rather than closed over, so `armClock` keeps one identity for
  // the life of the page. A live refetch rebuilds `beats`, and a callback that
  // changed with it would re-run the effect below and restart the sentence the
  // auditor is halfway through hearing.
  const beatCount = useRef(0)
  useEffect(() => { beatCount.current = beats.length }, [beats.length])

  const freezeClock = useCallback(() => {
    if (!clock.current.id) return
    clearTimeout(clock.current.id)
    clock.current.id = null
    clock.current.left = Math.max(0, clock.current.left - (Date.now() - clock.current.at))
  }, [])

  const armClock = useCallback((ms) => {
    clearTimeout(clock.current.id)
    clock.current.left = ms
    clock.current.at = Date.now()
    clock.current.id = setTimeout(() => {
      clock.current.id = null
      clock.current.left = 0
      setTour((t) => (t.index + 1 < beatCount.current ? { ...t, index: t.index + 1 } : IDLE_TOUR))
    }, ms)
  }, [])

  useEffect(() => {
    if (!tour.playing || !beat) return undefined
    const disarm = () => { clearTimeout(clock.current.id); clock.current.id = null; clock.current.left = 0 }

    if (voiceOn) {
      voice.current = narrate(beat.narration, {
        // A breath before the next step, so it never feels clipped.
        onEnd: () => { if (!reducedMotion) armClock(900) },
      })
      // A safety net for the case where the line never ends by itself, which
      // some browsers manage when a tab loses focus mid-sentence.
      if (!reducedMotion) armClock(beat.duration + 5000)
      return () => { voice.current?.cancel(); voice.current = null; disarm() }
    }

    if (reducedMotion) return undefined
    armClock(beat.duration)
    return disarm
    // Keyed on the beat id, not the object: a live refetch must not restart the
    // timer. `paused` is deliberately absent — pausing must not re-run this.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tour.playing, beat?.id, reducedMotion, voiceOn, armClock])

  useEffect(() => {
    if (!tour.playing) return
    if (tour.paused) {
      voice.current?.pause()
      freezeClock()
    } else if (clock.current.left > 0 && !clock.current.id) {
      // Only when the beat effect has not already re-armed for a new beat.
      voice.current?.resume()
      armClock(clock.current.left)
    }
  }, [tour.paused, tour.playing, armClock, freezeClock])

  // Leaving the page mid-sentence must not leave the browser talking.
  useEffect(() => cancelSpeech, [])

  // A beat lights up several stages at once, and they are often in different
  // bands — "your sign-off unlocks fieldwork" points at a card in Planning and
  // at one two bands below it, and "chasing the evidence" reaches from the
  // Document Request List down to Isabelle. Centring the first card left the
  // others off screen, so the tour narrated agents the auditor never saw.
  //
  // So the whole focus set is measured and centred as one block, with room kept
  // for the caption bar that floats over the bottom of the page. When the block
  // is taller than the window — those two beats are, on any normal screen — the
  // view pans: focus[0] first, then the rest of the set partway through the
  // beat. A tour is a camera, and a camera follows the arrow it is describing.
  useEffect(() => {
    if (!beat) return undefined
    const behavior = reducedMotion ? 'auto' : 'smooth'
    const cardFor = (key) => wrapRef.current?.querySelector(`[data-node="${key}"]`)
    const cards = beat.focus.map(cardFor).filter(Boolean)

    if (!cards.length) {
      railRef.current?.scrollIntoView({ block: 'center', behavior })
      return undefined
    }

    const scroller = scrollParentOf(cards[0])
    const page = scroller === document.scrollingElement
    const viewTop = page ? 0 : scroller.getBoundingClientRect().top
    const viewH = page ? window.innerHeight : scroller.clientHeight
    const usable = Math.max(120, viewH - CAPTION_SPACE)

    const boxOf = (keys) => {
      const rects = keys.map(cardFor).filter(Boolean).map((c) => c.getBoundingClientRect())
      if (!rects.length) return null
      const top = Math.min(...rects.map((r) => r.top))
      return { top, height: Math.max(...rects.map((r) => r.bottom)) - top }
    }
    // Centres a group, or shows its top card with a little headroom when even
    // the group does not fit.
    const show = (keys) => {
      const b = boxOf(keys)
      if (!b) return
      scroller.scrollBy({ top: b.top - (viewTop + (b.height <= usable ? (usable - b.height) / 2 : 24)), behavior })
    }

    const groups = panGroups(beat.focus, (keys) => boxOf(keys)?.height ?? 0, usable)
    if (!groups.length) return undefined
    show(groups[0])
    if (groups.length < 2) return undefined
    const pan = setTimeout(() => show(groups[1]), Math.round(beat.duration * 0.45))
    return () => clearTimeout(pan)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [beat?.id, reducedMotion])

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') {
        if (tour.playing) stopTour()
        else setSelectedKey(null)
      } else if (tour.playing && e.key === 'ArrowRight') {
        goTo(tour.index + 1)
      } else if (tour.playing && e.key === 'ArrowLeft') {
        goTo(tour.index - 1)
      } else if (tour.playing && !reducedMotion && (e.key === ' ' || e.key === 'Spacebar')) {
        // Space is how every media player pauses, and during a demo the mouse is
        // rarely on the caption bar. Never while the auditor is typing, and the
        // default is swallowed so the page does not scroll a screen down.
        const tag = e.target?.tagName
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target?.isContentEditable) return
        e.preventDefault()
        setTour((t) => ({ ...t, paused: !t.paused }))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [tour.playing, tour.index, reducedMotion, stopTour, goTo])

  const chain = useMemo(
    () => (layout && hoverKey && !beat ? chainOf(hoverKey, layout.edges) : null),
    [layout, hoverKey, beat],
  )
  const activeKeys = useMemo(() => {
    if (!layout) return null
    if (beat) return new Set(beat.focus)
    if (chain) return chain
    if (pendingOnly) return new Set(layout.nodes.filter((n) => n.pending_decisions > 0).map((n) => n.key))
    return null
  }, [layout, beat, chain, pendingOnly])
  const highlightEdges = useMemo(() => {
    if (!layout || !activeKeys) return null
    const list = beat
      ? beatEdges(beat, layout.edges)
      : layout.edges.filter((e) => activeKeys.has(e.from) && activeKeys.has(e.to))
    return new Set(list.map((e) => e.id))
  }, [layout, activeKeys, beat])

  const sortedEngagements = useMemo(
    () => [...engagements].sort((a, b) => a.name.localeCompare(b.name)),
    [engagements],
  )

  const openNode = (node) => navigate(`/engagements/${engagementId}/${node.base ? `${node.base}/` : ''}${node.route}`)
  const handleSelect = (node) => {
    if (tour.playing) return
    if (live && node.status !== 'locked') openNode(node)
    else setSelectedKey(node.key)
  }
  const jumpTo = (key) => {
    setSelectedKey(key)
    wrapRef.current?.querySelector(`[data-node="${key}"]`)?.scrollIntoView({
      block: 'center', behavior: reducedMotion ? 'auto' : 'smooth',
    })
  }
  const toggleVoice = () => {
    voice.current?.cancel()
    voice.current = null
    cancelSpeech()
    setTourVoice(!tourVoice)
  }

  const startTour = () => {
    setSelectedKey(null)
    setHoverKey(null)
    setPendingOnly(false)
    setTour({ playing: true, paused: false, index: 0 })
  }
  const changeAudit = (id) => setParams(id ? { engagement: id } : {})

  const selected = selectedKey && layout ? layout.byKey[selectedKey] : null
  const nextNode = live && wf.next_gate && layout ? layout.byKey[wf.next_gate] : null
  const currentBand = live ? BAND_OF_STATUS[wf.engagement.status] : null
  const notFound = liveQuery.error?.response?.status === 404
  const legend = live ? [...LEGEND_LIVE, ...LEGEND_ALWAYS] : LEGEND_ALWAYS

  return (
    <PageContainer width="wide">
      <PageHeader
        badges={live ? <EntityBadge entity={wf.engagement.entity} /> : null}
        title="Workflow"
        subtitle={live
          ? `${wf.engagement.name}${wf.engagement.audit_code ? ` · ${wf.engagement.audit_code}` : ''}`
          : 'How an audit moves through IA Wingman — where AI proposes and where you decide.'}
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <label htmlFor="wf-audit" className="text-caption">Audit</label>
          <select
            id="wf-audit"
            value={engagementId}
            onChange={(e) => changeAudit(e.target.value)}
            className={fieldClass({ className: 'min-w-0 max-w-[20rem] cursor-pointer' })}
          >
            <option value="">Method overview</option>
            <optgroup label="Audits">
              {sortedEngagements.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
            </optgroup>
          </select>
        </div>
        <Button
          variant={tour.playing ? 'secondary' : 'primary'}
          size="sm"
          disabled={!layout}
          onClick={tour.playing ? stopTour : startTour}
        >
          {tour.playing ? <><Square size={14} /> Stop tour</> : <><Play size={14} /> Play</>}
        </Button>
        {live && liveQuery.isFetching && (
          <span className="inline-flex items-center gap-1.5 text-xs text-fg-subtle">
            <RefreshCw size={12} className="animate-spin" /> Updating
          </span>
        )}
      </div>

      {wf && (
        <div ref={railRef} className={`mt-4 rounded-lg py-2 transition-shadow duration-300 ${beat?.id === 'lifecycle' ? 'wf-focus bg-surface px-3' : ''}`}>
          <StatusRail statuses={wf.statuses} current={live ? wf.engagement.status : null} />
        </div>
      )}

      {wf && (
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          {live ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 text-[13px] text-fg-muted">
                <Check size={13} className="text-brand" />
                <span className="font-medium tabular-nums text-fg">{wf.completed}/{wf.total}</span> complete
              </span>
              <button
                type="button"
                aria-pressed={pendingOnly}
                disabled={!wf.pending.total}
                onClick={() => setPendingOnly((v) => !v)}
                className={`inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-[13px] transition-colors duration-150 disabled:opacity-50 focus:outline-none focus-visible:shadow-ring ${
                  pendingOnly ? 'border-sev-med/40 bg-sev-med/12 text-sev-med' : 'border-line bg-surface text-fg-muted hover:bg-surface-2'
                }`}
              >
                <UserCheck size={13} />
                <span className="font-medium tabular-nums">{wf.pending.total}</span> awaiting you
              </button>
              {nextNode ? (
                <button
                  type="button"
                  onClick={() => jumpTo(nextNode.key)}
                  className="inline-flex h-7 min-w-0 items-center gap-1.5 rounded-md border border-line bg-surface px-2 text-[13px] text-fg transition-colors duration-150 hover:bg-surface-2 focus:outline-none focus-visible:shadow-ring"
                >
                  <ArrowRight size={13} className="shrink-0 text-sev-med" />
                  <span className="truncate">Next gate: <span className="font-semibold">{nextNode.label}</span></span>
                </button>
              ) : (
                <span className="text-[13px] text-fg-muted">All gates cleared</span>
              )}
            </div>
          ) : (
            <p className="text-[13px] text-fg-muted">
              Choose an audit to see where it stands. Hover a step to trace what it waits on and what it unlocks.
            </p>
          )}
          <ul className="flex flex-wrap items-center gap-x-4 gap-y-1" aria-label="Legend">
            {legend.map(({ icon: Icon, label, cls }) => (
              <li key={label} className="inline-flex items-center gap-1.5 text-xs text-fg-muted">
                <Icon size={13} className={cls} aria-hidden="true" /> {label}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div ref={wrapRef} className="relative mt-5">
        {query.isLoading && <div className="h-[520px] animate-pulse rounded-lg bg-surface-3" />}

        {query.isError && (
          <div className="rounded-lg border border-line bg-surface p-6 text-center">
            <AlertTriangle size={18} className="mx-auto text-sev-med" />
            <p className="mt-2 text-sm font-medium text-fg">
              {notFound ? 'This audit could not be found.' : 'The workflow could not be loaded.'}
            </p>
            <div className="mt-4 flex justify-center">
              {notFound ? (
                <Button variant="secondary" onClick={() => changeAudit('')}>Show the method overview</Button>
              ) : (
                <Button variant="secondary" onClick={() => query.refetch()}><RefreshCw size={14} /> Try again</Button>
              )}
            </div>
          </div>
        )}

        {layout && width > 0 && (mapMode ? (
          // Scrolls sideways only when the map is wider than the page; the
          // inspector popover sits OUTSIDE this box so it stays pinned to the
          // visible edge instead of scrolling away with the canvas.
          <div className="-my-2 overflow-x-auto py-2">
          <WorkflowCanvas
            key={engagementId || 'method'}
            layout={layout}
            wf={wf}
            live={live}
            scale={scale}
            activeKeys={activeKeys}
            highlightEdges={highlightEdges}
            hoverKey={hoverKey}
            beat={beat}
            particles={Boolean(beat?.particles && !tour.paused && !reducedMotion)}
            currentBand={currentBand}
            onSelect={handleSelect}
            onHover={setHoverKey}
          />
          </div>
        ) : (
          <WorkflowList
            layout={layout}
            wf={wf}
            live={live}
            activeKeys={activeKeys}
            focusKeys={beat ? new Set(beat.focus) : null}
            currentBand={currentBand}
            onSelect={handleSelect}
          />
        ))}

        {selected && !tour.playing && (
          <NodeInspector
            node={selected}
            layout={layout}
            wf={wf}
            live={live}
            className={mapMode
              ? 'absolute w-80'
              : 'fixed inset-x-3 bottom-3 max-h-[75vh] overflow-y-auto sm:left-auto sm:right-6 sm:w-80'}
            style={mapMode
              ? {
                  top: Math.max(0, selected.y * scale - 8),
                  ...(selected.x + selected.w / 2 > layout.width / 2 ? { left: 12 } : { right: 12 }),
                }
              : undefined}
            onOpen={openNode}
            onClose={() => setSelectedKey(null)}
            onJump={jumpTo}
          />
        )}
      </div>

      {beat && (
        <ShowcaseTour
          beats={beats}
          index={tour.index}
          paused={tour.paused}
          reducedMotion={reducedMotion}
          onPrev={() => goTo(tour.index - 1)}
          onNext={() => (tour.index + 1 < beats.length ? goTo(tour.index + 1) : stopTour())}
          onJump={goTo}
          onTogglePause={() => setTour((t) => ({ ...t, paused: !t.paused }))}
          voice={tourVoice}
          voiceAvailable={speechSupported()}
          onToggleVoice={toggleVoice}
          onStop={stopTour}
        />
      )}
    </PageContainer>
  )
}
