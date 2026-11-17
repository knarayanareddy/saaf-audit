// Lightweight CSS-only tooltip wrapper (no positioning lib). Wrap any element.
export default function Tooltip({ label, children, side = 'top', className = '', width }) {
  const pos = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-1.5',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-1.5',
    left: 'right-full top-1/2 -translate-y-1/2 mr-1.5',
    right: 'left-full top-1/2 -translate-y-1/2 ml-1.5',
  }[side]
  return (
    <span className={`group relative inline-flex ${className}`}>
      {children}
      {/* `width` turns the one-liner into a small wrapping card — needed where the
          trigger sits in a narrow column (the 232px sidebar) and the label is a sentence. */}
      <span
        role="tooltip"
        style={width ? { width } : undefined}
        className={`pointer-events-none absolute z-50 rounded-md bg-fg px-2 py-1 text-[11px] font-medium leading-snug text-canvas opacity-0 shadow-elevated transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100 ${
          width ? 'whitespace-normal' : 'whitespace-nowrap'
        } ${pos}`}
      >
        {label}
      </span>
    </span>
  )
}
