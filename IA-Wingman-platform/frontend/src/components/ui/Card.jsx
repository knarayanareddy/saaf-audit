// A surface that sits ON the page: separated by a hairline, never by a shadow.
// The old version floated (rounded-lg + shadow + a hover lift), which is the
// single most template-looking detail in the app.
//
// `padding` defaults to 'none' so the 38 existing call sites keep supplying their
// own — two competing padding classes on one element resolve unpredictably.
const PADDING = { none: '', sm: 'p-3', md: 'p-4' }

export function Card({ as: Tag = 'div', className = '', hover = false, padding = 'none', children, ...props }) {
  return (
    <Tag
      className={`rounded-lg border border-line bg-surface ${PADDING[padding] || ''} ${
        hover ? 'transition-colors duration-150 hover:border-line-strong hover:bg-surface-2' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </Tag>
  )
}

// A section label. Quiet, uppercase, and the same everywhere — it orients the
// reader without competing with the content underneath it.
export function SectionHeading({ children, action, className = '' }) {
  return (
    <div className={`mb-2.5 flex items-center justify-between gap-3 ${className}`}>
      <h2 className="text-caption">{children}</h2>
      {action}
    </div>
  )
}

export function Kbd({ children }) {
  return (
    <kbd className="inline-flex min-w-[1.25rem] items-center justify-center rounded border border-line bg-surface-3 px-1 py-0.5 font-sans text-[10px] font-medium text-fg-muted">
      {children}
    </kbd>
  )
}
