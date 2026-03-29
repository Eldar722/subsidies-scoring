export function ErrorState({ message = 'Произошла ошибка', onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <p className="text-red-600 text-sm mt-2">{message}</p>
      {onRetry && <button onClick={onRetry} className="mt-3 text-blue-600 text-sm underline">Повторить</button>}
    </div>
  )
}
