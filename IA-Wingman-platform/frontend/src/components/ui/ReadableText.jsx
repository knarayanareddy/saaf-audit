// Renders a plain string as scannable content: paragraphs, bullet and numbered
// lists, mini-headings, and inline bold / italic / code. Parsing lives in
// lib/markdown.js so it can be unit-tested; this file only turns the parsed
// blocks into nodes. No HTML is ever injected — everything is built from text.
import { parseBlocks } from '../../lib/markdown'

function Spans({ spans }) {
  return spans.map((s, i) => {
    if (s.type === 'strong') return <strong key={i} className="font-semibold text-fg">{s.text}</strong>
    if (s.type === 'em') return <em key={i}>{s.text}</em>
    if (s.type === 'code') {
      return (
        <code key={i} className="rounded bg-surface-3 px-1 py-0.5 font-mono text-[0.85em] text-fg">
          {s.text}
        </code>
      )
    }
    return <span key={i}>{s.text}</span>
  })
}

function List({ block }) {
  const ordered = block.type === 'ol'
  const Tag = ordered ? 'ol' : 'ul'
  return (
    <Tag className="space-y-1">
      {block.items.map((spans, i) => (
        <li key={i} className="flex gap-2">
          {ordered ? (
            <span className="mt-[1px] shrink-0 text-xs font-semibold tabular-nums text-brand">{i + 1}.</span>
          ) : (
            <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-brand" />
          )}
          <span className="min-w-0 flex-1"><Spans spans={spans} /></span>
        </li>
      ))}
    </Tag>
  )
}

// The assistant panel is a narrow column, and a three-column table does not fit
// in it at any font size worth reading. So the table scrolls sideways inside its
// own box rather than squeezing every cell to two words per line — the row stays
// readable as a row, which is the only reason to use a table at all.
function Table({ block }) {
  const cell = (align) => (align === 'right' ? 'text-right tabular-nums'
    : align === 'center' ? 'text-center' : 'text-left')
  return (
    <div className="-mx-1 overflow-x-auto px-1">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr>
            {block.head.map((spans, i) => (
              <th
                key={i}
                className={`border-b border-line px-2 py-1 font-semibold text-fg ${cell(block.align[i])}`}
              >
                <Spans spans={spans} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.rows.map((row, r) => (
            <tr key={r} className="align-top">
              {row.map((spans, c) => (
                <td key={c} className={`border-b border-line/60 px-2 py-1 ${cell(block.align[c])}`}>
                  <Spans spans={spans} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function ReadableText({ value, className = '' }) {
  const blocks = parseBlocks(value)
  if (!blocks.length) return null
  return (
    <div className={`space-y-2 text-sm text-fg ${className}`}>
      {blocks.map((b, i) => {
        if (b.type === 'hr') return <hr key={i} className="border-line" />
        if (b.type === 'h') {
          return <p key={i} className="font-semibold text-fg"><Spans spans={b.spans} /></p>
        }
        if (b.type === 'ul' || b.type === 'ol') return <List key={i} block={b} />
        if (b.type === 'table') return <Table key={i} block={b} />
        return <p key={i} className="leading-relaxed"><Spans spans={b.spans} /></p>
      })}
    </div>
  )
}
