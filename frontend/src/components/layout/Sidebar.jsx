import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChartBar, Sliders, Scales, MapTrifold, Leaf, ChartPie, Moon, Sun } from '@phosphor-icons/react'
import { getHealth } from '../../services/api'

const NAV_ITEMS = [
  { to: '/dashboard', icon: ChartBar,   label: 'Дашборд' },
  { to: '/simulator', icon: Sliders,    label: 'Симулятор' },
  { to: '/fairness',  icon: Scales,     label: 'Справедливость' },
  { to: '/map',       icon: MapTrifold, label: 'Карта' },
  { to: '/analytics', icon: ChartPie,   label: 'Аналитика' },
]

export function Sidebar() {
  const { data } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
    retry: false,
  })
  const isOnline = data?.status === 'ok'

  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    if (saved) return saved === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [isDark])

  return (
    <aside
      className="app-sidebar-shell fixed left-0 top-0 h-screen flex flex-col z-[1200]"
      style={{
        width:       'var(--sidebar-width, 240px)',
        background:  'var(--bg-surface)',
        borderRight: '1px solid var(--border)',
        boxShadow:   'var(--shadow-sm)',
        transition:  'background 0.2s ease, border-color 0.2s ease',
      }}
    >
      {/* Logo */}
      <div
        className="px-5 flex items-center flex-shrink-0"
        style={{
          height:       'var(--header-height, 60px)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #2563EB 0%, #7C3AED 100%)' }}
          >
            <Leaf size={15} weight="fill" className="text-white" />
          </div>
          <div>
            <div className="text-sm font-bold leading-none" style={{ color: 'var(--text-primary)' }}>
              SubsidyLens
            </div>
            <div className="text-[10px] leading-none mt-1 font-medium" style={{ color: 'var(--text-disabled)' }}>
              Скоринг и прозрачность поддержки АПК
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-5 space-y-0.5 overflow-y-auto">
        <p
          className="px-3 mb-3 text-[9px] font-bold uppercase tracking-widest"
          style={{ color: 'var(--text-disabled)' }}
        >
          Навигация
        </p>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 no-underline ${
                  isActive ? 'nav-item-active' : ''
                }`
              }
              style={({ isActive }) =>
                isActive ? {} : { color: '#6b7280' }
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full"
                      style={{ background: 'var(--color-primary)' }}
                    />
                  )}
                  {/* #7 Active: filled + blue; Inactive: medium-weight outline + gray */}
                  <Icon
                    size={16}
                    weight={isActive ? 'fill' : 'bold'}
                    className="flex-shrink-0"
                    style={{ color: isActive ? '#2563eb' : '#6b7280' }}
                  />
                  <span>{item.label}</span>
                </>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div
        className="px-4 py-4 space-y-3 flex-shrink-0"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        {/* Online status */}
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg ${
              isOnline
                ? 'bg-green-50 text-green-700 border border-green-100'
                : 'bg-red-50 text-red-600 border border-red-100'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isOnline ? 'bg-green-500 animate-pulse' : 'bg-red-400'
              }`}
            />
            {isOnline ? 'API онлайн' : 'Нет соединения'}
          </span>
        </div>

        {/* Theme toggle */}
        <button
          onClick={() => setIsDark(v => !v)}
          className="flex items-center gap-2.5 text-xs font-medium px-3 py-2 rounded-xl transition-all w-full"
          style={{
            color:      'var(--text-secondary)',
            background: 'var(--bg-subtle)',
            border:     '1px solid var(--border)',
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = '0.8'}
          onMouseLeave={e => e.currentTarget.style.opacity = '1'}
        >
          {isDark
            ? <Sun size={14} weight="bold" style={{ color: '#F59E0B' }} />
            : <Moon size={14} weight="bold" style={{ color: '#64748B' }} />
          }
          {isDark ? 'Светлая тема' : 'Тёмная тема'}
        </button>

        <p className="text-[10px] font-medium px-1" style={{ color: 'var(--text-disabled)' }}>
          v2.0 · 2026
        </p>
      </div>
    </aside>
  )
}
