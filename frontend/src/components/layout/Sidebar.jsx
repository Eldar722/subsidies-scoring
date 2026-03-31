import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChartBar, Sliders, Scales, MapTrifold, Leaf, Circle } from '@phosphor-icons/react'
import { getHealth } from '../../services/api'

const NAV_ITEMS = [
  { to: '/dashboard', icon: ChartBar,    label: 'Дашборд' },
  { to: '/simulator', icon: Sliders,     label: 'Симулятор' },
  { to: '/fairness',  icon: Scales,      label: 'Справедливость' },
  { to: '/map',       icon: MapTrifold,  label: 'Карта' },
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
    <aside className="fixed left-0 top-0 h-screen bg-white border-r border-slate-200 flex flex-col z-40" style={{ width: 240 }}>
      <div className="px-5 py-6 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Leaf size={20} weight="fill" className="text-blue-600" />
          <span className="text-blue-600 font-bold text-base tracking-tight">AI Субсидии</span>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150 no-underline ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={16} weight={isActive ? 'fill' : 'regular'} />
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-slate-100">
        <div className="flex items-center gap-2">
          <Circle size={8} weight="fill" className={isOnline ? 'text-green-500' : 'text-red-400'} />
          <span className="text-xs text-slate-400">{isOnline ? 'Сервер онлайн' : 'Нет соединения'}</span>
        </div>
      </div>
    </aside>
  )
}
