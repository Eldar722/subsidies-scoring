export function Button({ children, variant = 'primary', size = 'md', loading = false, disabled = false, onClick, className = '' }) {
  // TODO P2: реализовать варианты primary/secondary/ghost/danger
  return (
    <button onClick={onClick} disabled={disabled || loading} className={className}>
      {loading ? '...' : children}
    </button>
  )
}
