import { useLocation } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Lightning } from '@phosphor-icons/react'
import { runPipeline } from '../../services/api'
import { useToast } from '../ui/Toast'

const TITLES = {
  '/dashboard': 'Дашборд',
  '/simulator': 'Симулятор',
  '/fairness':  'Справедливость',
  '/map':       'Карта регионов',
}

export function Header() {
  const { pathname } = useLocation()
  const { showToast } = useToast()
  const title = pathname.startsWith('/producer/') ? 'Профиль производителя' : (TITLES[pathname] || 'Дашборд')

  const { mutate, isPending } = useMutation({
    mutationFn: runPipeline,
    onSuccess: () => showToast({ message: 'Пайплайн запущен успешно', type: 'success' }),
    onError: ()  => showToast({ message: 'Ошибка запуска пайплайна', type: 'error' }),
  })

  return (
    <header className="sticky top-0 h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 z-30">
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <button
        onClick={() => mutate()}
        disabled={isPending}
        className="flex items-center gap-2 bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isPending
          ? <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          : <Lightning size={14} weight="fill" />
        }
        Запустить пайплайн
      </button>
    </header>
  )
}
