// Borderless grouping — the tool that replaces "a card around everything".
//
// Structure comes from a quiet label, a rule, and the hairlines between rows;
// the section itself has no box. Use `<Card>` only when a block genuinely needs
// to read as a separate object on the page.
export default function Section({ title, action, children, className = '', divided = true }) {
  return (
    <section className={className}>
      {(title || action) && (
        <div className="flex h-7 items-center justify-between gap-3 border-b border-line">
          <h2 className="text-caption">{title}</h2>
          {action}
        </div>
      )}
      <div className={divided ? 'divide-y divide-line-subtle' : ''}>{children}</div>
    </section>
  )
}

// One row inside a section: a fixed 40px line that stays scannable because every
// row puts the same information in the same place.
export function Row({ as: Tag = 'div', className = '', children, ...props }) {
  return (
    <Tag
      className={`flex w-full items-center gap-3 px-1 py-2 text-left text-[13px] transition-colors duration-150 ${className}`}
      {...props}
    >
      {children}
    </Tag>
  )
}
