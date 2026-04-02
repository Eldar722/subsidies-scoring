export function Card({ children, className = '' }) {
  return (
    <div
      className={`rounded-2xl overflow-hidden ${className}`}
      style={{
        background:   'var(--bg-surface)',
        border:       '1px solid var(--border)',
        boxShadow:    'var(--shadow-md)',
        transition:   'background 0.2s ease, border-color 0.2s ease, box-shadow 0.15s ease',
      }}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action, className = '' }) {
  return (
    <div
      className={`px-5 py-4 flex items-start justify-between gap-4 ${className}`}
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      <div>
        <h3
          className="text-sm font-semibold leading-snug"
          style={{ color: 'var(--text-primary)' }}
        >
          {title}
        </h3>
        {subtitle && (
          <p
            className="text-xs mt-0.5 leading-snug"
            style={{ color: 'var(--text-disabled)' }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  )
}

export function CardBody({ children, className = '' }) {
  return (
    <div className={`p-5 ${className}`}>
      {children}
    </div>
  )
}
