export function Card({ children, className = '', variant = 'default' }) {
  const base = 'rounded-xl border'
  const variants = {
    default: 'bg-white border-slate-200 shadow-sm',
    muted: 'bg-slate-50 border-slate-200',
    outline: 'bg-white border-slate-200',
  }
  return (
    <div className={`${base} ${variants[variant] || variants.default} ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action, className = '' }) {
  return (
    <div className={`px-5 py-4 border-b border-slate-100 flex items-start justify-between gap-4 ${className}`}>
      <div>
        <h3 className="text-sm font-semibold text-slate-800 leading-snug">{title}</h3>
        {subtitle && <p className="text-xs text-slate-400 mt-0.5 leading-snug">{subtitle}</p>}
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
