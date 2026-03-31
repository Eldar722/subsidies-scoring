import { Tray } from '@phosphor-icons/react'
import { Button } from './Button'

export function EmptyState({ title = 'Нет данных', description = '', actionLabel, onAction, icon }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon || <Tray size={48} className="text-slate-300 mb-4" />}
      <h3 className="text-lg font-semibold text-slate-700 mb-1">{title}</h3>
      {description && <p className="text-sm text-slate-500 mb-4 max-w-sm">{description}</p>}
      {actionLabel && onAction && (
        <Button variant="secondary" size="sm" onClick={onAction}>{actionLabel}</Button>
      )}
    </div>
  )
}
