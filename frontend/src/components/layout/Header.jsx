export function Header({ title }) {
  return (
    <header className="h-14 border-b border-slate-200 bg-white flex items-center px-6">
      <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
    </header>
  )
}
