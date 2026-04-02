import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getSubsidyEffectiveness, getRedFlags } from '../services/api'
import { Skeleton } from '../components/ui/Skeleton'
import { CardHeader } from '../components/ui/Card'
import { ErrorState } from '../components/ui/ErrorState'
import {
  TrendUp, TrendDown, Warning, CheckCircle, XCircle,
  Equals, ShieldWarning, ArrowUp, ArrowDown,
} from '@phosphor-icons/react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

// ── Tabs ──
const TABS = [
  { key: 'effectiveness', label: '📈 Эффективность субсидий' },
  { key: 'redflags', label: '⚠️ Индикаторы риска' },
]

// ── Risk badge ──
function RiskBadge({ level }) {
  const map = {
    high: 'bg-red-50 text-red-700 border border-red-200',
    medium: 'bg-amber-50 text-amber-700 border border-amber-200',
    low: 'bg-slate-100 text-slate-600 border border-slate-200',
  }
  const labels = { high: '🔴 Высокий', medium: '🟡 Средний', low: '⚪ Низкий' }
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${map[level] || map.low}`}>
      {labels[level] || level}
    </span>
  )
}

// ── Delta display ──
function Delta({ value, suffix = '' }) {
  if (value === undefined || value === null) return <span className="text-slate-400">—</span>
  const pos = value > 0
  const zero = value === 0
  return (
    <span className={`font-semibold tabular-nums ${zero ? 'text-slate-400' : pos ? 'text-green-600' : 'text-red-500'}`}>
      {pos ? '+' : ''}{typeof value === 'number' ? value.toFixed(2) : value}{suffix}
    </span>
  )
}

// ── Subsidy Effectiveness Tab ──
function EffectivenessTab() {
  const navigate = useNavigate()
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['subsidy-effectiveness'],
    queryFn: getSubsidyEffectiveness,
    staleTime: 300_000,
    retry: 1,
  })

  if (isError) return <ErrorState message="Не удалось загрузить данные эффективности субсидий." onRetry={() => refetch()} />

  if (isLoading) return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        {[1,2,3].map(i => <Skeleton key={i} className="h-24 rounded-xl" />)}
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )

  if (!data) return <p className="text-slate-400 text-sm py-8 text-center">Нет данных</p>

  const producers = data.producers || []
  const improved = producers.filter(p => p.improved)
  const needsReview = producers.filter(p => p.needs_review)

  // Гистограмма топ-20 по effectiveness score
  const chartData = producers.slice(0, 20).map(p => ({
    id: p.producer_id,
    score: p.effectiveness_score,
    improved: p.improved,
  }))

  return (
    <div className="space-y-5 animate-fade-in">
      {/* KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Проанализировано', value: data.total_analyzed, color: 'text-slate-900', bg: 'bg-slate-100', icon: Equals },
          { label: 'Улучшились', value: data.improved_count, color: 'text-green-600', bg: 'bg-green-100', icon: TrendUp },
          { label: 'На проверку', value: data.needs_review_count, color: 'text-amber-600', bg: 'bg-amber-100', icon: Warning },
          { label: 'Ср. эффективность', value: data.avg_effectiveness_score + '%', color: 'text-blue-600', bg: 'bg-blue-100', icon: CheckCircle },
        ].map(({ label, value, color, bg, icon: Icon }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <div className="flex items-start justify-between mb-3">
              <p className="text-xs text-slate-500 font-medium">{label}</p>
              <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center`}>
                <Icon size={15} className={color} weight="bold" />
              </div>
            </div>
            <div className={`text-2xl font-bold ${color}`}>{value ?? '—'}</div>
          </div>
        ))}
      </div>

      {/* Bar chart effectiveness scores */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <CardHeader title="Топ-20 производителей по индексу эффективности" subtitle="Сравнение показателей 2025 → 2026 после получения субсидии" />
        <div className="p-5" style={{ height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 20 }}>
              <XAxis dataKey="id" tick={{ fontSize: 9, fill: '#94a3b8' }} angle={-30} textAnchor="end" interval={0} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const d = payload[0].payload
                  return (
                    <div className="bg-white border border-slate-200 rounded-lg p-2.5 shadow text-xs">
                      <p className="font-mono font-semibold text-slate-800">{d.id}</p>
                      <p className="text-slate-500 mt-0.5">Индекс: <span className="font-bold text-blue-600">{d.score}%</span></p>
                    </div>
                  )
                }}
              />
              <Bar dataKey="score" radius={[4, 4, 0, 0]} maxBarSize={24}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.improved ? '#16a34a' : '#dc2626'} fillOpacity={0.82} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Producers table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <CardHeader title="Детальный анализ" subtitle="Сравнение поведения до / после получения субсидии" />
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                {['Производитель', 'Регион', 'Индекс', 'Δ Исполнение', 'Δ Сумма', 'Δ Активность', 'Статус'].map(h => (
                  <th key={h} className="text-left px-4 py-2.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {producers.slice(0, 30).map((p, i) => (
                <tr key={i} className="hover:bg-slate-50 transition-colors">
                  <td
                    className="px-4 py-3 font-mono text-slate-700 font-semibold cursor-pointer hover:text-blue-600 transition-colors"
                    onClick={() => navigate(`/producer/${p.producer_id}`)}
                  >
                    {p.producer_id}
                  </td>
                  <td className="px-4 py-3 text-slate-500 max-w-[120px] truncate">{p.region || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`font-bold ${p.effectiveness_score >= 60 ? 'text-green-600' : p.effectiveness_score >= 40 ? 'text-amber-600' : 'text-red-500'}`}>
                      {p.effectiveness_score}%
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Delta value={p.deltas?.completion_rate ? p.deltas.completion_rate * 100 : null} suffix="%" />
                  </td>
                  <td className="px-4 py-3">
                    <Delta value={p.deltas?.avg_amount} suffix=" ₸" />
                  </td>
                  <td className="px-4 py-3">
                    <Delta value={p.deltas?.activity} suffix=" зяв/мес" />
                  </td>
                  <td className="px-4 py-3">
                    {p.improved
                      ? <span className="text-[10px] font-semibold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">↑ Улучшился</span>
                      : <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">⚠ На проверку</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ── Red Flags Tab ──
function RedFlagsTab() {
  const navigate = useNavigate()
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['red-flags'],
    queryFn: getRedFlags,
    staleTime: 300_000,
    retry: 1,
  })
  const [expanded, setExpanded] = useState(null)

  if (isError) return <ErrorState message="Не удалось загрузить индикаторы риска." onRetry={() => refetch()} />

  if (isLoading) return (
    <div className="space-y-3">
      {[1,2,3,4].map(i => <Skeleton key={i} className="h-20 rounded-xl" />)}
    </div>
  )

  if (!data) return <p className="text-slate-400 text-sm py-8 text-center">Нет данных</p>

  const flags = data.flags || []

  return (
    <div className="space-y-5 animate-fade-in">
      {/* KPI */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Всего флагов', value: data.total_flags, color: 'text-slate-900', bg: 'bg-slate-100', icon: ShieldWarning },
          { label: 'Высокий риск', value: data.high_risk, color: 'text-red-600', bg: 'bg-red-50 border border-red-100', icon: XCircle },
          { label: 'Средний риск', value: data.medium_risk, color: 'text-amber-600', bg: 'bg-amber-50 border border-amber-100', icon: Warning },
        ].map(({ label, value, color, bg, icon: Icon }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <div className="flex items-start justify-between mb-3">
              <p className="text-xs text-slate-500 font-medium">{label}</p>
              <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center`}>
                <Icon size={15} className={color} weight="bold" />
              </div>
            </div>
            <div className={`text-2xl font-bold ${color}`}>{value ?? '—'}</div>
          </div>
        ))}
      </div>

      {/* Info box */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <ShieldWarning size={16} className="text-amber-600 flex-shrink-0 mt-0.5" weight="fill" />
          <div>
            <p className="text-xs font-semibold text-amber-800 mb-1">Примечание</p>
            <p className="text-xs text-amber-700 leading-relaxed">
              Флаги — это индикаторы для ручной проверки комиссией, а не автоматические решения.
              Высокий ML-балл не отменяет необходимость проверки при наличии флагов.
            </p>
          </div>
        </div>
      </div>

      {/* Flags list */}
      <div className="space-y-3">
        {flags.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 text-center">
            <CheckCircle size={32} className="text-green-400 mx-auto mb-3" weight="light" />
            <p className="text-slate-600 font-medium">Подозрительных паттернов не обнаружено</p>
            <p className="text-slate-400 text-xs mt-1">Система не выявила аномалий в поданных заявках</p>
          </div>
        ) : flags.map((flag, i) => (
          <div
            key={i}
            className={`bg-white rounded-xl border shadow-sm overflow-hidden transition-all duration-200 ${
              flag.risk_level === 'high' ? 'border-red-200' :
              flag.risk_level === 'medium' ? 'border-amber-200' : 'border-slate-200'
            }`}
          >
            <button
              className="w-full px-5 py-4 flex items-start gap-3 text-left hover:bg-slate-50 transition-colors"
              onClick={() => setExpanded(expanded === i ? null : i)}
            >
              <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center mt-0.5 ${
                flag.risk_level === 'high' ? 'bg-red-100' :
                flag.risk_level === 'medium' ? 'bg-amber-100' : 'bg-slate-100'
              }`}>
                <Warning size={15} className={
                  flag.risk_level === 'high' ? 'text-red-600' :
                  flag.risk_level === 'medium' ? 'text-amber-600' : 'text-slate-500'
                } weight="fill" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="text-sm font-semibold text-slate-800">{flag.title}</span>
                  <RiskBadge level={flag.risk_level} />
                  {flag.affected_count > 0 && (
                    <span className="text-[10px] text-slate-400">{flag.affected_count} затронутых</span>
                  )}
                </div>
                <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">{flag.description}</p>
              </div>
              <span className="text-slate-300 text-lg leading-none flex-shrink-0 mt-1">
                {expanded === i ? '−' : '+'}
              </span>
            </button>

            {expanded === i && (
              <div className="px-5 pb-4 pt-0 border-t border-slate-100">
                <p className="text-xs text-slate-600 leading-relaxed mt-3 mb-3">{flag.description}</p>
                {flag.producer_ids?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Затронутые производители</p>
                    <div className="flex flex-wrap gap-1.5">
                      {flag.producer_ids.slice(0, 12).map(pid => (
                        <button
                          key={pid}
                          onClick={() => navigate(`/producer/${pid}`)}
                          className="font-mono text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded hover:bg-blue-100 hover:text-blue-700 transition-colors cursor-pointer"
                        >
                          {pid}
                        </button>
                      ))}
                      {flag.producer_ids.length > 12 && (
                        <span className="text-[10px] text-slate-400">+{flag.producer_ids.length - 12} ещё</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main Page ──
export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState('effectiveness')

  return (
    <div className="space-y-5 max-w-full animate-fade-in">
      {/* Page header */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-5 py-4">
        <h1 className="text-base font-bold text-slate-900 leading-tight">Аналитика субсидий</h1>
        <p className="text-xs text-slate-500 mt-1">
          Оценка эффективности выданных субсидий и выявление подозрительных паттернов
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 text-xs font-semibold py-2.5 px-4 rounded-lg transition-all duration-200 ${
              activeTab === tab.key
                ? 'bg-white shadow-sm text-slate-900'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'effectiveness' ? <EffectivenessTab /> : <RedFlagsTab />}
    </div>
  )
}
