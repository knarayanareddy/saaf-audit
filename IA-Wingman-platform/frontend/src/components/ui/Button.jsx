// Controls are the part of an interface people feel first. These are sized to a
// fixed height rather than to padding, so a button, an input and a select in one
// row line up to the pixel — the thing that separates precise software from a
// template. Green is reserved for the primary action; everything else is neutral.
const VARIANTS = {
  primary: 'bg-brand text-brand-fg hover:bg-brand-hover',
  secondary: 'bg-surface text-fg border border-line hover:bg-surface-2 hover:border-line-strong',
  ghost: 'bg-transparent text-fg-muted hover:bg-surface-3 hover:text-fg',
  danger: 'bg-surface text-sev-high border border-sev-high/30 hover:bg-sev-high/8',
  success: 'bg-brand text-brand-fg hover:bg-brand-hover',
}

// height · horizontal padding · type size
const SIZES = {
  sm: 'h-[30px] px-2.5 text-xs gap-1.5',
  md: 'h-9 px-3 text-[13px] gap-1.5',
  lg: 'h-10 px-4 text-sm gap-2',
}

export default function Button({ variant = 'primary', size = 'md', className = '', children, ...props }) {
  return (
    <button
      className={`inline-flex shrink-0 items-center justify-center whitespace-nowrap rounded-md font-medium transition-colors duration-150 focus:outline-none focus-visible:shadow-ring disabled:cursor-not-allowed disabled:opacity-45 disabled:pointer-events-none ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
