import { useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, SignOut, User } from '@phosphor-icons/react'
import { useAuth } from '../../contexts/AuthContext'

const PAGE_META = {
  '/dashboard': { title: 'Дашборд',              subtitle: 'Шортлист · ML Score · Delta' },
  '/simulator': { title: 'Симулятор весов',       subtitle: 'Настройка весов · Живой пересчёт' },
  '/fairness':  { title: 'Анализ справедливости', subtitle: 'Gini · Kruskal-Wallis · Lorenz' },
  '/map':       { title: 'Карта регионов',         subtitle: 'Хороплет RK · Статистика по регионам' },
  '/analytics': { title: 'Аналитика субсидий',    subtitle: 'Эффективность · Красные флаги' },
}

export function Header() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user, signOut } = useAuth()

  const handleLogout = async () => {
    await signOut()
    navigate('/login', { replace: true })
  }
  const isProducer = pathname.startsWith('/producer/')
  const meta = isProducer
    ? { title: 'Профиль производителя', subtitle: 'SHAP · SubsidyLens AI · История' }
    : (PAGE_META[pathname] || { title: 'Дашборд', subtitle: '' })

  return (
    <header
      className="app-header-shell sticky top-0 z-[1300] flex items-center px-6 flex-shrink-0"
      style={{
        height:      'var(--header-height, 60px)',
        background:  'var(--bg-surface)',
        borderBottom:'1px solid var(--border)',
        transition:  'background 0.2s ease, border-color 0.2s ease',
      }}
    >
      {isProducer && (
        <button
          onClick={() => navigate('/dashboard')}
          className="mr-3 flex items-center justify-center w-8 h-8 rounded-lg transition-colors flex-shrink-0"
          style={{ background: 'var(--bg-subtle)', color: 'var(--text-secondary)' }}
          onMouseEnter={e => e.currentTarget.style.opacity = '0.7'}
          onMouseLeave={e => e.currentTarget.style.opacity = '1'}
          title="Назад"
        >
          <ArrowLeft size={15} weight="bold" />
        </button>
      )}
      <div className="flex-1">
        <h1
          className="text-sm font-semibold leading-none"
          style={{ color: 'var(--text-primary)' }}
        >
          {meta.title}
        </h1>
        {meta.subtitle && (
          <p
            className="text-[11px] mt-1 leading-none"
            style={{ color: 'var(--text-muted)' }}
          >
            {meta.subtitle}
          </p>
        )}
      </div>

      {/* User info + logout */}
      {user && (
        <div className="flex items-center gap-2 ml-4">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg" style={{ background: 'var(--bg-subtle)' }}>
            <User size={12} style={{ color: 'var(--text-muted)' }} />
            <span className="text-[11px] font-medium" style={{ color: 'var(--text-secondary)' }}>
              {user.email}
            </span>
          </div>
          <button
            onClick={handleLogout}
            title="Выйти"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-colors"
            style={{ background: 'var(--bg-subtle)', color: 'var(--text-muted)' }}
            onMouseEnter={e => e.currentTarget.style.background = '#fee2e2'}
            onMouseLeave={e => e.currentTarget.style.background = 'var(--bg-subtle)'}
          >
            <SignOut size={12} />
            Выйти
          </button>
        </div>
      )}
    </header>
  )
}
