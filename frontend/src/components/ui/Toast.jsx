export function Toast({ message, type = 'success' }) {
  // TODO P2: auto-dismiss 3s, позиционирование
  return <div className="bg-green-600 text-white rounded-lg px-4 py-2 shadow-lg">{message}</div>
}
