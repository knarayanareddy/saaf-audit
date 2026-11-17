// One consistent page width per context — no more 2xl…7xl drift, and never
// changes mid-workflow. narrow: memo/form pages · default: hubs/lists ·
// wide: dense tables & the dashboard.
const WIDTHS = {
  narrow: 'max-w-3xl',
  default: 'max-w-5xl',
  wide: 'max-w-7xl',
}

export default function PageContainer({ width = 'default', className = '', children }) {
  return (
    <div className={`mx-auto ${WIDTHS[width] || WIDTHS.default} px-6 py-8 lg:px-8 ${className}`}>
      {children}
    </div>
  )
}
