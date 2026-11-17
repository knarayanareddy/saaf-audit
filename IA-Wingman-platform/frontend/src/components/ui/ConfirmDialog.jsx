import { AlertTriangle } from 'lucide-react'
import Modal from './Modal'
import Button from './Button'

// Styled confirmation built on Modal — replaces native confirm() everywhere.
export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'Are you sure?',
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  tone = 'default', // 'default' | 'danger'
  loading = false,
}) {
  return (
    <Modal open={open} onClose={onClose} title={title} maxWidth="440px">
      <div className="flex gap-3">
        {tone === 'danger' && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-sev-high/12 text-sev-high">
            <AlertTriangle size={18} />
          </div>
        )}
        {description && <p className="text-sm text-fg-muted">{description}</p>}
      </div>
      <div className="mt-6 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose} disabled={loading}>{cancelLabel}</Button>
        <Button
          variant={tone === 'danger' ? 'danger' : 'primary'}
          onClick={onConfirm}
          disabled={loading}
        >
          {loading ? 'Working…' : confirmLabel}
        </Button>
      </div>
    </Modal>
  )
}
