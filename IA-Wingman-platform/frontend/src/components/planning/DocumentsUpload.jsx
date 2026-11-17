import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, FileText, Trash2, ShieldAlert, Eye, Download, Loader2, Check } from 'lucide-react'
import {
  uploadDocument, listDocuments, deleteDocument,
  getDocument, updateDocument, downloadDocument,
} from '../../api/agents'
import { Tag } from '../ui/Badge'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import { useStore } from '../../store/useStore'
import Tooltip from '../ui/Tooltip'

const ACCEPT = '.pdf,.docx,.doc,.txt,.md,.markdown,.csv,.tsv,.text,.log'

// Drawer to open a document: view + correct the extracted text the analysers read,
// and download the original. Editing the extracted text lets the auditor fix
// OCR/extraction errors; analysers pick up the revised text on their next run.
function DocumentViewer({ engagementId, docId, onClose }) {
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [text, setText] = useState('')
  const [dirty, setDirty] = useState(false)

  const { data: doc, isPending } = useQuery({
    queryKey: ['doc', docId],
    queryFn: () => getDocument(docId),
    enabled: !!docId,
  })

  useEffect(() => {
    if (doc) { setText(doc.extracted_text ?? ''); setDirty(false) }
  }, [doc])

  const save = useMutation({
    mutationFn: () => updateDocument(docId, text),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['docs', engagementId] })
      qc.invalidateQueries({ queryKey: ['doc', docId] })
      setDirty(false)
      showToast('Document text saved', 'success')
    },
    onError: () => showToast('Could not save the document', 'error'),
  })

  return (
    <Modal open onClose={onClose} title={doc?.original_filename || 'Document'} maxWidth="820px">
      {isPending ? (
        <div className="flex items-center gap-2 py-8 text-sm text-fg-subtle">
          <Loader2 size={16} className="animate-spin" /> Loading document…
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {doc?.upload_status === 'failed' ? (
              <Tag className="bg-sev-high/10 text-sev-high">No text extracted</Tag>
            ) : (
              <Tag className="bg-sev-low/10 text-sev-low">Extracted text</Tag>
            )}
            {doc?.injection_flags?.length > 0 && (
              <Tag className="bg-sev-med/10 text-sev-med">
                <ShieldAlert size={10} className="mr-0.5 inline align-[-1px]" /> {doc.injection_flags.length} to verify
              </Tag>
            )}
            <span className="ml-auto">
              <Button variant="secondary" onClick={() => downloadDocument(docId, doc?.original_filename)}>
                <Download size={14} /> Download original
              </Button>
            </span>
          </div>

          <p className="text-xs text-fg-subtle">
            This is the text the AI analysers read. Correct any extraction errors here — the original file is unchanged.
          </p>
          <textarea
            value={text}
            onChange={(e) => { setText(e.target.value); setDirty(true) }}
            spellCheck={false}
            className="h-80 w-full resize-y rounded-xl border border-line bg-surface-2 p-3 font-mono text-xs leading-relaxed text-fg outline-none focus:border-brand"
            placeholder="No text was extracted from this file."
          />

          <div className="flex items-center justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Close</Button>
            <Button onClick={() => save.mutate()} disabled={!dirty || save.isPending}>
              {save.isPending ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />} Save text
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}

// Engagement-scoped document upload, reused across planning modules. Documents are
// shared per engagement, so the analysers (which read engagement docs) pick them up.
export default function DocumentsUpload({ engagementId, title = 'Documents' }) {
  const qc = useQueryClient()
  const showToast = useStore((s) => s.showToast)
  const [dragging, setDragging] = useState(false)
  const [viewDocId, setViewDocId] = useState(null)

  const { data: docs = [] } = useQuery({
    queryKey: ['docs', engagementId],
    queryFn: () => listDocuments(engagementId),
  })

  const upload = useMutation({
    mutationFn: (file) => uploadDocument(engagementId, file),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ['docs', engagementId] })
      if (d.upload_status === 'failed') showToast('Text could not be extracted from that file', 'error')
    },
    onError: (e) => showToast(e.response?.data?.detail || 'Upload failed', 'error'),
  })

  const removeDoc = useMutation({
    mutationFn: (docId) => deleteDocument(docId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['docs', engagementId] }),
  })

  return (
    <section>
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-fg-muted">{title}</h2>
      <label
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          const file = e.dataTransfer.files?.[0]
          if (file) upload.mutate(file)
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed py-8 text-center transition ${
          dragging ? 'border-brand bg-brand-subtle/40' : 'border-line bg-surface hover:border-brand/40'
        }`}
      >
        <Upload size={24} className={dragging ? 'text-brand' : 'text-fg-subtle'} />
        <span className="mt-2 text-sm text-fg-muted">
          {dragging ? 'Drop to upload' : 'Drag & drop, or click to choose a file'}
        </span>
        <span className="mt-0.5 text-[11px] text-fg-subtle">PDF, Word (.docx) or text (.txt, .md, .csv)</span>
        <input
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => {
            if (e.target.files[0]) upload.mutate(e.target.files[0])
            e.target.value = ''
          }}
        />
      </label>
      {upload.isPending && <p className="mt-2 text-xs text-fg-subtle">Uploading & extracting…</p>}
      <div className="mt-2 space-y-1">
        {docs.map((d) => (
          <div key={d.id} className="border border-line flex items-center justify-between rounded-lg bg-surface px-3 py-2 text-sm">
            <span className="flex min-w-0 items-center gap-2">
              <FileText size={14} className="shrink-0 text-fg-subtle" />
              <span className="truncate">{d.original_filename}</span>
              {d.upload_status === 'ready' && <Tag className="bg-sev-low/10 text-sev-low">Ready</Tag>}
              {d.upload_status === 'failed' && <Tag className="bg-sev-high/10 text-sev-high">No text</Tag>}
              {d.injection_flag_count > 0 && (
                <Tooltip width="16rem" label={`${d.injection_flag_count} possible prompt-injection signal(s): text that reads like instructions to an AI. Verify this document before relying on it.`}>
                  <Tag className="bg-sev-med/10 text-sev-med">
                    <ShieldAlert size={10} className="mr-0.5 inline align-[-1px]" /> Verify
                  </Tag>
                </Tooltip>
              )}
            </span>
            <span className="flex shrink-0 items-center gap-1">
              <button
                onClick={() => setViewDocId(d.id)}
                title="Open & edit extracted text"
                className="rounded p-1 text-fg-subtle transition hover:bg-surface-3 hover:text-brand"
              >
                <Eye size={15} />
              </button>
              <button
                onClick={() => removeDoc.mutate(d.id)}
                title="Delete document"
                className="rounded p-1 text-fg-subtle transition hover:bg-surface-3 hover:text-sev-high"
              >
                <Trash2 size={14} />
              </button>
            </span>
          </div>
        ))}
      </div>

      {viewDocId && (
        <DocumentViewer engagementId={engagementId} docId={viewDocId} onClose={() => setViewDocId(null)} />
      )}
    </section>
  )
}
