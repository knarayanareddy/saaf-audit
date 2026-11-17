import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Info, X } from 'lucide-react'
import client from '../../api/client'
import Tooltip from '../ui/Tooltip'

/**
 * Shows a single, calm banner when the Anthropic API key is not configured.
 * AI features (agents, drafting, chat) need the key; everything else works.
 * Dismissible so it never gets in the way during a demo.
 */
export default function ConfigBanner() {
  const [dismissed, setDismissed] = useState(false)

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => client.get('/health').then((r) => r.data),
    staleTime: 30_000,
  })

  if (dismissed || !health || health.ai_enabled) return null

  // Says what is wrong with the key — never the key itself — because "inactive"
  // alone sent a deploy round in circles: the key looked right in the host's field.
  const why = {
    missing: 'is not set',
    placeholder: 'is still the example placeholder',
    unexpected_prefix: `does not start with sk-ant- (it starts with "${health.ai_key_starts_with ?? ''}", ${health.ai_key_length} characters)`,
  }[health.ai_key_problem] || 'is not usable'
  const code = (t) => <code className="rounded bg-sev-med/10 px-1 text-xs">{t}</code>

  return (
    <div className="flex items-center gap-2 border-b border-sev-med/25 bg-sev-med/10 px-6 py-2 text-sm text-sev-med">
      <Info size={15} className="shrink-0 text-sev-med" />
      <span className="flex-1">
        AI features (agents, drafting, chat) are inactive: {code('ANTHROPIC_API_KEY')} {why}. Set it in the
        host&apos;s environment settings (locally: {code('backend/.env')}) and restart. All other features work normally.
      </span>
      <Tooltip label="Hide until the next reload" side="left" className="shrink-0">
        <button onClick={() => setDismissed(true)} aria-label="Hide this notice" className="text-sev-med transition hover:text-sev-med">
          <X size={15} />
        </button>
      </Tooltip>
    </div>
  )
}
