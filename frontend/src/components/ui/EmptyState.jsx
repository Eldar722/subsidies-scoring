export function EmptyState({ title = 'Нет данных', description = '', action }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <p className="text-slate-500 text-sm mt-2">{title}</p>
      {description && <p className="text-slate-400 text-xs mt-1">{description}</p>}
      {action}
    </div>
  )
}
