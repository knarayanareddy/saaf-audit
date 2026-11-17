import { CheckCircle, AlertCircle } from 'lucide-react'
import { useStore } from '../../store/useStore'

export default function Toast() {
  const toast = useStore((s) => s.toast)
  if (!toast) return null
  const isError = toast.type === 'error'
  return (
    <div className="fixed bottom-6 right-6 z-[60] flex items-center gap-2 rounded-xl border border-line bg-surface px-4 py-3 shadow-elevated animate-fade-in-up">
      {isError ? (
        <AlertCircle size={16} className="text-sev-high" />
      ) : (
        <CheckCircle size={16} className="text-brand" />
      )}
      <span className="text-sm text-fg">{toast.message}</span>
    </div>
  )
}
