// One definition of what a form control looks like. Inputs, selects and search
// boxes were each carrying their own hand-written class string (seven copies),
// which is why they never quite lined up with the buttons next to them.
//
// Everything is sized to a fixed height so a filter bar reads as one straight
// line rather than as a row of slightly different boxes.
export const CONTROL_H = { sm: 'h-[30px]', md: 'h-9', lg: 'h-10' }

const BASE =
  'w-full rounded-md border border-line bg-surface text-fg outline-none transition-colors duration-150 ' +
  'placeholder:text-fg-subtle hover:border-line-strong focus:border-brand focus:shadow-ring ' +
  'disabled:cursor-not-allowed disabled:opacity-45'

export function fieldClass({ size = 'md', className = '' } = {}) {
  const pad = size === 'sm' ? 'px-2 text-xs' : size === 'lg' ? 'px-3.5 text-sm' : 'px-3 text-[13px]'
  return `${BASE} ${CONTROL_H[size]} ${pad} ${className}`
}

export function Input({ size = 'md', className = '', ...props }) {
  return <input className={fieldClass({ size, className })} {...props} />
}

// Native select, restyled: the chevron is drawn as a background image so the
// control keeps the exact height and radius of every other control in the row.
export function Select({ size = 'md', className = '', children, ...props }) {
  return (
    <select
      className={`${fieldClass({ size, className })} cursor-pointer appearance-none bg-[length:14px] bg-[right_0.5rem_center] bg-no-repeat pr-7`}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='none' stroke='%23889' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m4 6 4 4 4-4'/%3E%3C/svg%3E\")",
      }}
      {...props}
    >
      {children}
    </select>
  )
}
