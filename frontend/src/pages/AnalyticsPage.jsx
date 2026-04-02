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
  const [activeMetric, setActiveMetric] = useState('completion_2025')
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

  // Новая структура с тремя метриками
  const metrics = data.metrics || {}
  const current = metrics[activeMetric] || {}

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Metric Tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        {data.tabs?.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveMetric(tab.id)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeMetric === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-600 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 2025 Completion Tab */}
      {activeMetric === 'completion_2025' && current.metric && (
        <div className="space-y-5">
          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Всего заявок', value: current.total_applications, icon: Equals, color: 'text-slate-900', bg: 'bg-slate-100' },
              { label: 'Исполнено', value: current.completed, icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100' },
              { label: 'Отклонено', value: current.rejected, icon: XCircle, color: 'text-red-600', bg: 'bg-red-100' },
              { label: '% Исполнения', value: (current.completion_rate * 100).toFixed(1) + '%', icon: TrendUp, color: 'text-blue-600', bg: 'bg-blue-100' },
            ].map(({ label, value, icon: Icon, color, bg }) => (
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

          {/* By Region Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <CardHeader title="Статистика по регионам" subtitle="Распределение исполненных субсидий в 2025" />
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-100">
                    {['Регион', 'Всего заявок', 'Исполнено', '% Исполнения'].map(h => (
                      <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-600 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {current.by_region?.slice(0, 15).map((r, i) => (
                    <tr key={i} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-slate-700">{r.region}</td>
                      <td className="px-4 py-3 text-slate-600">{r.total_applications}</td>
                      <td className="px-4 py-3"><span className="text-green-600 font-semibold">{r.completed}</span></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-blue-600">{(r.completion_rate * 100).toFixed(1)}%</span>
                          <div className="w-16 h-2 bg-slate-100 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-blue-500 rounded-full" 
                              style={{ width: `${r.completion_rate * 100}%` }}
                            />
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Survival Rate Tab */}
      {activeMetric === 'survival' && current.metric && (
        <div className="space-y-5">
          {/* Main Survival Metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { label: 'Производителей в 2025', value: current.initial_count, icon: Equals, color: 'text-slate-900', bg: 'bg-slate-100' },
              { label: 'Вернулось в 2026', value: current.survived_count, icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100' },
              { label: 'Процент выживаемости', value: (current.survival_percentage || 0).toFixed(1) + '%', icon: TrendUp, color: 'text-blue-600', bg: 'bg-blue-100' },
            ].map(({ label, value, icon: Icon, color, bg }) => (
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

          {/* Survival Details */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <h3 className="font-semibold text-slate-900 mb-4">Характеристика вернувшихся производителей (2026)</h3>
            {current.details ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-xs text-slate-600 font-medium mb-1">Всего заявок в 2026</p>
                  <p className="text-2xl font-bold text-slate-900">{current.details.total_2026 || 0}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-xs text-slate-600 font-medium mb-1">Исполнено в 2026</p>
                  <p className="text-2xl font-bold text-green-600">{current.details.completed_2026 || 0}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-xs text-slate-600 font-medium mb-1">% Исполнения 2026</p>
                  <p className="text-2xl font-bold text-blue-600">{((current.details.completion_rate_2026 || 0) * 100).toFixed(1)}%</p>
                </div>
              </div>
            ) : (
              <p className="text-slate-500 text-sm">Нет данных о вернувшихся производителях</p>
            )}
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <p className="text-sm text-blue-800">
              💡 <strong>Вывод:</strong> {current.summary || 'Недостаточно данных'}
            </p>
          </div>
        </div>
      )}

      {/* Year-over-Year Tab */}
      {activeMetric === 'year_over_year' && current.metric && (
        <div className="space-y-5">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Проанализировано', value: current.total_analyzed, icon: Equals, color: 'text-slate-900', bg: 'bg-slate-100' },
              { label: 'Улучшились', value: current.improved_count, icon: TrendUp, color: 'text-green-600', bg: 'bg-green-100' },
              { label: 'Без измен.', value: (current.total_analyzed - current.improved_count) || 0, icon: Equals, color: 'text-amber-600', bg: 'bg-amber-100' },
              { label: 'Ср. индекс', value: (current.avg_effectiveness_score || 0) + '%', icon: CheckCircle, color: 'text-blue-600', bg: 'bg-blue-100' },
            ].map(({ label, value, icon: Icon, color, bg }) => (
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

          {/* Detailed Table */}
          {current.total_analyzed > 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <CardHeader title="Детальный анализ производителей" subtitle="Сравнение показателей 2025 vs 2026" />
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-100">
                      {['Производитель', 'Регион', 'Индекс', 'Δ Заявок', 'Δ Сумма', 'Δ Активность', 'Статус'].map(h => (
                        <th key={h} className="text-left px-4 py-2.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {current.producers?.slice(0, 30).map((p, i) => (
                      <tr key={i} className="hover:bg-slate-50 transition-colors">
                        <td 
                          className="px-4 py-3 font-mono text-slate-700 font-semibold cursor-pointer hover:text-blue-600 transition-colors"
                          onClick={() => navigate(`/producer/${p.producer_id}`)}
                        >
                          {p.producer_id}
                        </td>
                        <td className="px-4 py-3 text-slate-500 max-w-[100px] truncate">{p.region || '—'}</td>
                        <td className="px-4 py-3">
                          <span className={`font-bold ${p.effectiveness_score >= 60 ? 'text-green-600' : p.effectiveness_score >= 40 ? 'text-amber-600' : 'text-red-500'}`}>
                            {p.effectiveness_score}%
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <Delta value={p.deltas?.apps} suffix=" заявок" />
                        </td>
                        <td className="px-4 py-3">
                          <Delta value={p.deltas?.avg_amount} suffix=" ₸" />
                        </td>
                        <td className="px-4 py-3">
                          <Delta value={p.deltas?.activity} suffix=" /мес" />
                        </td>
                        <td className="px-4 py-3">
                          {p.improved
                            ? <span className="text-[10px] font-semibold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">↑ Лучше</span>
                            : <span className="text-[10px] font-semibold text-slate-600 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-full">— Стабиль</span>
                          }
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6">
              <p className="text-yellow-800 text-sm">
                ⚠️ {current.summary || 'Недостаточно данных для анализа года-в-год'}
              </p>
            </div>
          )}
        </div>
      )}
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
