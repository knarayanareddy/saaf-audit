// The list/table hybrid: a table's column alignment with a list's click target.
//
// A real <table> would fight the row-as-button interaction; a stack of cards
// loses the alignment that makes a list scannable. This keeps both — every row
// draws the same columns at the same x-positions, so the eye reads down a column
// instead of re-parsing each row.
//
// columns: [{ key, header, width?, align?, className? }]
//   width — a CSS length ('120px', '1fr'); omit for '1fr'.

function template(columns) {
  return columns.map((c) => c.width || '1fr').join(' ')
}

export function DataListHeader({ columns, className = '' }) {
  return (
    <div
      className={`grid items-center gap-3 border-b border-line px-2 pb-1.5 ${className}`}
      style={{ gridTemplateColumns: template(columns) }}
    >
      {columns.map((c) => (
        <div key={c.key} className={`text-caption truncate ${c.align === 'right' ? 'text-right' : ''}`}>
          {c.header}
        </div>
      ))}
    </div>
  )
}

export function DataListRow({ columns, cells, onClick, trailing, className = '' }) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <div className={`group relative flex items-center transition-colors duration-150 hover:bg-surface-2 ${className}`}>
      <Tag
        onClick={onClick}
        className="grid min-w-0 flex-1 items-center gap-3 rounded px-2 py-2 text-left"
        style={{ gridTemplateColumns: template(columns) }}
      >
        {columns.map((c) => (
          <div key={c.key} className={`min-w-0 truncate ${c.align === 'right' ? 'text-right' : ''} ${c.className || ''}`}>
            {cells[c.key]}
          </div>
        ))}
      </Tag>
      {trailing && (
        <div className="absolute right-1 opacity-0 transition-opacity duration-150 focus-within:opacity-100 group-hover:opacity-100">
          {trailing}
        </div>
      )}
    </div>
  )
}

export default function DataList({ columns, children, className = '' }) {
  return (
    <div className={className}>
      <DataListHeader columns={columns} />
      <div className="divide-y divide-line-subtle">{children}</div>
    </div>
  )
}
