import { useCallback, useEffect, useRef, useState } from 'react'

// Browser-native speech-to-text via the Web Speech API. It is free and fully
// client-side — the audio is transcribed in the browser and never leaves the
// device, which fits the interview module's privacy-first stance (no server,
// no paid AI, no recording stored). Degrades gracefully when the browser has
// no SpeechRecognition support: `supported` is false and the caller keeps the
// plain textarea.
const SR = typeof window !== 'undefined'
  ? (window.SpeechRecognition || window.webkitSpeechRecognition)
  : null

export function useSpeechDictation({ lang = 'en-US', onFinal } = {}) {
  const supported = !!SR
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const [error, setError] = useState(null)

  const recRef = useRef(null)
  const shouldListenRef = useRef(false)   // true while the user wants to keep dictating
  const onFinalRef = useRef(onFinal)
  const langRef = useRef(lang)
  useEffect(() => { onFinalRef.current = onFinal }, [onFinal])
  useEffect(() => { langRef.current = lang }, [lang])

  const stop = useCallback(() => {
    shouldListenRef.current = false
    setListening(false)
    setInterim('')
    try { recRef.current?.stop() } catch { /* no-op */ }
  }, [])

  const start = useCallback(() => {
    if (!SR) return
    setError(null)
    const rec = new SR()
    rec.continuous = true
    rec.interimResults = true
    rec.lang = langRef.current

    rec.onresult = (e) => {
      let interimText = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i]
        if (r.isFinal) {
          const t = (r[0]?.transcript || '').trim()
          if (t) onFinalRef.current?.(t)
        } else {
          interimText += r[0]?.transcript || ''
        }
      }
      setInterim(interimText)
    }
    rec.onerror = (e) => {
      if (e.error === 'no-speech' || e.error === 'aborted') return
      setError(e.error || 'dictation error')
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        shouldListenRef.current = false
        setListening(false)
      }
    }
    rec.onend = () => {
      setInterim('')
      // Chromium ends a session after a pause; restart while the user is still
      // dictating so continuous capture survives natural silences.
      if (shouldListenRef.current) {
        try { rec.start() } catch { /* no-op */ }
      } else {
        setListening(false)
      }
    }

    recRef.current = rec
    shouldListenRef.current = true
    try {
      rec.start()
      setListening(true)
    } catch { /* already started */ }
  }, [])

  const toggle = useCallback(() => { listening ? stop() : start() }, [listening, start, stop])

  useEffect(() => () => {
    shouldListenRef.current = false
    try { recRef.current?.stop() } catch { /* no-op */ }
  }, [])

  return { supported, listening, interim, error, start, stop, toggle }
}
