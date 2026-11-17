import { ChevronLeft, ChevronRight, Pause, Play, Volume2, VolumeX, X } from 'lucide-react'

const CONTROL = 'flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-fg-muted transition-colors duration-150 hover:bg-surface-3 hover:text-fg disabled:pointer-events-none disabled:opacity-40 focus:outline-none focus-visible:shadow-ring'

// Caption bar for the "Play" tour. With reduced motion it never auto-advances:
// the auditor steps through it with Next / Previous instead.
//
// Deliberately one slim row: the tour exists to draw attention to the MAP, so a
// tall caption card defeats its own purpose by covering the thing it is
// explaining. Step number, title and text sit on one line; the text clamps to
// two lines rather than growing the bar.
export default function ShowcaseTour({
  beats, index, paused, reducedMotion, onPrev, onNext, onJump, onTogglePause, onStop,
  voice, voiceAvailable, onToggleVoice,
}) {
  const beat = beats[index]
  const auto = !reducedMotion
  return (
    <div className="pointer-events-none sticky bottom-3 z-30 mx-auto mt-4 flex w-full max-w-3xl justify-center px-2 animate-fade-in-up" role="region" aria-label="Workflow tour">
      <div className="pointer-events-auto w-full overflow-hidden rounded-lg border border-line bg-surface/95 shadow-elevated backdrop-blur">
        {/* Pausing holds the bar where it is rather than restarting it: the key
            leaves `paused` out on purpose, so the same animation is suspended
            instead of a new one being mounted from zero. */}
        <div className="h-0.5 bg-surface-3">
          <div
            key={`${beat.id}-${index}`}
            className="h-full bg-brand"
            style={auto
              ? { animation: `wf-progress ${beat.duration}ms linear forwards`, animationPlayState: paused ? 'paused' : 'running' }
              : { width: `${((index + 1) / beats.length) * 100}%` }}
          />
        </div>

        <div className="flex items-center gap-3 px-3 py-2">
          <span className="shrink-0 text-[11px] font-medium tabular-nums text-brand">
            {index + 1}/{beats.length}
          </span>

          {/* Title and text share one paragraph so they wrap together and the whole
              caption stays within two lines, whatever the beat says. */}
          <p
            className="line-clamp-4 min-w-0 flex-1 text-[12px] leading-[17px] text-fg-muted lg:line-clamp-2"
            aria-live="polite"
          >
            <span className="font-semibold text-fg">{beat.title}.</span> {beat.text}
          </p>

          <div className="hidden shrink-0 items-center lg:flex">
            {beats.map((b, i) => (
              <button
                key={b.id}
                type="button"
                onClick={() => onJump(i)}
                aria-label={`Go to step ${i + 1}: ${b.title}`}
                aria-current={i === index ? 'step' : undefined}
                className="flex h-6 w-3 items-center justify-center focus:outline-none focus-visible:shadow-ring"
              >
                <span className={`h-1 rounded-full transition-all duration-300 ${i === index ? 'w-3 bg-brand' : 'w-1 bg-line-strong'}`} />
              </button>
            ))}
          </div>

          <div className="flex shrink-0 items-center border-l border-line pl-1">
            {/* Only offered where the browser can actually speak — a dead mute
                button is worse than no button. */}
            {voiceAvailable && (
              <button
                type="button"
                onClick={onToggleVoice}
                aria-pressed={voice}
                aria-label={voice ? 'Mute the narration' : 'Unmute the narration'}
                title={voice ? 'Narration on — click to mute' : 'Narration muted — click to unmute'}
                className={`${CONTROL} ${voice ? 'text-brand hover:text-brand' : ''}`}
              >
                {voice ? <Volume2 size={15} /> : <VolumeX size={15} />}
              </button>
            )}
            <button type="button" onClick={onPrev} disabled={index === 0} aria-label="Previous step" className={CONTROL}>
              <ChevronLeft size={15} />
            </button>
            {!reducedMotion && (
              <button
                type="button"
                onClick={onTogglePause}
                aria-label={paused ? 'Resume the tour' : 'Pause the tour'}
                title={paused ? 'Resume (space)' : 'Pause (space)'}
                className={`${CONTROL} ${paused ? 'text-brand hover:text-brand' : ''}`}
              >
                {paused ? <Play size={15} /> : <Pause size={15} />}
              </button>
            )}
            <button type="button" onClick={onNext} aria-label={index === beats.length - 1 ? 'Finish the tour' : 'Next step'} className={CONTROL}>
              <ChevronRight size={15} />
            </button>
            <button type="button" onClick={onStop} aria-label="Stop the tour" className={CONTROL}>
              <X size={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
