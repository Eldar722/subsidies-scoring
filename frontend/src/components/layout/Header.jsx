import { useLocation } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Lightning } from '@phosphor-icons/react'
import { runPipeline } from '../../services/api'
import { useToast } from '../ui/Toast'

const TITLES = {
  '/dashboard': 'Дашборд',
  '/simulator': 'Симулятор весов',
  '/fairness': 'Анализ справедливости',
  '/map': 'Карта регионов',
}

const SUBTITLES = {
  '/dashboard': 'Шортлист производителей · ML Score · Delta',
  '/simulator': 'Настройка весов · Живой пересчёт',
  '/fairness': 'Gini · Kruskal-Wallis · Lorenz · Z-score',
  '/map': 'Хороплет RK · Статистика по регионам',
}

export function Header() {
  const { pathname } = useLocation()
  const { showToast } = useToast()
  const isProducer = pathname.startsWith('/producer/')
  const title = isProducer ? 'Профиль производителя' : (TITLES[pathname] || 'Дашборд')
  const subtitle = isProducer ? 'SHAP · Gemini AI · История' : (SUBTITLES[pathname] || '')

  const { mutate, isPending } = useMutation({
    mutationFn: runPipeline,
    onSuccess: (res) => {
      if (res?.status === 'started') {
        showToast({ message: 'Пайплайн запущен — обновит модель за ~60–120 сек', type: 'success' })
      } else {
        showToast({ message: `Пайплайн завершён за ${res?.duration_seconds ?? '?'}с`, type: 'success' })
      }
    },
    onError: (err) => {
      const detail = err?.response?.data?.detail || 'Ошибка запуска пайплайна'
      showToast({ message: detail, type: 'error' })
    },
  })

  return (
    <header
      className="sticky top-0 z-30 flex items-center justify-between px-6 border-b border-slate-100 bg-white/95 backdrop-blur-sm"
      style={{ height: 'var(--header-height, 56px)' }}
    >
      <div>
        <h1 className="text-sm font-semibold text-slate-900 leading-none">{title}</h1>
        {subtitle && <p className="text-[11px] text-slate-400 mt-0.5 leading-none">{subtitle}</p>}
      </div>

      <button
        onClick={() => mutate()}
        disabled={isPending}
        className="inline-flex items-center gap-2 bg-blue-600 text-white text-xs font-medium px-3.5 py-2 rounded-lg shadow-sm hover:bg-blue-700 active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
      >
        {isPending
          ? <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          : <Lightning size={13} weight="fill" />
        }
        Запустить пайплайн
      </button>
    </header>
  )
}
