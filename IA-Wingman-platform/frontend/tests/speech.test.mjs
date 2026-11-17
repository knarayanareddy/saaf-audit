// Tests for the shared speech module. No framework/deps — runs with:
//   node --test tests/speech.test.mjs   (from the frontend/ directory)
//
// The browser's SpeechSynthesis is stubbed rather than mocked away, because the
// two bugs this module has had were both about WHEN its events arrive: `onend`
// and `onerror` land a tick after `cancel()`, and a pause that lets one of them
// through advances the tour it was supposed to hold still.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

class FakeUtterance {
  constructor(text) { this.text = text }
}

class FakeSynth {
  constructor() { this.spoken = []; this.live = null }
  speak(u) { this.spoken.push(u.text); this.live = u }
  // A real cancel ends the utterance asynchronously. Everything this module
  // gets wrong, it gets wrong in that gap.
  cancel() {
    const u = this.live
    this.live = null
    if (u) queueMicrotask(() => u.onerror?.({ error: 'canceled' }))
  }
  getVoices() { return [] }
  addEventListener() {}
  // Pronounce `n` characters of the live utterance, then let it finish.
  say(n) { this.live?.onboundary?.({ charIndex: n }) }
  finish() { const u = this.live; this.live = null; u?.onend?.() }
}

globalThis.SpeechSynthesisUtterance = FakeUtterance
globalThis.window = { speechSynthesis: new FakeSynth(), SpeechSynthesisUtterance: FakeUtterance }
const synth = globalThis.window.speechSynthesis

const { narrate, speak, speechSupported } = await import('../src/lib/speech.js')
const settle = () => new Promise((r) => setTimeout(r, 0))

const fresh = () => { synth.spoken.length = 0; synth.live = null }

test('the stub looks like a browser that can speak', () => {
  assert.equal(speechSupported(), true)
})

test('a line that runs to its end reports done exactly once', async () => {
  fresh()
  let ends = 0
  narrate('One two three.', { onEnd: () => { ends += 1 } })
  assert.deepEqual(synth.spoken, ['One two three.'])
  synth.finish()
  synth.finish()
  await settle()
  assert.equal(ends, 1)
})

test('pausing does not report the line as finished', async () => {
  // The failure this prevents: pause cancels the utterance, the cancel arrives
  // as an error a tick later, and the tour steps to the next beat by itself.
  fresh()
  let ends = 0
  const line = narrate('Alpha bravo charlie.', { onEnd: () => { ends += 1 } })
  synth.say(6)
  line.pause()
  await settle()
  assert.equal(ends, 0, 'a pause is not an ending')
  assert.equal(line.speaking, false)
})

test('resuming picks up at the last word, and stays silent about it otherwise', async () => {
  fresh()
  let ends = 0
  const line = narrate('Alpha bravo charlie.', { onEnd: () => { ends += 1 } })
  synth.say(6)                       // "Alpha " spoken
  line.pause()
  await settle()
  line.resume()
  assert.deepEqual(synth.spoken, ['Alpha bravo charlie.', 'bravo charlie.'])
  assert.equal(ends, 0)
  synth.finish()
  await settle()
  assert.equal(ends, 1, 'the resumed half still ends the line')
})

test('a second pause carries the first one forward', async () => {
  fresh()
  const line = narrate('Alpha bravo charlie delta.', { onEnd: () => {} })
  synth.say(6)
  line.pause(); await settle(); line.resume()   // -> 'bravo charlie delta.'
  synth.say(6)
  line.pause(); await settle(); line.resume()   // -> 'charlie delta.'
  assert.equal(synth.spoken.at(-1), 'charlie delta.')
})

test('a voice that never reports a word boundary restarts rather than falling silent', async () => {
  // Some remote voices do not emit `boundary`. A worse resume is acceptable;
  // a button that produces silence is not.
  fresh()
  const line = narrate('Alpha bravo.', { onEnd: () => {} })
  line.pause(); await settle(); line.resume()
  assert.deepEqual(synth.spoken, ['Alpha bravo.', 'Alpha bravo.'])
})

test('cancelling stops the line and never reports it as finished', async () => {
  fresh()
  let ends = 0
  const line = narrate('Alpha bravo.', { onEnd: () => { ends += 1 } })
  line.cancel()
  await settle()
  assert.equal(ends, 0, 'a stop button must not advance anything')
  line.resume()
  assert.equal(synth.spoken.length, 1, 'a cancelled line cannot be resumed')
})

test('speak hands back a stop that works', async () => {
  fresh()
  let ends = 0
  const stop = speak('Alpha bravo.', { onEnd: () => { ends += 1 } })
  stop()
  await settle()
  assert.equal(ends, 0)
})

test('the platform listens in the language it speaks', async () => {
  // One constant, not two: the recogniser in the assistant panel and the voice
  // that reads replies back must not disagree about the language, and neither
  // follows `navigator.language` — that reports the browser's locale, which has
  // no opinion about what this interface is written in.
  const { SPEECH_LANG } = await import('../src/lib/speech.js')
  assert.equal(SPEECH_LANG, 'en-GB')

  const panel = readFileSync(new URL('../src/components/ai/AIChatPanel.jsx', import.meta.url), 'utf8')
  const code = panel.replace(/\/\/.*/g, '').replace(/\/\*[\s\S]*?\*\//g, '')
  assert.match(code, /recognition\.lang = SPEECH_LANG/, 'dictation does not use the shared language')
  assert.doesNotMatch(code, /navigator\.language/, 'dictation fell back to the browser locale')
})

test('dictation starts on the click itself, with nothing awaited first', () => {
  // The regression this locks down: a permission pre-check was added in front of
  // `recognition.start()`. Two things broke at once. The `await` spent the user
  // gesture the browser requires before it will open a microphone, and the early
  // return on "denied" meant the browser's own permission prompt — the only
  // dialog that can actually grant the microphone — never appeared at all.
  //
  // Explanations belong in `onerror`, after the browser has said what is wrong.
  const panel = readFileSync(new URL('../src/components/ai/AIChatPanel.jsx', import.meta.url), 'utf8')
  const from = panel.indexOf('const toggleListening')
  assert.ok(from > 0, 'toggleListening not found')
  const body = panel.slice(from, panel.indexOf('\n  }\n', from))
  const code = body.replace(/\/\/.*/g, '').replace(/\/\*[\s\S]*?\*\//g, '')

  assert.doesNotMatch(code, /async/, 'the click handler must not be async')
  assert.doesNotMatch(code, /\bawait\b/, 'nothing may be awaited before start()')
  assert.doesNotMatch(code, /permissions\s*\.?\s*\??\.query/, 'no permission gate in front of the prompt')
  assert.doesNotMatch(code, /enumerateDevices/, 'no device gate in front of the prompt')
  assert.match(code, /recognition\.start\(\)/, 'the handler still has to start recognition')
  assert.match(code, /onerror/, 'failures still have to be explained')
})
