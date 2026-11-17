/**
 * AIFieldHelper — small ✦ button that opens an inline popover
 * for AI-assisted improvement of a text field.
 *
 * Usage:
 *   <AIFieldHelper
 *     fieldLabel="Background section"
 *     currentValue={text}
 *     engagementId={id}       // optional
 *     onAccept={(improved) => handleSave(improved)}
 *   />
 */
import { useState, useRef, useEffect } from 'react'
import { Sparkles, X, Check, Loader2 } from 'lucide-react'
import { improveText } from '../../api/ai'
import Tooltip from './Tooltip'

export default function AIFieldHelper({ fieldLabel, currentValue, engagementId, onAccept }) {
  const [open, setOpen] = useState(false)
  const [instruction, setInstruction] = useState('')
  const [suggestion, setSuggestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const popoverRef = useRef(null)

  // Close on click outside
  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const reset = () => {
    setInstruction('')
    setSuggestion('')
    setError('')
    setLoading(false)
  }

  const handleOpen = () => {
    reset()
    setOpen(true)
  }

  const handleGenerate = async () => {
    if (!currentValue?.trim()) {
      setError('No text to improve. Add content first.')
      return
    }
    setLoading(true)
    setError('')
    setSuggestion('')
    try {
      const data = await improveText({
        text: currentValue,
        field_label: fieldLabel,
        instruction: instruction.trim(),
        engagement_id: engagementId || null,
      })
      setSuggestion(data.improved || '')
    } catch {
      setError('AI service unavailable — try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleAccept = () => {
    if (suggestion) {
      onAccept(suggestion)
    }
    setOpen(false)
    reset()
  }

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={handleOpen}
        title={`AI: improve ${fieldLabel}`}
        className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-brand hover:bg-brand-subtle transition-colors"
      >
        <Sparkles size={13} />
      </button>

      {open && (
        <div
          ref={popoverRef}
          className="absolute right-0 top-8 z-50 w-80 rounded-lg border border-line bg-surface-raised shadow-elevated"
        >
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <span className="flex items-center gap-1 text-xs font-semibold text-fg"><Sparkles size={12} /> Improve this field</span>
            <Tooltip label="Close" side="left">
              <button
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="text-fg-subtle hover:text-fg-muted"
              >
                <X size={14} />
              </button>
            </Tooltip>
          </div>

          <div className="p-4 space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-fg-muted">
                Instruction (optional)
              </label>
              <input
                type="text"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="e.g. Add transaction monitoring to the scope"
                className="w-full rounded-lg border border-line px-3 py-2 text-xs focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
                onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
              />
            </div>

            <button
              onClick={handleGenerate}
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand py-2 text-xs font-semibold text-white hover:bg-brand-hover disabled:opacity-60"
            >
              {loading ? (
                <><Loader2 size={12} className="animate-spin" /> Generating…</>
              ) : (
                'Generate suggestion'
              )}
            </button>

            {error && (
              <p className="text-xs text-sev-high">{error}</p>
            )}

            {suggestion && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-fg-muted">Suggestion:</p>
                <div className="max-h-40 overflow-y-auto rounded-lg bg-surface-3 p-3 text-xs text-fg">
                  {suggestion}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleAccept}
                    className="flex flex-1 items-center justify-center gap-1 rounded-md bg-brand/10 py-1.5 text-xs font-medium text-brand transition-colors duration-150 hover:bg-brand/15"
                  >
                    <Check size={12} /> Accept
                  </button>
                  <button
                    onClick={reset}
                    className="flex items-center gap-1 rounded-lg border border-line px-3 py-1.5 text-xs text-fg-muted hover:bg-surface-3"
                  >
                    <X size={12} /> Dismiss
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
