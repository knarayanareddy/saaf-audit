import { useCallback, useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { X, Send, Sparkles, Mic, MicOff, Square, Volume2, VolumeX } from 'lucide-react'
import { useStore } from '../../store/useStore'
import { streamChat, getCopilotMessages, patchCopilotProposal, runCopilotStage } from '../../api/ai'
import { createEngagement, updateEngagement } from '../../api/engagements'
import { detailPayload } from '../../lib/engagementEdit'
import { addFramework } from '../../api/planning'
import { promoteTestToFinding } from '../../api/racm'
import ActionCard from './ActionCard'
import { narrate, cancelSpeech, SPEECH_LANG } from '../../lib/speech'
import ReadableText from '../ui/ReadableText'
import Segmented from '../ui/Segmented'
import Tooltip from '../ui/Tooltip'

// Chromium/Edge/Safari only — not Firefox. Feature-detected, never assumed.
const SpeechRecognitionCtor =
  typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null

// What the browser tells us when dictation fails, in words the reader can act
// on. `aborted` is left out on purpose: that is what stopping it yourself looks
// like, and a toast for it would fire every time you finish a sentence.
const MIC_ERRORS = {
  'not-allowed': 'The microphone is blocked for this site. Allow it in your browser settings, then try again.',
  'service-not-allowed': 'This browser will not start its speech service. Dictation is unavailable here.',
  'audio-capture': 'The microphone could not be opened. Check that one is connected and selected as the input device.',
  network: 'Speech recognition needs the network and could not reach it.',
  'no-speech': 'Nothing was picked up — check the microphone is not muted.',
  'language-not-supported': 'This browser cannot recognise the language the page is set to.',
}


export default function AIChatPanel() {
  const navigate = useNavigate()
  const open = useStore((s) => s.chatOpen)
  const setChatOpen = useStore((s) => s.setChatOpen)
  const activeEngagement = useStore((s) => s.activeEngagement)
  const setActiveEngagement = useStore((s) => s.setActiveEngagement)
  const showToast = useStore((s) => s.showToast)
  const speakReplies = useStore((s) => s.speakReplies)
  const setSpeakReplies = useStore((s) => s.setSpeakReplies)
  const chatVerbosity = useStore((s) => s.chatVerbosity)
  const setChatVerbosity = useStore((s) => s.setChatVerbosity)
  const qc = useQueryClient()

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const scrollRef = useRef(null)
  const streamingRef = useRef(false)
  const messagesLenRef = useRef(0)

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight)
  }, [messages])

  useEffect(() => { streamingRef.current = streaming }, [streaming])
  useEffect(() => { messagesLenRef.current = messages.length }, [messages])

  // Reads a completed reply aloud — opt-in (speakReplies defaults to off).
  //
  // A long reply takes a minute to read out, so the reading has to be
  // interruptible: turning the toggle off, closing the panel or leaving the page
  // stops it mid-word. A setting that only governs the NEXT reply leaves someone
  // sitting through one they have already read.
  const reading = useRef(null)
  const [speaking, setSpeaking] = useState(false)

  const stopSpeaking = useCallback(() => {
    reading.current?.cancel()
    reading.current = null
    setSpeaking(false)
  }, [])

  const speak = (text) => {
    if (!speakReplies) return
    reading.current = narrate(text, { onEnd: () => { reading.current = null; setSpeaking(false) } })
    setSpeaking(true)
  }

  useEffect(() => { if (!speakReplies) stopSpeaking() }, [speakReplies, stopSpeaking])
  useEffect(() => { if (!open) stopSpeaking() }, [open, stopSpeaking])
  useEffect(() => () => cancelSpeech(), [])

  // Dictation — feature-detected; the mic button simply doesn't render when
  // unsupported.
  //
  // Every failure here used to end at `setListening(false)`, so a blocked
  // microphone looked exactly like a broken button: it lit up, went out, and
  // said nothing. The browser reports why in `event.error`, and there are only
  // a handful of reasons, so each one gets a sentence that tells you what to do
  // about it.
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef(null)

  useEffect(() => () => recognitionRef.current?.stop(), [])

  // NOTHING may be awaited between the click and `recognition.start()`.
  //
  // The browser only opens a microphone on a user gesture, and an `await`
  // spends it: by the time the promise resolves, the click is no longer what
  // the call is attached to and Chrome refuses. A permission pre-check here is
  // worse than useless for a second reason too — when it answers "denied" and
  // we return early, the browser's OWN prompt never appears, so the one dialog
  // that could have granted the microphone is the thing we stood in front of.
  //
  // Diagnosis therefore belongs after the attempt, in `onerror`, where the
  // browser has said what is actually wrong. This handler stays synchronous.
  const toggleListening = () => {
    if (!SpeechRecognitionCtor) return
    if (listening) {
      recognitionRef.current?.stop()
      return
    }

    // Dictating into a speaker that is reading the last reply out loud puts the
    // assistant's own voice into the transcript.
    stopSpeaking()

    const recognition = new SpeechRecognitionCtor()
    recognition.lang = SPEECH_LANG
    // Interim results are what make the button feel alive: words land in the box
    // while you talk instead of after you stop.
    recognition.interimResults = true
    recognition.continuous = true
    recognition.maxAlternatives = 1

    // Only settled text is kept. Interim guesses are shown and then replaced, so
    // the draft never keeps a word the browser changed its mind about.
    let settled = ''
    const before = input
    recognition.onresult = (event) => {
      let pending = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) settled += `${result[0].transcript.trim()} `
        else pending += result[0].transcript
      }
      const dictated = `${settled}${pending}`.trim()
      setInput(before && dictated ? `${before} ${dictated}` : dictated || before)
    }
    recognition.onerror = (event) => {
      setListening(false)
      // The browser's own code goes in the message. Two different code paths
      // once carried the identical sentence, which made the report "it says
      // blocked" impossible to act on: it named the words, not the cause.
      const message = MIC_ERRORS[event.error]
      console.warn('[dictation] speech recognition failed', { error: event.error, message: event.message, lang: SPEECH_LANG })
      showToast(`${message || 'Dictation failed.'} (${event.error})`, 'error')
    }
    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition
    try {
      recognition.start()
      setListening(true)
    } catch {
      // Chrome throws InvalidStateError when a previous session is still closing.
      showToast('The microphone is still busy — try again in a moment. (start-threw)', 'error')
    }
  }

  const applyHistory = (history) =>
    setMessages(
      history.map((m) => ({
        role: m.role,
        content: m.content,
        isProactive: !!m.is_proactive,
        // tc.status is live from the backend (pending/accepted/dismissed/expired) —
        // a reloaded 'pending' proposal is still fully actionable, not just a record.
        actions: (m.tool_calls || []).map((tc) => ({ ...tc, id: crypto.randomUUID() })),
      })),
    )

  // Restore this engagement's persisted thread on open/switch, so the
  // conversation survives a refresh instead of always starting empty.
  useEffect(() => {
    let cancelled = false
    if (!activeEngagement?.id) {
      setMessages([])
      return
    }
    getCopilotMessages(activeEngagement.id)
      .then((history) => { if (!cancelled) applyHistory(history) })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [activeEngagement?.id])

  // The copilot can post a message on its own initiative (M10's proactive
  // check-ins) — the SSE stream only ever delivers messages for a turn THIS
  // tab started, so a background nudge needs its own, lighter poll to
  // actually show up while the panel is open. Skips while a turn is
  // streaming, and only applies the fetch when the persisted thread has
  // genuinely grown, so it never fights an in-progress local update.
  useEffect(() => {
    if (!open || !activeEngagement?.id) return
    const engagementId = activeEngagement.id
    const interval = setInterval(() => {
      if (streamingRef.current) return
      getCopilotMessages(engagementId)
        .then((history) => { if (history.length > messagesLenRef.current) applyHistory(history) })
        .catch(() => {})
    }, 20000)
    return () => clearInterval(interval)
  }, [open, activeEngagement?.id])

  const updateLast = (fn) =>
    setMessages((m) => {
      const copy = [...m]
      copy[copy.length - 1] = fn(copy[copy.length - 1])
      return copy
    })

  const send = async () => {
    const text = input.trim()
    if (!text || streaming) return
    const nextMessages = [...messages, { role: 'user', content: text }]
    setMessages(nextMessages)
    setInput('')
    setStreaming(true)
    setMessages((m) => [...m, { role: 'assistant', content: '', actions: [] }])

    await streamChat(
      { messages: nextMessages, engagementId: activeEngagement?.id, verbosity: chatVerbosity },
      {
        onDelta: (delta) => updateLast((last) => ({ ...last, content: last.content + delta })),
        onAction: (action) =>
          updateLast((last) => ({
            ...last,
            actions: [...(last.actions || []), { ...action, id: crypto.randomUUID(), status: 'pending' }],
          })),
        onComplete: (fullText) => { setStreaming(false); speak(fullText) },
        onError: (err) => {
          updateLast((last) => ({ ...last, content: last.content || `⚠ ${err}` }))
          setStreaming(false)
        },
      },
    )
  }

  const setActionStatus = (msgIdx, actionId, status) =>
    setMessages((m) =>
      m.map((msg, i) =>
        i !== msgIdx ? msg : { ...msg, actions: msg.actions.map((a) => (a.id === actionId ? { ...a, status } : a)) },
      ),
    )

  // Best-effort: the proposal's persisted status is what survives a refresh,
  // but a failure here should never block the local UI from reflecting what
  // the auditor just did — the side effect (if any) has already happened.
  const persistStatus = (proposalId, status) => {
    if (!proposalId) return
    patchCopilotProposal(proposalId, status).catch(() => {})
  }

  const dismissAction = (msgIdx, action) => {
    setActionStatus(msgIdx, action.id, 'dismissed')
    persistStatus(action.proposal_id, 'dismissed')
  }

  const acceptAction = async (msgIdx, action) => {
    try {
      if (action.tool === 'propose_create_engagement') {
        await createEngagement({ ...action.input, status: 'in_planning', team_members: [] })
        qc.invalidateQueries({ queryKey: ['engagements'] })
        qc.invalidateQueries({ queryKey: ['stats'] })
        showToast('Engagement created')
      } else if (action.tool === 'propose_add_framework') {
        if (!activeEngagement) {
          showToast('Open an engagement first', 'error')
          return
        }
        await addFramework(activeEngagement.id, {
          framework_code: action.input.framework_code || action.input.framework_name?.slice(0, 20) || 'FW',
          framework_name: action.input.framework_name,
          applicability_rationale: action.input.applicability_rationale || '',
        })
        qc.invalidateQueries({ queryKey: ['framework-requirements', activeEngagement.id] })
        qc.invalidateQueries({ queryKey: ['engagement', activeEngagement.id] })
        showToast('Framework added')
      } else if (action.tool === 'propose_run_stage') {
        if (!activeEngagement) {
          showToast('Open an engagement first', 'error')
          return
        }
        const result = await runCopilotStage(activeEngagement.id, action.input.stage_key)
        qc.invalidateQueries({ queryKey: ['agent-pack', activeEngagement.id] })
        qc.invalidateQueries({ queryKey: ['copilot-tasks', activeEngagement.id] })
        showToast(
          result?.status === 'already_running'
            ? 'Already running in the background — it will land in Ready for Review'
            : 'Started — it will appear in Ready for Review when done',
        )
      } else if (action.tool === 'propose_promote_finding') {
        if (!activeEngagement) {
          showToast('Open an engagement first', 'error')
          return
        }
        await promoteTestToFinding(activeEngagement.id, action.input.test_id)
        qc.invalidateQueries({ queryKey: ['racm', activeEngagement.id] })
        qc.invalidateQueries({ queryKey: ['findings', activeEngagement.id] })
        showToast('Finding created')
      } else if (action.tool === 'propose_update_engagement_status') {
        if (!activeEngagement) {
          showToast('Open an engagement first', 'error')
          return
        }
        await updateEngagement(activeEngagement.id, { status: action.input.new_status })
        qc.invalidateQueries({ queryKey: ['engagement', activeEngagement.id] })
        qc.invalidateQueries({ queryKey: ['engagements'] })
        showToast('Engagement status updated')
      } else if (action.tool === 'propose_update_engagement_details') {
        if (!activeEngagement) {
          showToast('Open an engagement first', 'error')
          return
        }
        const changes = detailPayload(action.input, activeEngagement)
        if (!Object.keys(changes).length) {
          showToast('Nothing to change')
          return
        }
        const updated = await updateEngagement(activeEngagement.id, changes)
        setActiveEngagement(updated)
        qc.invalidateQueries({ queryKey: ['engagement', activeEngagement.id] })
        qc.invalidateQueries({ queryKey: ['engagements'] })
        showToast('Engagement updated')
      } else if (action.tool === 'propose_open_engagement') {
        navigate(`/engagements/${action.input.engagement_id}/agents`)
      }
      setActionStatus(msgIdx, action.id, 'accepted')
      persistStatus(action.proposal_id, 'accepted')
    } catch {
      showToast('Action failed', 'error')
    }
  }

  return (
    <>
      {/* Backdrop on narrow screens where the panel overlays instead of pushing */}
      {open && <div className="fixed inset-0 z-30 bg-black/30 xl:hidden" onClick={() => setChatOpen(false)} />}

      {/* Always mounted so streaming + message history survive toggling. The
          outer wrapper animates width on xl (pushes content) and slides as a
          fixed overlay below xl (never squeezes content). Inner is fixed-width
          so text does not reflow during the animation. */}
      <div
        className={`fixed inset-y-0 right-0 z-40 min-w-0 shrink-0 overflow-hidden transition-all duration-300 ease-out xl:static ${
          open ? 'w-[440px] translate-x-0' : 'w-[440px] translate-x-full xl:w-0 xl:translate-x-0'
        }`}
      >
        <div className="flex h-full w-[440px] flex-col border-l border-line bg-surface shadow-elevated xl:shadow-none">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <div className="flex items-center gap-2 font-semibold text-brand">
              <Sparkles size={18} /> IA Wingman Assistant
            </div>
            <div className="flex items-center gap-1">
              {/* While a reply is being read the same button stops it, because that
                  is the button someone reaches for. It only turns the setting
                  off once there is nothing left to interrupt. */}
              <button
                onClick={() => (speaking ? stopSpeaking() : setSpeakReplies(!speakReplies))}
                title={speaking
                  ? 'Reading aloud — click to stop'
                  : speakReplies ? 'Reading replies aloud — click to turn off' : 'Read replies aloud (off by default)'}
                className={`rounded-lg p-1 transition hover:bg-surface-3 ${speakReplies ? 'text-brand' : 'text-fg-subtle hover:text-fg'}`}
                aria-label={speaking ? 'Stop reading aloud' : 'Toggle read replies aloud'}
              >
                {speaking ? <Square size={16} /> : speakReplies ? <Volume2 size={16} /> : <VolumeX size={16} />}
              </button>
              <button
                onClick={() => setChatOpen(false)}
                className="rounded-lg p-1 text-fg-subtle transition hover:bg-surface-3 hover:text-fg"
                aria-label="Close assistant"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* How long an answer should be. Kept per browser, switchable mid-conversation
              — "Brief" answers the question and stops, "Detailed" reasons out loud. */}
          <div className="flex items-center justify-between border-b border-line px-4 py-2">
            <span className="text-[11px] text-fg-subtle">Answer length</span>
            <Segmented
              size="sm"
              value={chatVerbosity}
              onChange={setChatVerbosity}
              options={[{ value: 'brief', label: 'Brief' }, { value: 'detailed', label: 'Detailed' }]}
            />
          </div>

          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="mt-8 text-center text-sm text-fg-muted">
                Ask about regulations, frameworks, or scoping. You can also say things like
                “add an AML framework to this audit” or “create an ESG audit”.
                {activeEngagement && (
                  <span className="mt-2 block text-xs text-fg-subtle">Context: {activeEngagement.name}</span>
                )}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex flex-col items-start'}>
                {m.isProactive && (
                  <div className="mb-1 flex items-center gap-1 text-[11px] font-medium text-brand">
                    <Sparkles size={11} /> Copilot checked in
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                    m.role === 'user' ? 'whitespace-pre-wrap bg-brand text-brand-fg' : 'bg-surface-3 text-fg'
                  }`}
                >
                  {/* The assistant's markdown is rendered (bold, bullets, code) instead
                      of printed with its asterisks showing. Your own message is shown
                      exactly as you typed it. */}
                  {m.role === 'assistant' && m.content
                    ? <ReadableText value={m.content} />
                    : m.content || (m.actions?.length ? null : '…')}
                </div>
                {m.actions?.map((a) => (
                  <div key={a.id} className="w-[85%]">
                    <ActionCard
                      action={a}
                      onAccept={() => acceptAction(i, a)}
                      onDismiss={() => dismissAction(i, a)}
                    />
                  </div>
                ))}
              </div>
            ))}
          </div>

          <div className="border-t border-line p-3">
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    send()
                  }
                }}
                placeholder={listening ? 'Listening…' : 'Ask anything… (Enter to send)'}
                rows={1}
                className="flex-1 resize-none rounded-lg border border-line bg-surface px-3 py-2 text-sm text-fg outline-none transition placeholder:text-fg-subtle focus:border-brand focus:ring-2 focus:ring-brand/20"
              />
              {SpeechRecognitionCtor && (
                <button
                  onClick={toggleListening}
                  title={listening ? 'Stop dictating' : `Dictate in English (${SPEECH_LANG}) — Chrome/Edge/Safari only`}
                  className={`rounded-lg p-2 transition ${
                    listening
                      ? 'bg-sev-high/12 text-sev-high hover:bg-sev-high/20'
                      : 'border border-line text-fg-subtle hover:bg-surface-3 hover:text-fg'
                  }`}
                >
                  {listening ? <MicOff size={16} /> : <Mic size={16} />}
                </button>
              )}
              <Tooltip label="Send (Enter)" side="top">
                <button
                  onClick={send}
                  disabled={streaming || !input.trim()}
                  aria-label="Send"
                  className="rounded-lg bg-brand p-2 text-brand-fg transition hover:bg-brand-hover disabled:opacity-40"
                >
                  <Send size={16} />
                </button>
              </Tooltip>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
