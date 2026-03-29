import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../../services/api'

const NAV_ITEMS = [
  { to: '/dashboard', icon: '📊', label: 'Дашборд' },
  { to: '/simulator', icon: '🎮', label: 'Симулятор' },
  { to: '/fairness', icon: '⚖️', label: 'Справедливость' },
  { to: '/map', icon: '🗺️', label: 'Карта' },
]

export function Sidebar() {
  const { data } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
    retry: false,
  })

  const isOnline = data?.status === 'ok'

  return (
    <aside className="fixed left-0 top-0 h-screen bg-slate-900 flex flex-col" style={{ width: 240 }}>
      {/* Logo */}
      <div className="px-5 py-6 border-b border-slate-700">
        <span className="text-white font-bold text-base tracking-tight">🌾 AI Субсидии</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 space-y-1">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 mx-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`
            }
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* API Status */}
      <div className="px-4 py-4 border-t border-slate-700">
        <div className="flex items-center gap-2">
          <span className={`text-xs ${isOnline ? 'text-green-400' : 'text-red-400'}`}>●</span>
          <span className="text-xs text-slate-400">
            {isOnline ? 'Сервер онлайн' : 'Нет соединения'}
          </span>
        </div>
      </div>
    </aside>
  )
}
