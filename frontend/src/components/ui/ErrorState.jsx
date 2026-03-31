import { Warning, ArrowCounterClockwise } from '@phosphor-icons/react'
import { Button } from './Button'

export function ErrorState({ message = 'Что-то пошло не так', onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center bg-red-50 border border-red-200 rounded-xl">
      <Warning size={48} className="text-red-400 mb-3" />
      <h3 className="text-base font-semibold text-red-800 mb-1">Ошибка загрузки</h3>
      {message && <p className="text-sm text-red-600 mb-4 max-w-sm">{message}</p>}
      {onRetry && (
        <Button variant="danger" size="sm" onClick={onRetry}>
          <ArrowCounterClockwise size={14} /> Повторить
        </Button>
      )}
    </div>
  )
}
