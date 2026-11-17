import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Check, Loader2, ShieldAlert, Sparkles, Table2, Upload,
} from 'lucide-react'
import Button from '../../components/ui/Button'
import {
  confirmMapping, defaultSelection, getRcsaRows, listRcsaImports, previewRcsa,
  proposeMapping, proposeRisks, recordReliance, uploadRcsa,
} from '../../api/rcsa'

// Importing the RCSA the business made about itself.
//
// Four steps, in this order and no other: upload, say which rows are the header,
// confirm what each column holds, read the rows. The third is the one that
// matters — a bank's export has no standard shape, so the agent proposes and a
// person decides, and their decision is the template the next import reuses.
//
// Two things are deliberately impossible to miss on this page. Every column the
// mapping did not claim is listed rather than hidden, because a wrong match is
// invisible and a visible gap is not. And nothing here is Internal Audit's
// conclusion: the auditee label comes from the API with the rows and sits above
// them, so the page cannot show the data without it.

const TARGET_NONE = '__unmapped__'

function Step({ n, title, done, children }) {
  return (
    <section className="rounded-xl border border-line bg-surface-2 p-4">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-fg">
        <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] ${
          done ? 'bg-brand text-brand-fg' : 'bg-surface-3 text-fg-muted'}`}>
          {done ? <Check size={12} /> : n}
        </span>
        {title}
      </h2>
      {children}
    </section>
  )
}

// The sheet as it is, so the person choosing the header can see what they are
// choosing. A real export opens with a title block; the column names are further
// down, and which row holds them is obvious to a reader and a guess to a parser.
function GridPreview({ grid, headerRows, onToggleRow, candidates }) {
  const best = new Set((candidates || []).slice(0, 2).map((c) => c.row))
  return (
    <div className="max-h-72 overflow-auto rounded-lg border border-line">
      <table className="min-w-full border-collapse text-[11px]">
        <tbody>
          {(grid || []).slice(0, 14).map((row, i) => {
            const n = i + 1
            const chosen = headerRows.includes(n)
            return (
              <tr
                key={n}
                onClick={() => onToggleRow(n)}
                className={`cursor-pointer ${chosen ? 'bg-brand/10' : 'hover:bg-surface-3'}`}
              >
                <td className="sticky left-0 whitespace-nowrap bg-surface-2 px-2 py-1 text-right text-fg-subtle">
                  {n}
                  {best.has(n) && !chosen && <span className="ml-1 text-brand">•</span>}
                </td>
                {row.slice(0, 12).map((cell, c) => (
                  <td key={c} className="max-w-[140px] truncate border-l border-line px-2 py-1 text-fg-muted">
                    {cell}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function RcsaPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [importId, setImportId] = useState(null)
  const [sheet, setSheet] = useState(null)
  const [headerRows, setHeaderRows] = useState([])
  const [columns, setColumns] = useState(null)      // the mapping being confirmed
  const [notes, setNotes] = useState('')
  const [primaryBand, setPrimaryBand] = useState('')
  const [name, setName] = useState('')
  const [rationale, setRationale] = useState('')
  const [extent, setExtent] = useState('partial')
  const [assessed, setAssessed] = useState(false)
  const [selected, setSelected] = useState(null)   // null = the default, still untouched

  const { data: imports } = useQuery({
    queryKey: ['rcsa-imports', id],
    queryFn: () => listRcsaImports(id),
  })
  const { data: preview } = useQuery({
    queryKey: ['rcsa-preview', importId, sheet],
    queryFn: () => previewRcsa(importId, sheet),
    enabled: !!importId,
  })
  const { data: rows } = useQuery({
    queryKey: ['rcsa-rows', importId],
    queryFn: () => getRcsaRows(importId),
    enabled: !!importId && !!columns === false,
  })

  const upload = useMutation({
    mutationFn: (file) => uploadRcsa(id, file),
    onSuccess: (d) => {
      setImportId(d.id)
      setColumns(null)
      setHeaderRows([])
      qc.invalidateQueries({ queryKey: ['rcsa-imports', id] })
    },
  })

  const propose = useMutation({
    mutationFn: () => proposeMapping(importId, { sheet, header_rows: headerRows }),
    onSuccess: (d) => {
      setColumns(d.columns)
      setNotes(d.notes || '')
    },
  })

  const confirm = useMutation({
    mutationFn: () => confirmMapping(importId, {
      sheet, header_rows: headerRows, columns, name: name || preview?.filename,
      primary_band: primaryBand || null,
    }),
    onSuccess: () => {
      setColumns(null)
      qc.invalidateQueries({ queryKey: ['rcsa-imports', id] })
      qc.invalidateQueries({ queryKey: ['rcsa-rows', importId] })
      // The default selection is computed from the rows, which did not exist
      // until this call created them. Without this the page offers "no row
      // carries a key-risk flag" over an import whose rows do — the answer to a
      // question asked before there was anything to answer it with.
      qc.invalidateQueries({ queryKey: ['rcsa-default-selection', importId] })
    },
  })

  const { data: suggested } = useQuery({
    queryKey: ['rcsa-default-selection', importId],
    queryFn: () => defaultSelection(importId),
    enabled: !!importId,
  })

  const push = useMutation({
    mutationFn: () => proposeRisks(importId, chosenRows),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['racm'] }),
  })

  const reliance = useMutation({
    mutationFn: () => recordReliance(importId, {
      quality_assessed: assessed, extent, rationale,
    }),
    onSuccess: () => {
      setRationale('')
      qc.invalidateQueries({ queryKey: ['rcsa-rows', importId] })
      qc.invalidateQueries({ queryKey: ['rcsa-imports', id] })
    },
  })

  // Untouched, the selection is what the business itself flagged. The moment the
  // auditor ticks anything it becomes theirs, and the default stops applying.
  const chosenRows = selected ?? (suggested?.row_ids || [])
  const toggleRowPick = (rowId) =>
    setSelected((cur) => {
      const base = cur ?? (suggested?.row_ids || [])
      return base.includes(rowId) ? base.filter((r) => r !== rowId) : [...base, rowId]
    })

  const targets = propose.data?.targets || []
  const bands = [...new Set((columns || []).map((c) => c.band).filter(Boolean))]
  const unmapped = (columns || []).filter((c) => !c.target)

  const toggleRow = (n) =>
    setHeaderRows((rs) => (rs.includes(n) ? rs.filter((r) => r !== n) : [...rs, n].sort((a, b) => a - b)))

  const setTarget = (i, value) =>
    setColumns((cs) => cs.map((c, j) => (j === i ? { ...c, target: value === TARGET_NONE ? null : value } : c)))

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <button onClick={() => navigate(`/engagements/${id}/planning`)}
              className="flex items-center gap-1 text-sm text-fg-muted hover:text-fg">
        <ArrowLeft size={14} /> Planning
      </button>

      <header>
        <h1 className="flex items-center gap-2 text-xl font-semibold text-fg">
          <Table2 size={18} className="text-brand" /> RCSA import
        </h1>
        <p className="mt-1 text-sm text-fg-muted">
          The risk and control self-assessment the business made about itself. An agent proposes
          what each column holds; you confirm it once, and the next export from the same template
          is one click.
        </p>
      </header>

      <Step n={1} title="Upload the export" done={!!importId}>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-fg-muted">
          <input type="file" accept=".xlsx,.xlsm,.csv" className="hidden"
                 onChange={(e) => e.target.files?.[0] && upload.mutate(e.target.files[0])} />
          <span className="flex items-center gap-2 rounded-lg border border-line px-3 py-2 hover:bg-surface-3">
            {upload.isPending ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
            Choose an .xlsx or .csv
          </span>
          {preview?.filename && <span className="text-fg">{preview.filename}</span>}
        </label>
        {upload.isError && (
          <p className="mt-2 text-sm text-sev-high">
            {upload.error?.response?.data?.detail || 'Upload failed'}
          </p>
        )}
        {(imports?.imports || []).length > 0 && (
          <ul className="mt-3 space-y-1 text-xs text-fg-muted">
            {imports.imports.map((imp) => (
              <li key={imp.id}>
                <button className="hover:text-fg" onClick={() => { setImportId(imp.id); setColumns(null) }}>
                  {imp.filename} — {imp.rows} rows
                  {imp.reliance.allowed ? '' : ' · not relied on yet'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </Step>

      {importId && (
        <Step n={2} title="Which rows are the header?" done={headerRows.length > 0}>
          {preview?.sheets?.length > 1 && (
            <div className="mb-2 flex gap-2 text-xs">
              {preview.sheets.map((s) => (
                <button key={s} onClick={() => setSheet(s)}
                        className={`rounded px-2 py-1 ${s === (sheet || preview.sheet)
                          ? 'bg-brand text-brand-fg' : 'bg-surface-3 text-fg-muted'}`}>
                  {s}
                </button>
              ))}
            </div>
          )}
          <p className="mb-2 text-xs text-fg-subtle">
            Click the rows that name the columns — several, where the header is banded. The dots
            mark what this looks like from here; the choice is yours.
          </p>
          <GridPreview grid={preview?.grid} headerRows={headerRows} onToggleRow={toggleRow}
                       candidates={preview?.header_candidates} />
          <div className="mt-3">
            <Button onClick={() => propose.mutate()} disabled={!headerRows.length || propose.isPending}>
              {propose.isPending
                ? <><Loader2 size={14} className="mr-1 animate-spin" /> Reading the columns…</>
                : <><Sparkles size={14} className="mr-1" /> Propose what each column holds</>}
            </Button>
          </div>
        </Step>
      )}

      {columns && (
        <Step n={3} title="Confirm the mapping" done={false}>
          {notes && <p className="mb-3 rounded-lg bg-surface-3 px-3 py-2 text-xs text-fg-muted">{notes}</p>}
          <div className="max-h-96 overflow-auto rounded-lg border border-line">
            <table className="min-w-full border-collapse text-xs">
              <thead className="sticky top-0 bg-surface-2">
                <tr>
                  <th className="border-b border-line px-2 py-1 text-left font-semibold text-fg">Column in the export</th>
                  <th className="border-b border-line px-2 py-1 text-left font-semibold text-fg">Holds</th>
                  <th className="border-b border-line px-2 py-1 text-left font-semibold text-fg">Why</th>
                </tr>
              </thead>
              <tbody>
                {columns.map((c, i) => (
                  <tr key={i} className={c.target ? '' : 'bg-sev-med/5'}>
                    <td className="border-b border-line/60 px-2 py-1 align-top text-fg">
                      {c.column}
                      {c.band && <div className="text-[10px] text-fg-subtle">{c.band}</div>}
                    </td>
                    <td className="border-b border-line/60 px-2 py-1 align-top">
                      <select
                        value={c.target || TARGET_NONE}
                        onChange={(e) => setTarget(i, e.target.value)}
                        className="w-full rounded border border-line bg-surface px-1 py-0.5 text-xs text-fg"
                      >
                        <option value={TARGET_NONE}>— not mapped —</option>
                        {targets.map((t) => (
                          <option key={t.key} value={t.key}>{t.label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="border-b border-line/60 px-2 py-1 align-top text-fg-subtle">{c.why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-2 text-xs text-fg-muted">
            {unmapped.length} of {columns.length} columns are not mapped. They stay in the import
            and stay on screen — a column matched to the wrong field is the mistake nobody sees.
          </p>

          {bands.length > 1 && (
            <div className="mt-3 rounded-lg border border-line bg-surface-3 p-3">
              <p className="text-xs text-fg">
                This export carries more than one rating band. Which one does this audit read as
                the residual rating?
              </p>
              <select value={primaryBand} onChange={(e) => setPrimaryBand(e.target.value)}
                      className="mt-2 w-full rounded border border-line bg-surface px-2 py-1 text-xs text-fg">
                <option value="">— not chosen; both are kept, neither is read as 'the' residual —</option>
                {bands.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
          )}

          <div className="mt-3 flex items-center gap-2">
            <input value={name} onChange={(e) => setName(e.target.value)}
                   placeholder="Name this template, e.g. AM quarterly RCSA"
                   className="flex-1 rounded border border-line bg-surface px-2 py-1 text-sm text-fg" />
            <Button onClick={() => confirm.mutate()} disabled={confirm.isPending}>
              {confirm.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Confirm and import'}
            </Button>
          </div>
        </Step>
      )}

      {rows && !columns && (
        <Step n={4} title="The rows" done>
          <p className="mb-1 flex items-center gap-2 text-xs font-medium text-fg">
            <ShieldAlert size={13} className="text-sev-med" /> {rows.auditee_label}
          </p>
          <p className="mb-3 text-xs text-fg-subtle">
            {rows.coverage.mapped} of {rows.coverage.columns} columns mapped ·{' '}
            {rows.coverage.unmapped} left unmapped ·{' '}
            {rows.coverage.targets_missing.length} fields this export does not cover
          </p>

          <div className={`mb-3 rounded-lg border p-3 ${rows.reliance.allowed
            ? 'border-line bg-surface-3' : 'border-sev-med/40 bg-sev-med/5'}`}>
            <p className="text-xs text-fg">{rows.reliance.reason}</p>
            {!rows.reliance.allowed && (
              <div className="mt-2 space-y-2">
                <label className="flex items-center gap-2 text-xs text-fg-muted">
                  <input type="checkbox" checked={assessed} onChange={(e) => setAssessed(e.target.checked)} />
                  I assessed the quality of this second-line work
                </label>
                <div className="flex gap-2">
                  <select value={extent} onChange={(e) => setExtent(e.target.value)}
                          className="rounded border border-line bg-surface px-2 py-1 text-xs text-fg">
                    <option value="full">Rely fully</option>
                    <option value="partial">Rely in part</option>
                    <option value="none">Do not rely</option>
                  </select>
                  <input value={rationale} onChange={(e) => setRationale(e.target.value)}
                         placeholder="What you assessed, and why this extent"
                         className="flex-1 rounded border border-line bg-surface px-2 py-1 text-xs text-fg" />
                  <Button onClick={() => reliance.mutate()} disabled={!rationale || reliance.isPending}>
                    Record
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="text-xs text-fg-subtle">
              {chosenRows.length} of {rows.rows.length} rows selected
              {selected === null && suggested?.reason ? ` — ${suggested.reason.toLowerCase()}` : ''}
            </p>
            <Button onClick={() => push.mutate()}
                    disabled={!rows.reliance.allowed || !chosenRows.length || push.isPending}>
              {push.isPending
                ? <Loader2 size={14} className="animate-spin" />
                : 'Propose the selected rows into the matrix'}
            </Button>
          </div>
          {push.data && (
            <p className="mb-2 text-xs text-fg-muted">
              {push.data.written} proposal(s) now await your acceptance in the risk matrix —
              each one naming the row of this export it came from.
            </p>
          )}
          {push.isError && (
            <p className="mb-2 text-xs text-sev-high">
              {push.error?.response?.data?.detail || 'Could not propose these rows'}
            </p>
          )}

          <div className="max-h-96 overflow-auto rounded-lg border border-line">
            <table className="min-w-full border-collapse text-xs">
              <thead className="sticky top-0 bg-surface-2">
                <tr>
                  <th className="border-b border-line px-2 py-1" />
                  {['Risk', 'Process', 'Key risk', 'Inherent', 'Residual', 'Controls'].map((h) => (
                    <th key={h} className="border-b border-line px-2 py-1 text-left font-semibold text-fg">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.rows.map((r) => {
                  const p = r.projected || {}
                  const rating = (v) => (v?.raw || v?.label || '—')
                  return (
                    <tr key={r.id} className="align-top">
                      <td className="border-b border-line/60 px-2 py-1">
                        <input type="checkbox" checked={chosenRows.includes(r.id)}
                               onChange={() => toggleRowPick(r.id)}
                               disabled={!rows.reliance.allowed} />
                      </td>
                      <td className="border-b border-line/60 px-2 py-1 text-fg">{p.risk_title || '—'}</td>
                      <td className="border-b border-line/60 px-2 py-1 text-fg-muted">{p.process || '—'}</td>
                      <td className="border-b border-line/60 px-2 py-1">
                        {p.key_risk === true ? <span className="text-sev-high">Yes</span>
                          : p.key_risk === false ? <span className="text-fg-subtle">No</span>
                            : <span className="text-fg-subtle">—</span>}
                      </td>
                      <td className="border-b border-line/60 px-2 py-1 text-fg-muted">{rating(p.inherent_exposure)}</td>
                      <td className="border-b border-line/60 px-2 py-1 text-fg-muted">
                        {p.needs_band_choice?.includes('residual_exposure')
                          ? <span className="text-sev-med">band not chosen</span>
                          : rating(p.residual_exposure)}
                      </td>
                      <td className="border-b border-line/60 px-2 py-1 text-fg-subtle">{p.controls || '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Step>
      )}
    </div>
  )
}
