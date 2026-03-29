const variants = {
  success: 'bg-green-100 text-green-800 border border-green-200',
  warning: 'bg-yellow-100 text-yellow-800 border border-yellow-200',
  error:   'bg-red-100 text-red-800 border border-red-200',
  hidden:  'bg-purple-100 text-purple-800 border border-purple-200',
  default: 'bg-slate-100 text-slate-700 border border-slate-200',
}

export function Badge({ children, variant = 'default', className = '' }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${variants[variant] || variants.default} ${className}`}>
      {children}
    </span>
  )
}
