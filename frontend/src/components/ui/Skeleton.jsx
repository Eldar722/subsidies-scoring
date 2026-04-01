export function Skeleton({ variant = 'text', rows = 5, className = '' }) {
  const base = 'skeleton-shimmer rounded-md'
  if (variant === 'card')   return <div className={`${base} h-24 w-full rounded-xl ${className}`} />
  if (variant === 'chart')  return <div className={`${base} h-48 w-full rounded-xl ${className}`} />
  if (variant === 'circle') return <div className={`${base} h-10 w-10 rounded-full ${className}`} />
  if (variant === 'table') {
    return (
      <tbody>
        {Array.from({ length: rows }).map((_, i) => (
          <tr key={i} className="border-b border-slate-100">
            {Array.from({ length: 5 }).map((_, j) => (
              <td key={j} className="px-4 py-3.5">
                <div className={`${base} h-3.5 w-full`} />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    )
  }
  return <div className={`${base} h-4 w-full ${className}`} />
}
