import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion' // eslint-disable-line no-unused-vars
import { useSimulator } from '../hooks/useSimulator'
import { Badge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'

const SLIDERS = [
  { key: 'completion_rate', label: 'Результативность', emoji: '✅', description: 'Доля успешно исполненных заявок', defaultValue: 35 },
  { key: 'approval_rate',   label: 'Одобряемость заявок', emoji: '📋', description: 'Процент одобренных из поданных', defaultValue: 25 },
  { key: 'diversification', label: 'Диверсификация', emoji: '🌿', description: 'Разнообразие видов животноводства', defaultValue: 20 },
  { key: 'activity',        label: 'Активность подачи', emoji: '📨', description: 'Регулярность подачи заявок', defaultValue: 10 },
  { key: 'working_hours',   label: 'Рабочие часы', emoji: '⏱', description: 'Активность в рабочие часы', defaultValue: 10 },
]

const initialWeights = Object.fromEntries(SLIDERS.map(s => [s.key, s.defaultValue]))

export default function SimulatorPage() {
  const [weights, setWeights] = useState(initialWeights)
  const { simulate, data: simResult, isLoading } = useSimulator()
  const timerRef = useRef(null)

  const total = Object.values(weights).reduce((s, v) => s + v, 0)

  useEffect(() => {
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => simulate({ weights, topN: 20 }), 300)
    return () => clearTimeout(timerRef.current)
  }, [weights, simulate])

  const handleChange = (key, newVal) => {
    const delta = newVal - weights[key]
    const others = SLIDERS.filter(s => s.key !== key)
    const othersTotal = others.reduce((s, o) => s + weights[o.key], 0)
    const newWeights = { ...weights, [key]: newVal }
    if (othersTotal > 0 && delta !== 0) {
      others.forEach(s => {
        const ratio = weights[s.key] / othersTotal
        newWeights[s.key] = Math.max(0, Math.round(weights[s.key] - delta * ratio))
      })
    }
    setWeights(newWeights)
  }

  const shortlist = simResult?.shortlist || []
  const entered = simResult?.entered || []
  const left = simResult?.left || []

  return (
    <div className="flex gap-6">
      {/* Sliders */}
      <div className="w-80 flex-shrink-0">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sticky top-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-1">Веса факторов</h2>
          <p className="text-xs text-slate-400 mb-5">Изменяй веса — шортлист обновляется автоматически</p>
          <div className="space-y-5">
            {SLIDERS.map(s => (
              <div key={s.key}>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-sm font-medium text-slate-700">{s.emoji} {s.label}</label>
                  <span className="text-sm font-bold text-blue-600 tabular-nums w-10 text-right">{weights[s.key]}%</span>
                </div>
                <p className="text-xs text-slate-400 mb-1.5">{s.description}</p>
                <input type="range" min={0} max={100} value={weights[s.key]}
                  onChange={e => handleChange(s.key, parseInt(e.target.value))}
                  className="w-full accent-blue-600 h-1.5" />
              </div>
            ))}
          </div>
          <div className="mt-5 pt-4 border-t border-slate-100 flex justify-between items-center">
            <span className="text-sm text-slate-500">Сумма весов:</span>
            <span className={`text-sm font-bold tabular-nums ${total === 100 ? 'text-green-600' : 'text-amber-600'}`}>
              {total}% {total === 100 ? '✓' : '⚠ авто-нормировка'}
            </span>
          </div>
          <button onClick={() => setWeights(initialWeights)}
            className="mt-3 w-full text-xs text-slate-500 hover:text-slate-700 py-1.5 rounded-lg hover:bg-slate-50 transition-colors border border-slate-200">
            Сбросить к умолчаниям
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-green-50 border border-green-200 rounded-xl p-4">
            <div className="text-xs text-green-600 font-medium uppercase tracking-wide mb-1">Вошли в шортлист</div>
            <div className="text-3xl font-bold text-green-700">+{entered.length}</div>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <div className="text-xs text-red-600 font-medium uppercase tracking-wide mb-1">Вышли из шортлиста</div>
            <div className="text-3xl font-bold text-red-700">−{left.length}</div>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
            <div className="text-xs text-purple-600 font-medium uppercase tracking-wide mb-1">Скрытых талантов</div>
            <div className="text-3xl font-bold text-purple-700">{simResult?.hidden_talent_count ?? '—'}/20</div>
            {simResult && (
              <div className="mt-2 bg-white rounded-full h-1.5 overflow-hidden">
                <div className="h-full bg-purple-500 rounded-full transition-all duration-500"
                  style={{ width: `${((simResult.hidden_talent_count || 0) / 20) * 100}%` }} />
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700">Шортлист (топ-20)</h3>
            {isLoading && <span className="text-xs text-slate-400 animate-pulse">Пересчёт...</span>}
          </div>
          <div className="divide-y divide-slate-100">
            {isLoading && !simResult
              ? Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="px-5 py-3"><Skeleton className="h-5 w-full" /></div>
                ))
              : (
                <AnimatePresence mode="popLayout">
                  {shortlist.map((p, idx) => {
                    const isEntered = entered.some(e => e.producer_id === p.producer_id)
                    return (
                      <motion.div key={p.producer_id} layout
                        initial={{ opacity: 0, x: isEntered ? -16 : 0 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 16 }}
                        transition={{ duration: 0.2 }}
                        className={`px-5 py-3 flex items-center gap-4 transition-colors ${isEntered ? 'border-l-4 border-green-500 bg-green-50' : 'border-l-4 border-transparent hover:bg-slate-50'}`}>
                        <span className="text-xs text-slate-400 w-5 tabular-nums">{idx + 1}</span>
                        <span className="font-mono text-xs text-slate-700 w-20">{p.producer_id}</span>
                        <span className="text-xs text-slate-500 flex-1">{p.region} · {p.direction}</span>
                        {p.hidden_talent && <Badge variant="hidden_talent" />}
                        {isEntered && <span className="text-xs font-semibold text-green-700 bg-green-100 px-2 py-0.5 rounded-full">↑ Вошёл</span>}
                        <span className={`text-xs font-bold tabular-nums ${p.ml_score >= 0.8 ? 'text-green-600' : p.ml_score >= 0.6 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {(p.ml_score * 100).toFixed(1)}%
                        </span>
                      </motion.div>
                    )
                  })}
                </AnimatePresence>
              )
            }
            <AnimatePresence>
              {left.map(p => (
                <motion.div key={`left-${p.producer_id}`} initial={{ opacity: 1 }} exit={{ opacity: 0, height: 0 }}
                  className="px-5 py-3 flex items-center gap-4 border-l-4 border-red-400 bg-red-50">
                  <span className="text-xs text-slate-400 w-5">—</span>
                  <span className="font-mono text-xs text-slate-500 w-20 line-through">{p.producer_id}</span>
                  <span className="text-xs text-slate-400 flex-1">{p.region}</span>
                  <span className="text-xs font-semibold text-red-600 bg-red-100 px-2 py-0.5 rounded-full">↓ Вышел</span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  )
}
