// How this platform speaks. One module, because two features now read text aloud
// — the assistant's replies and the workflow tour — and they should sound the
// same. Built on the browser's own SpeechSynthesis: no dependency, no API cost,
// nothing leaves the machine.

export const speechSupported = () =>
  typeof window !== 'undefined' && typeof window.speechSynthesis !== 'undefined'

// The voice list is populated asynchronously and is empty on the first call in
// most browsers, so it is cached on the `voiceschanged` event instead of being
// looked up at speak time.
let voices = []
let listening = false

function refreshVoices() {
  try {
    voices = window.speechSynthesis.getVoices() || []
  } catch {
    voices = []
  }
}

function ensureVoices() {
  if (!speechSupported()) return
  if (!listening) {
    listening = true
    window.speechSynthesis.addEventListener?.('voiceschanged', refreshVoices)
  }
  if (!voices.length) refreshVoices()
}

// The language this platform speaks AND listens in. English, because the
// interface is: a Dutch voice reading English text is close to unintelligible,
// and a Dutch recogniser transcribing English speech is worse — it returns
// confident nonsense rather than nothing. Deliberately not `navigator.language`,
// which reports the browser's locale and has no opinion about the app's.
export const SPEECH_LANG = 'en-GB'

// Falls back to the browser default rather than staying silent.
export function pickVoice() {
  ensureVoices()
  if (!voices.length) return null
  return (
    voices.find((v) => v.lang === 'en-GB' && v.localService)
    || voices.find((v) => v.lang === 'en-GB')
    || voices.find((v) => v.lang === 'en-US' && v.localService)
    || voices.find((v) => v.lang?.startsWith('en'))
    || null
  )
}

/**
 * Narrate one line, with a pause that actually resumes and a stop that actually
 * stops. Returns a handle: `{ pause, resume, cancel, speaking }`.
 *
 * `speechSynthesis.pause()` is the obvious way to do this and it is not
 * dependable. Chrome drops a paused utterance after a short while, so
 * `resume()` returns to silence and the reader is left with a dead button —
 * which is exactly the bug this replaces.
 *
 * So a pause here cancels the utterance and remembers how far the voice got:
 * the `boundary` event reports the character index of each word as it is
 * spoken. Resume speaks the remainder, and the listener hears it continue from
 * the current word. Where `boundary` never fires — some remote voices do not
 * emit it — the offset stays at zero and resume restarts the sentence. That is
 * a worse resume, never a silent one.
 *
 * `onEnd` fires exactly once, and never because of a pause or a cancel: a
 * caller that advances a tour on it must not be advanced by its own stop button.
 */
export function narrate(text, { rate = 0.95, pitch = 1, onEnd } = {}) {
  let done = false
  let paused = false
  let spoken = 0        // characters confirmed spoken, across pauses
  let sinceStart = 0    // characters spoken within the current utterance
  // The utterance we are still listening to. A pause or a cancel clears it
  // BEFORE cancelling, because `onend` and `onerror` arrive a tick later — a
  // flag reset on the next line would already be back to false by then, and the
  // tour would advance on its own pause button.
  let live = null

  const finish = () => {
    if (done) return
    done = true
    onEnd?.()
  }

  const startAt = (from) => {
    const rest = text.slice(from)
    if (!rest) return finish()
    const utterance = new SpeechSynthesisUtterance(rest)
    const voice = pickVoice()
    if (voice) utterance.voice = voice
    utterance.lang = voice?.lang || SPEECH_LANG
    utterance.rate = rate
    utterance.pitch = pitch
    sinceStart = 0
    utterance.onboundary = (e) => { sinceStart = e.charIndex ?? sinceStart }
    utterance.onend = () => { if (utterance === live) finish() }
    // A cancel counts as an error in some browsers; only an error on the
    // utterance we are still listening to means the line ended by itself.
    utterance.onerror = () => { if (utterance === live) finish() }
    live = utterance
    window.speechSynthesis.speak(utterance)
  }

  if (!speechSupported() || !text) {
    // Still hand back the callback so a caller can rely on being told "done".
    finish()
    return { pause() {}, resume() {}, cancel() {}, get speaking() { return false } }
  }

  cancelSpeech()
  startAt(0)

  return {
    pause() {
      if (done || paused) return
      paused = true
      spoken += sinceStart
      live = null
      cancelSpeech()
    },
    resume() {
      if (done || !paused) return
      paused = false
      startAt(spoken)
    },
    cancel() {
      if (done) return
      done = true     // set first: nothing this cancel triggers may call onEnd
      live = null
      cancelSpeech()
    },
    get speaking() { return !done && !paused },
  }
}

/**
 * Speak one line and forget about it — for callers with nothing to pause.
 * @returns {() => void} a cancel function.
 */
export function speak(text, options = {}) {
  const handle = narrate(text, options)
  return () => handle.cancel()
}

export function cancelSpeech() {
  if (!speechSupported()) return
  try {
    window.speechSynthesis.cancel()
  } catch {
    /* a browser that refuses to cancel is not worth crashing the page over */
  }
}
