import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, FileSpreadsheet, Lock, Download, DownloadCloud, Loader2 } from 'lucide-react'
import { getEngagement } from '../api/engagements'
import { getGeneratedDocuments, downloadDocument } from '../api/documents'
import { useStore } from '../store/useStore'
import PageContainer from '../components/layout/PageContainer'
import { PageHeader } from '../components/layout/PageHeader'
import { EntityBadge } from '../components/ui/Badge'
import Button from '../components/ui/Button'
import { SectionHeading } from '../components/ui/Card'

const FORMAT = {
  word: { icon: FileText, label: 'Word', cls: 'text-indigo-500 bg-indigo-500/10' },
  excel: { icon: FileSpreadsheet, label: 'Excel', cls: 'text-sev-low bg-sev-low/10' },
}

function DocCard({ doc, busy, onDownload }) {
  const fmt = FORMAT[doc.format] || FORMAT.word
  const Icon = fmt.icon
  return (
    <div className={`flex flex-col rounded-xl border p-4 transition ${
      doc.available ? 'border-line bg-surface hover:' : 'border-line bg-surface-2'}`}>
      <div className="flex items-start gap-3">
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${doc.available ? fmt.cls : 'bg-surface-3 text-fg-subtle'}`}>
          {doc.available ? <Icon size={18} /> : <Lock size={16} />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-fg">{doc.title}</div>
          <div className="mt-0.5 text-xs text-fg-muted">{doc.description}</div>
        </div>
        <span className="shrink-0 rounded-md bg-surface-3 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-fg-subtle">{fmt.label}</span>
      </div>
      <div className="mt-3">
        {doc.available ? (
          <Button variant="secondary" onClick={() => onDownload(doc)} disabled={busy}>
            {busy ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />} Download
          </Button>
        ) : (
          <p className="flex items-center gap-1.5 text-xs text-fg-subtle"><Lock size={12} /> {doc.reason}</p>
        )}
      </div>
    </div>
  )
}

export default function DocumentCenterPage() {
  const { id } = useParams()
  const setActiveEngagement = useStore((s) => s.setActiveEngagement)
  const { data: eng } = useQuery({ queryKey: ['engagement', id], queryFn: () => getEngagement(id) })
  useEffect(() => { if (eng) setActiveEngagement(eng) }, [eng, setActiveEngagement])

  const { data } = useQuery({ queryKey: ['generated-docs', id], queryFn: () => getGeneratedDocuments(id) })
  const [busyKey, setBusyKey] = useState(null)

  const download = async (doc) => {
    setBusyKey(doc.key)
    try {
      await downloadDocument(doc.download_path, `${doc.title}.${doc.format === 'excel' ? 'xlsx' : 'docx'}`)
    } finally {
      setBusyKey(null)
    }
  }

  const downloadAll = async () => {
    const avail = (data?.documents || []).filter((d) => d.available)
    for (const d of avail) {
      // Sequential so the browser doesn't drop concurrent download prompts.
      // eslint-disable-next-line no-await-in-loop
      await download(d)
    }
  }

  const docs = data?.documents || []
  const categories = [...new Set(docs.map((d) => d.category))]

  return (
    <PageContainer>
      <PageHeader
        back={{ to: `/engagements/${id}/planning`, label: 'Planning' }}
        badges={eng && <EntityBadge entity={eng.entity} />}
        title="Document center"
        subtitle={eng?.name}
        actions={
          <Button onClick={downloadAll} disabled={!data?.available || busyKey !== null}>
            <DownloadCloud size={15} /> Download all available{data ? ` (${data.available})` : ''}
          </Button>
        }
      />

      {!data ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-32 animate-pulse rounded-xl bg-surface-3" />)}
        </div>
      ) : (
        <div className="space-y-8">
          {categories.map((cat) => (
            <div key={cat}>
              <SectionHeading>{cat}</SectionHeading>
              <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {docs.filter((d) => d.category === cat).map((d) => (
                  <DocCard key={d.key} doc={d} busy={busyKey === d.key} onDownload={download} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  )
}
