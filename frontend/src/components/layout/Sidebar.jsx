import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChartBar, Sliders, Scales, MapTrifold, Leaf } from '@phosphor-icons/react'
import { getHealth } from '../../services/api'

const NAV_ITEMS = [
  { to: '/dashboard', icon: ChartBar, label: 'Дашборд' },
  { to: '/simulator', icon: Sliders, label: 'Симулятор' },
  { to: '/fairness', icon: Scales, label: 'Справедливость' },
  { to: '/map', icon: MapTrifold, label: 'Карта' },
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
    <aside
      className="fixed left-0 top-0 h-screen bg-white border-r border-slate-100 flex flex-col z-40"
      style={{ width: 'var(--sidebar-width, 240px)' }}
    >
      {/* Logo */}
      <div className="px-4 h-14 flex items-center border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
            <Leaf size={14} weight="fill" className="text-white" />
          </div>
          <div>
            <div className="text-slate-900 font-semibold text-sm leading-none">AI Субсидии</div>
            <div className="text-slate-400 text-[10px] leading-none mt-0.5">Decentrathon 5.0</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <p className="px-2 mb-2 text-[10px] font-semibold text-slate-400 uppercase tracking-widest">Навигация</p>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 no-underline ${isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-blue-600 rounded-r-full" />
                  )}
                  <Icon size={16} weight={isActive ? 'fill' : 'regular'} className="flex-shrink-0" />
                  <span>{item.label}</span>
                </>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-slate-100 space-y-3">
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-md ${isOnline
              ? 'bg-green-50 text-green-700 border border-green-100'
              : 'bg-red-50 text-red-600 border border-red-100'
            }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-400'}`} />
            {isOnline ? 'API онлайн' : 'Нет соединения'}
          </span>
        </div>
        <p className="text-[10px] text-slate-300 font-medium">v2.0 · 2026</p>
      </div>
    </aside>
  )
}
