const variants = {
  hidden_talent: 'bg-purple-50 text-purple-700 border border-purple-200 ring-1 ring-purple-100',
  shortlisted: 'bg-green-50  text-green-700  border border-green-200',
  at_risk: 'bg-red-50    text-red-700    border border-red-200',
  score_high: 'bg-green-50  text-green-700  border border-green-200',
  score_mid: 'bg-amber-50  text-amber-700  border border-amber-200',
  score_low: 'bg-red-50    text-red-700    border border-red-200',
  success: 'bg-green-50  text-green-700  border border-green-200',
  warning: 'bg-amber-50  text-amber-700  border border-amber-200',
  error: 'bg-red-50    text-red-700    border border-red-200',
  hidden: 'bg-purple-50 text-purple-700 border border-purple-200 ring-1 ring-purple-100',
  neutral: 'bg-slate-100 text-slate-600  border border-slate-200',
  default: 'bg-slate-100 text-slate-600  border border-slate-200',
}

const defaultLabels = {
  hidden_talent: '★ Скрытый талант',
  shortlisted: '✓ Шортлист',
  at_risk: '↓ Переоценён',
}

export function Badge({ children, variant = 'default', className = '' }) {
  const label = children !== undefined ? children : (defaultLabels[variant] ?? '')
  return (
    <span className={`inline-flex items-center rounded-full text-xs font-semibold px-2 py-0.5 tracking-tight ${variants[variant] || variants.default} ${className}`}>
      {label}
    </span>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function getScoreVariant(score) {
  if (score >= 0.8) return 'score_high'
  if (score >= 0.6) return 'score_mid'
  return 'score_low'
}
