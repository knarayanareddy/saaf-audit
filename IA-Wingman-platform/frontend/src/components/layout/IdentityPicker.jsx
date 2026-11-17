import { useState } from 'react'
import { ArrowRight, ShieldCheck, Sparkles, Lock, Loader2, AlertCircle } from 'lucide-react'
import { useStore } from '../../store/useStore'

// The first impression: a calm, brand-neutral hero. IA Wingman is the product;
// the customer org's identity appears once inside. Works in light and dark.
export default function IdentityPicker() {
  const currentUser = useStore((s) => s.currentUser)
  const setCurrentUser = useStore((s) => s.setCurrentUser)
  const setAuth = useStore((s) => s.setAuth)

  const [initials, setInitials] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const needsInitials = !currentUser

  const submit = async (e) => {
    e.preventDefault()
    const pw = password.trim()
    const ini = initials.trim()
    if (!pw || (needsInitials && !ini)) return
    setError('')
    setBusy(true)
    try {
      const ok = await setAuth(pw)
      if (!ok) {
        setError('Wrong password — please try again.')
        setPassword('')
        return
      }
      if (needsInitials) setCurrentUser(ini)
    } catch {
      setError('Cannot reach the server — is the backend running?')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-canvas p-4">
      {/* Organic brand accents — subtle, sustainable feel */}
      <div className="pointer-events-none absolute -left-40 -top-40 h-96 w-96 rounded-full bg-brand/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -right-32 h-96 w-96 rounded-full bg-brand/10 blur-3xl" />

      <div className="relative w-full max-w-md animate-fade-in-up">
        {/* Brand header band */}
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-brand-fg border border-line">
            <Sparkles size={20} />
          </div>
          <div>
            <div className="text-lg font-bold tracking-tight text-fg">IA Wingman</div>
            <div className="text-xs text-fg-muted">AI copilot for internal audit</div>
          </div>
        </div>

        <div className="rounded-2xl border border-line bg-surface p-8 shadow-elevated">
          <h1 className="text-h2 text-fg">
            {needsInitials ? 'Welcome' : `Welcome back, ${currentUser}`}
          </h1>
          <p className="mt-1.5 text-sm text-fg-muted">
            {needsInitials
              ? 'Enter your initials and the team password to begin.'
              : 'Enter the team password to continue.'}
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            {needsInitials && (
              <div>
                <label className="mb-1.5 block text-caption text-fg-subtle">Your initials</label>
                <input
                  autoFocus
                  value={initials}
                  onChange={(e) => setInitials(e.target.value)}
                  placeholder="e.g. AB"
                  className="w-full rounded-lg border border-line bg-surface px-4 py-2.5 text-sm text-fg outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
                />
                <p className="mt-1.5 flex items-center gap-1 text-xs text-fg-subtle">
                  {/* This used to say "never in a database". Since the edit register,
                      the initials go with each change, so the audit trail can say who
                      accepted or edited what — the screen has to say so too. */}
                  <ShieldCheck size={12} /> Recorded with each change you make, so the audit trail shows who decided
                </p>
              </div>
            )}

            <div>
              <label className="mb-1.5 block text-caption text-fg-subtle">Team password</label>
              <div className="relative">
                <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-subtle" />
                <input
                  autoFocus={!needsInitials}
                  type="password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); if (error) setError('') }}
                  placeholder="••••••••"
                  aria-invalid={!!error}
                  className={`w-full rounded-lg border bg-surface py-2.5 pl-9 pr-4 text-sm text-fg outline-none transition focus:ring-2 ${error ? 'border-sev-high/40 focus:border-sev-high/40 focus:ring-sev-high/20' : 'border-line focus:border-brand focus:ring-brand/20'}`}
                />
              </div>
            </div>

            {error && (
              <p role="alert" className="flex items-center gap-1.5 text-xs font-medium text-sev-high">
                <AlertCircle size={13} /> {error}
              </p>
            )}

            <button
              type="submit"
              disabled={busy || (needsInitials && !initials.trim()) || !password.trim()}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-brand py-2.5 text-sm font-semibold text-brand-fg shadow-sm transition hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? <Loader2 size={16} className="animate-spin" /> : null}
              {busy ? 'Signing in…' : (needsInitials ? 'Get started' : 'Sign in')}
              {!busy && <ArrowRight size={16} />}
            </button>
          </form>
        </div>

        <p className="mt-5 text-center text-xs text-fg-subtle">
          Human-in-the-loop by design — AI proposes, you decide.
        </p>
      </div>
    </div>
  )
}
