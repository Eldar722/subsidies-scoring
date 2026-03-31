const variants = {
  hidden_talent: 'bg-purple-100 text-purple-800 border border-purple-200',
  shortlisted:   'bg-green-100 text-green-800 border border-green-200',
  at_risk:       'bg-red-100 text-red-800 border border-red-200',
  score_high:    'bg-green-100 text-green-800',
  score_mid:     'bg-yellow-100 text-yellow-800',
  score_low:     'bg-red-100 text-red-800',
  success: 'bg-green-100 text-green-800 border border-green-200',
  warning: 'bg-yellow-100 text-yellow-800 border border-yellow-200',
  error:   'bg-red-100 text-red-800 border border-red-200',
  hidden:  'bg-purple-100 text-purple-800 border border-purple-200',
  default: 'bg-slate-100 text-slate-700 border border-slate-200',
}
const defaultLabels = {
  hidden_talent: '★ Скрытый талант',
  shortlisted:   '✓ Шортлист',
  at_risk:       '↓ Переоценён',
}
export function Badge({ children, variant = 'default', className = '' }) {
  const label = children !== undefined ? children : (defaultLabels[variant] ?? '')
  return (
    <span className={`inline-flex items-center rounded-full text-xs font-semibold px-2.5 py-0.5 ${variants[variant] || variants.default} ${className}`}>
      {label}
    </span>
  )
}
export function getScoreVariant(score) {
  if (score >= 0.8) return 'score_high'
  if (score >= 0.6) return 'score_mid'
  return 'score_low'
}
