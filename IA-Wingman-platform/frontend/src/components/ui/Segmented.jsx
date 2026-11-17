import Tooltip from './Tooltip'

// Generic segmented control. options: [{ value, label, icon?, hint? }]
// `hint` explains an option on hover and keyboard focus — for options whose
// label is a term ("Computed") rather than something self-evident.
export default function Segmented({ options, value, onChange, size = 'md', className = '' }) {
  const pad = size === 'sm' ? 'h-[26px] px-2.5 text-xs' : 'h-8 px-3 text-[13px]'
  return (
    <div className={`inline-flex items-center gap-0.5 rounded-md bg-surface-3 p-0.5 ${className}`} role="tablist">
      {options.map(({ value: v, label, icon: Icon, hint }) => {
        const active = v === value
        const button = (
          <button
            key={v}
            role="tab"
            aria-selected={active}
            aria-description={hint}
            onClick={() => onChange(v)}
            className={`inline-flex items-center gap-1.5 rounded font-medium transition-colors duration-150 ${pad} ${
              active ? 'bg-surface text-fg ring-1 ring-inset ring-line' : 'text-fg-muted hover:text-fg'
            }`}
          >
            {Icon && <Icon size={14} />}
            {label}
          </button>
        )
        return hint ? <Tooltip key={v} label={hint} side="bottom" width="16rem">{button}</Tooltip> : button
      })}
    </div>
  )
}
