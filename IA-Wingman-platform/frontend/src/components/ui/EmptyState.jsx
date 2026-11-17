export default function EmptyState({ icon: Icon, title, description, action, className = '' }) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-lg border border-dashed border-line-strong bg-surface/50 px-6 py-10 text-center ${className}`}
    >
      {Icon && (
        <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-md bg-surface-3 text-fg-subtle">
          <Icon size={22} />
        </div>
      )}
      <h3 className="text-sm font-semibold text-fg">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-fg-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
