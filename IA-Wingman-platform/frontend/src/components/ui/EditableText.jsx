import { useState, useRef, useEffect } from 'react'
import { Pencil } from 'lucide-react'
import ReadableText from './ReadableText'

// Renders text that becomes an editable textarea on click. Saves on blur.
// `readable` renders the display (non-editing) value as scannable bullets/headings
// while still allowing click-to-edit of the raw text.
export default function EditableText({
  value,
  onSave,
  placeholder = 'Click to add…',
  multiline = true,
  className = '',
  readable = false,
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value || '')
  const ref = useRef(null)

  useEffect(() => setDraft(value || ''), [value])
  useEffect(() => {
    if (editing && ref.current) {
      ref.current.focus()
      ref.current.style.height = 'auto'
      ref.current.style.height = ref.current.scrollHeight + 'px'
    }
  }, [editing])

  const commit = () => {
    setEditing(false)
    if (draft !== (value || '')) onSave(draft)
  }

  if (editing) {
    return (
      <textarea
        ref={ref}
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value)
          e.target.style.height = 'auto'
          e.target.style.height = e.target.scrollHeight + 'px'
        }}
        onBlur={commit}
        onKeyDown={(e) => {
          if (!multiline && e.key === 'Enter') {
            e.preventDefault()
            commit()
          }
          if (e.key === 'Escape') {
            setDraft(value || '')
            setEditing(false)
          }
        }}
        className={`w-full resize-none rounded-md border border-brand/40 px-2 py-1 text-sm outline-none focus:border-brand ${className}`}
        rows={1}
      />
    )
  }

  return (
    <div
      className={`editable group relative px-2 py-1 ${className}`}
      onClick={() => setEditing(true)}
    >
      {value ? (
        readable
          ? <ReadableText value={value} />
          : <span className="whitespace-pre-wrap text-sm text-fg">{value}</span>
      ) : (
        <span className="text-sm italic text-fg-subtle">{placeholder}</span>
      )}
      <Pencil
        size={12}
        className="absolute right-1 top-1.5 text-fg-subtle opacity-0 transition group-hover:opacity-100"
      />
    </div>
  )
}
