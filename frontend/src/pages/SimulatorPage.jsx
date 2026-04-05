import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion' // eslint-disable-line no-unused-vars
import { useSimulator } from '../hooks/useSimulator'
import { Badge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import { ArrowUp, ArrowDown, Star } from '@phosphor-icons/react'

const SLIDERS = [
  { key: 'completion_rate', label: 'Результативность',    description: 'Доля успешно исполненных заявок', defaultValue: 35 },
  { key: 'approval_rate',   label: 'Одобряемость',        description: 'Процент одобренных из поданных',  defaultValue: 25 },
  { key: 'diversification', label: 'Диверсификация',      description: 'Разнообразие видов животноводства', defaultValue: 20 },
  { key: 'activity',        label: 'Активность',          description: 'Регулярность подачи заявок',      defaultValue: 10 },
  { key: 'working_hours',   label: 'Рабочие часы',        description: 'Активность в рабочие часы',       defaultValue: 10 },
]

const initialWeights = Object.fromEntries(SLIDERS.map(s => [s.key, s.defaultValue]))

const SLIDER_COLORS = ['#2563EB', '#7C3AED', '#059669', '#D97706', '#DC2626']

export default function SimulatorPage() {
  const navigate = useNavigate()
  const [weights, setWeights] = useState(initialWeights)
  const { simulate, data: simResult, isLoading } = useSimulator()
  const timerRef = useRef(null)

  const total = Object.values(weights).reduce((s, v) => s + v, 0)
  const isBalanced = total === 100

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
      // Correction pass: ensure sum is exactly 100 (rounding can drift)
      const currentTotal = Object.values(newWeights).reduce((s, v) => s + v, 0)
      const diff = 100 - currentTotal
      if (diff !== 0) {
        const adjustKey = others
          .filter(s => newWeights[s.key] + diff >= 0)
          .sort((a, b) => newWeights[b.key] - newWeights[a.key])[0]?.key
        if (adjustKey) newWeights[adjustKey] = Math.max(0, newWeights[adjustKey] + diff)
      }
    }
    setWeights(newWeights)
  }

  const shortlist = simResult?.shortlist || []
  const entered   = simResult?.entered   || []
  const left      = simResult?.left      || []

  // Donut SVG for total %
  const r = 14
  const circ = 2 * Math.PI * r
  const fill = Math.min(total / 100, 1)
  const dashArray = `${fill * circ} ${circ}`

  return (
    <div className="flex gap-5 max-w-full">
      {/* Controls */}
      <div className="w-72 flex-shrink-0">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm sticky top-20 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-800">Веса факторов</h2>
              <p className="text-xs text-slate-400 mt-0.5">Авто-нормировка до 100%</p>
            </div>
            {/* Donut */}
            <div className="relative w-9 h-9">
              <svg viewBox="0 0 36 36" className="w-9 h-9 -rotate-90">
                <circle cx="18" cy="18" r={r} fill="none" stroke="#E2E8F0" strokeWidth="4" />
                <circle
                  cx="18" cy="18" r={r} fill="none"
                  stroke={isBalanced ? '#16A34A' : '#2563EB'}
                  strokeWidth="4"
                  strokeDasharray={dashArray}
                  strokeLinecap="round"
                  className="transition-all duration-300"
                />
              </svg>
              <span className={`absolute inset-0 flex items-center justify-center text-[9px] font-bold ${isBalanced ? 'text-green-600' : 'text-blue-600'}`}>
                {total}
              </span>
            </div>
          </div>

          <div className="px-5 py-4 space-y-5">
            {SLIDERS.map((s, idx) => (
              <div key={s.key}>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-700">{s.label}</label>
                  <span className="text-sm font-bold tabular-nums" style={{ color: SLIDER_COLORS[idx] }}>
                    {weights[s.key]}<sup className="text-[9px] opacity-70">%</sup>
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 mb-1.5 leading-snug">{s.description}</p>
                <input
                  type="range" min={0} max={100} value={weights[s.key]}
                  onInput={e => handleChange(s.key, parseInt(e.target.value))}
                  onChange={e => handleChange(s.key, parseInt(e.target.value))}
                  className="w-full h-1 rounded-full cursor-pointer"
                  style={{ accentColor: SLIDER_COLORS[idx] }}
                />
              </div>
            ))}
          </div>

          <div className="px-5 pb-4">
            <button
              onClick={() => setWeights(initialWeights)}
              className="w-full text-xs text-slate-500 hover:text-slate-700 py-2 rounded-lg hover:bg-slate-50 transition-colors border border-slate-200 font-medium"
            >
              Сбросить к умолчаниям
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 min-w-0 space-y-4">
        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white border border-green-200 rounded-xl p-4 shadow-xs">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 bg-green-100 rounded-lg flex items-center justify-center">
                <ArrowUp size={12} className="text-green-600" weight="bold" />
              </div>
              <span className="text-xs text-green-600 font-semibold uppercase tracking-wide">Вошли</span>
            </div>
            <div className="text-2xl font-bold text-green-700">+{entered.length}</div>
          </div>

          <div className="bg-white border border-red-200 rounded-xl p-4 shadow-xs">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 bg-red-100 rounded-lg flex items-center justify-center">
                <ArrowDown size={12} className="text-red-500" weight="bold" />
              </div>
              <span className="text-xs text-red-500 font-semibold uppercase tracking-wide">Вышли</span>
            </div>
            <div className="text-2xl font-bold text-red-600">−{left.length}</div>
          </div>

          <div className="bg-white border border-purple-200 rounded-xl p-4 shadow-xs">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 bg-purple-100 rounded-lg flex items-center justify-center">
                <Star size={12} className="text-purple-600" weight="fill" />
              </div>
              <span className="text-xs text-purple-600 font-semibold uppercase tracking-wide">Таланты</span>
            </div>
            <div className="text-2xl font-bold text-purple-700">{simResult?.hidden_talent_count ?? '—'}<span className="text-sm font-normal text-purple-400">/20</span></div>
            {simResult && (
              <div className="mt-2 bg-purple-100 rounded-full h-1 overflow-hidden">
                <div
                  className="h-full bg-purple-500 rounded-full transition-all duration-500"
                  style={{ width: `${((simResult.hidden_talent_count || 0) / 20) * 100}%` }}
                />
              </div>
            )}
          </div>
        </div>

        {/* Shortlist */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-800">Шортлист (топ-20)</h3>
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
                      <motion.div
                        key={p.producer_id}
                        layout
                        initial={{ opacity: 0, x: isEntered ? -12 : 0 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 12 }}
                        transition={{ duration: 0.18 }}
                        onClick={() => navigate(`/producer/${p.producer_id}`)}
                        className={`px-5 py-3.5 flex items-center gap-3 transition-colors cursor-pointer ${
                          isEntered
                            ? 'border-l-4 border-green-500 bg-green-50 hover:bg-green-100'
                            : idx % 2 === 0
                              ? 'border-l-4 border-transparent bg-white hover:bg-slate-50'
                              : 'border-l-4 border-transparent bg-slate-50/60 hover:bg-slate-100/60'
                        }`}
                      >
                        <span className="text-xs font-bold text-slate-400 w-6 tabular-nums text-right">{idx + 1}</span>
                        <span className="font-mono text-xs text-slate-700 font-semibold w-24">{p.producer_id}</span>
                        <span className="text-xs text-slate-400 flex-1 truncate">{p.region}{p.direction ? ` · ${p.direction}` : ''}</span>
                        {p.hidden_talent && <Badge variant="hidden_talent" />}
                        {isEntered && (
                          <span className="text-[10px] font-bold text-green-700 bg-green-100 border border-green-200 px-1.5 py-0.5 rounded-full">↑ Вошёл</span>
                        )}
                        <span className={`text-xs font-bold tabular-nums ${p.ml_score >= 0.8 ? 'text-green-600' : p.ml_score >= 0.6 ? 'text-amber-600' : 'text-red-500'}`}>
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
                <motion.div
                  key={`left-${p.producer_id}`}
                  initial={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  onClick={() => navigate(`/producer/${p.producer_id}`)}
                  className="px-5 py-3 flex items-center gap-3 border-l-4 border-red-300 bg-red-50 opacity-70 cursor-pointer hover:opacity-100 transition-opacity"
                >
                  <span className="text-xs text-slate-300 w-5">—</span>
                  <span className="font-mono text-xs text-slate-400 w-24 line-through">{p.producer_id}</span>
                  <span className="text-xs text-slate-400 flex-1 truncate">{p.region}</span>
                  <span className="text-[10px] font-bold text-red-600 bg-red-100 border border-red-200 px-1.5 py-0.5 rounded-full">↓ Вышел</span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  )
}
