import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion' // eslint-disable-line no-unused-vars
import {
  DownloadSimple, Buildings, ListChecks, Star, TrendUp, X,
  Play, SpinnerGap, CheckCircle, XCircle, Gauge, Warning,
} from '@phosphor-icons/react'
import { getStats, getMetrics, runPipeline, getPipelineStatus, getDriftStatus } from '../services/api'
import { useShortlist } from '../hooks/useShortlist'
import { Badge, getScoreVariant } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import { useToast } from '../components/ui/Toast'
import { ErrorState } from '../components/ui/ErrorState'
import { ProducerSidePanel } from '../components/features/ProducerSidePanel'

function DeltaCell({ delta }) {
  if (delta > 0) return (
    <span
      title={`Недооценён FCFS на ${delta} позиций`}
      className="inline-flex items-center gap-1 text-green-700 font-semibold text-xs bg-green-50 border border-green-100 px-2 py-0.5 rounded-full cursor-help"
    >
      ↑ +{delta}
    </span>
  )
  if (delta < 0) return (
    <span
      title={`Переоценён FCFS на ${Math.abs(delta)} позиций`}
      className="inline-flex items-center gap-1 text-red-600 font-semibold text-xs bg-red-50 border border-red-100 px-2 py-0.5 rounded-full cursor-help"
    >
      ↓ {delta}
    </span>
  )
  return <span className="text-slate-300 text-xs font-medium" title="Совпадает с FCFS">—</span>
}

function downloadCSV(data) {
  const h = ['ID', 'Регион', 'Направление', 'ML Score', 'ML Ранг', 'FCFS Ранг', 'Delta', 'Скрытый талант']
  const rows = data.map(p => [
    p.producer_id, p.region, p.direction,
    (p.ml_score * 100).toFixed(1) + '%',
    p.ml_rank, p.fcfs_rank, p.delta,
    p.hidden_talent ? 'Да' : 'Нет',
  ])
  const quoteVal = v => `"${String(v ?? '').replace(/"/g, '""')}"`
  const csv = [h, ...rows].map(r => r.map(quoteVal).join(',')).join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'shortlist.csv'
  a.click()
}

// ── Pipeline Button with WebSocket + polling fallback ──
function PipelineButton() {
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  const [running, setRunning] = useState(false)
  const [stage, setStage] = useState('')
  const wsRef = useRef(null)
  const pollRef = useRef(null)

  const stopAll = () => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null }
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const handleFinished = (status) => {
    stopAll()
    setRunning(false)
    setStage('')
    if (status.last_error) {
      showToast({ message: `Ошибка обучения: ${status.last_error.slice(0, 80)}`, type: 'error' })
    } else if (status.last_metrics) {
      const auc = status.last_metrics?.roc_auc?.toFixed(4)
      showToast({ message: `Модель обновлена! AUC: ${auc}`, type: 'success' })
      queryClient.invalidateQueries()
    }
  }

  const startPolling = () => {
    pollRef.current = setInterval(async () => {
      try {
        const status = await getPipelineStatus()
        if (!status.running) handleFinished(status)
      } catch {
        // ignore poll errors
      }
    }, 2000)
  }

  const startWebSocket = () => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const wsUrl = apiUrl.replace(/^http(s?)/, (_, s) => `ws${s}`) + '/api/pipeline/ws'
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => setStage('Инициализация...')

    ws.onmessage = (event) => {
      try {
        const status = JSON.parse(event.data)
        if (status.running) setStage('Обучение модели...')
        if (!status.running) handleFinished(status)
      } catch { /* ignore parse errors */ }
    }

    ws.onerror = () => {
      // WebSocket failed — fall back to polling
      wsRef.current = null
      setStage('Обучение...')
      startPolling()
    }

    ws.onclose = () => { wsRef.current = null }
  }

  useEffect(() => () => stopAll(), [])

  const handleRun = async () => {
    try {
      setRunning(true)
      setStage('Запуск...')
      await runPipeline()
      showToast({ message: 'Пайплайн запущен', type: 'info' })
      startWebSocket()
    } catch (err) {
      setRunning(false)
      setStage('')
      const msg = err?.response?.data?.detail || 'Не удалось запустить пайплайн'
      showToast({ message: msg, type: 'error' })
    }
  }

  return (
    <button
      id="pipeline-run-btn"
      onClick={handleRun}
      disabled={running}
      className={`inline-flex items-center gap-2 text-xs font-semibold px-3.5 py-2 rounded-lg transition-all duration-200 shadow-sm ${
        running
          ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
          : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-[0.97]'
      }`}
    >
      {running
        ? <><SpinnerGap size={13} className="animate-spin" /> {stage || 'Обучение...'}</>
        : <><Play size={13} weight="fill" /> Запустить пайплайн</>
      }
    </button>
  )
}

// ── Drift Status Banner ──
function DriftBanner() {
  const { data: drift } = useQuery({
    queryKey: ['drift-status'],
    queryFn: getDriftStatus,
    staleTime: 120_000,
    retry: false,
  })
  if (!drift) return null
  const isWarning = drift.status === 'warning' || drift.status === 'critical'
  if (!isWarning) return null
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl border text-xs font-medium bg-amber-50 border-amber-200 text-amber-800">
      <Gauge size={14} className="text-amber-500 flex-shrink-0" weight="fill" />
      <span>
        Дрифт модели обнаружен · {drift.low_confidence_pct?.toFixed(1)}% заявок с низкой уверенностью ·{' '}
        <span className="font-semibold">Рекомендуется переобучение</span>
      </span>
      {drift.drifted_features?.length > 0 && (
        <div className="ml-auto flex gap-1 flex-shrink-0">
          {drift.drifted_features.slice(0, 3).map(f => (
            <span key={f} className="bg-amber-100 border border-amber-200 text-amber-700 px-1.5 py-0.5 rounded-md text-[10px] font-semibold">{f}</span>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Model Metrics strip ──
function MetricsStrip() {
  const { data: metrics } = useQuery({ queryKey: ['metrics'], queryFn: getMetrics, staleTime: 60_000 })
  if (!metrics) return null

  const fcfs = metrics.vs_fcfs
  const items = [
    { label: 'ROC-AUC', value: metrics.roc_auc?.toFixed(4), color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-100', desc: 'Hold-out 2026' },
    { label: 'F1-Score', value: metrics.best_f1?.toFixed(4), color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-100', desc: 'Лучший F1' },
    { label: 'Precision', value: metrics.precision?.toFixed(4), color: 'text-purple-600', bg: 'bg-purple-50', border: 'border-purple-100', desc: 'Точность' },
    { label: 'Recall', value: metrics.recall?.toFixed(4), color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100', desc: 'Полнота' },
    { label: 'CV AUC', value: metrics.cv_auc_mean?.toFixed(4), color: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-200', desc: 'Cross-val 2025' },
  ]

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-5 gap-3">
        {items.map(item => item.value && (
          <div key={item.label} className={`${item.bg} border ${item.border} rounded-lg px-3 py-2.5`}>
            <div className="text-[10px] text-slate-500 font-medium mb-0.5">{item.label}</div>
            <div className={`text-base font-bold tabular-nums leading-none ${item.color}`}>{item.value}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">{item.desc}</div>
          </div>
        ))}
      </div>
      {fcfs && (
        <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-green-200 bg-green-50 text-xs">
          <CheckCircle size={14} className="text-green-600 flex-shrink-0" weight="fill" />
          <span className="text-green-800 font-semibold">ML vs FCFS:</span>
          <span className="text-green-700">
            F1 {fcfs.our_f1?.toFixed(2)} vs FCFS {fcfs.fcfs_f1?.toFixed(2)}
            <span className="ml-1.5 font-bold text-green-600">{fcfs.improvement_f1}</span>
          </span>
          <span className="text-green-600 mx-1">·</span>
          <span className="text-green-700">
            AUC {fcfs.our_auc?.toFixed(2)} vs FCFS {fcfs.fcfs_auc?.toFixed(2)}
            <span className="ml-1.5 font-bold text-green-600">{fcfs.improvement_auc}</span>
          </span>
          <span className="ml-auto text-[10px] text-green-600 font-medium">
            Temporal holdout 2026 · {metrics.hidden_talents_found ?? '—'} скрытых талантов
          </span>
        </div>
      )}
    </div>
  )
}

const KPI_CONFIG = [
  { key: 'producers', label: 'Производителей', icon: Buildings, iconBg: 'bg-slate-100', iconColor: 'text-slate-600' },
  { key: 'shortlist', label: 'В шортлисте', icon: ListChecks, iconBg: 'bg-green-100', iconColor: 'text-green-600' },
  { key: 'hidden', label: 'Скрытых талантов', icon: Star, iconBg: 'bg-purple-100', iconColor: 'text-purple-600' },
  { key: 'score', label: 'Средний ML Score', icon: TrendUp, iconBg: 'bg-blue-100', iconColor: 'text-blue-600' },
]

const KPI_COLORS = {
  producers: 'text-slate-900',
  shortlist: 'text-green-600',
  hidden: 'text-purple-600',
  score: 'text-blue-600',
}

export default function DashboardPage() {
  const { showToast } = useToast()
  const [selectedId, setSelectedId] = useState(null)
  const [regionFilter, setRegionFilter] = useState('')
  const [dirFilter, setDirFilter] = useState('')
  const [hiddenOnly, setHiddenOnly] = useState(false)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    staleTime: 30_000,
    retry: 1,
  })
  const { data: shortlistData, isLoading: shortlistLoading, isError: shortlistError, refetch } = useShortlist(200)

  const allProducers = shortlistData?.shortlist ?? []
  const filtered = allProducers.filter(p => {
    if (regionFilter && p.region !== regionFilter) return false
    if (dirFilter && p.direction !== dirFilter) return false
    if (hiddenOnly && !p.hidden_talent) return false
    return true
  })

  const hiddenCount = shortlistData?.hidden_talent_count ?? allProducers.filter(p => p.hidden_talent).length
  const avgScore = allProducers.length
    ? (allProducers.reduce((s, p) => s + p.ml_score, 0) / allProducers.length * 100).toFixed(1)
    : null

  const regions = stats?.regions ? Object.keys(stats.regions).filter(Boolean).sort() : [...new Set(allProducers.map(p => p.region).filter(Boolean))].sort()
  const directions = stats?.directions ? Object.keys(stats.directions).filter(Boolean).sort() : [...new Set(allProducers.map(p => p.direction).filter(Boolean))].sort()
  const hasFilters = regionFilter || dirFilter || hiddenOnly
  const isLoading = statsLoading || shortlistLoading

  const kpiValues = {
    producers: stats ? stats.total_producers.toLocaleString() : '—',
    shortlist: allProducers.length || '—',
    hidden: hiddenCount || '—',
    score: avgScore ? avgScore + '%' : '—',
  }

  if (shortlistError) {
    return (
      <div className="space-y-5 max-w-full animate-fade-in">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-5 py-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Метрики модели</h2>
          <PipelineButton />
        </div>
        <ErrorState
          message="Сервер недоступен. Проверьте подключение к backend API."
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  return (
    <div className="space-y-5 max-w-full animate-fade-in">
      <AnimatePresence>
        {selectedId && <ProducerSidePanel producerId={selectedId} onClose={() => setSelectedId(null)} />}
      </AnimatePresence>

      {/* Header bar with metrics + pipeline */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-5 py-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Метрики модели</h2>
          <PipelineButton />
        </div>
        <MetricsStrip />
        <DriftBanner />
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {KPI_CONFIG.map((cfg) => {
          const Icon = cfg.icon
          return (
            <div key={cfg.key} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 hover:shadow-md transition-shadow duration-200">
              <div className="flex items-start justify-between mb-3">
                <p className="text-xs text-slate-500 font-medium">{cfg.label}</p>
                <div className={`w-8 h-8 rounded-lg ${cfg.iconBg} flex items-center justify-center flex-shrink-0`}>
                  <Icon size={15} className={cfg.iconColor} weight="bold" />
                </div>
              </div>
              {isLoading
                ? <Skeleton className="h-8 w-20 mt-1" />
                : <div className={`text-2xl font-extrabold tracking-tight ${KPI_COLORS[cfg.key]}`}>{kpiValues[cfg.key]}</div>
              }
            </div>
          )
        })}
      </div>

      {/* Table card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Toolbar */}
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-2 flex-wrap bg-white">
          <span className="text-sm font-semibold text-slate-800 mr-1">
            {filtered.length < allProducers.length ? `${filtered.length} из ${allProducers.length}` : `${allProducers.length}`} производителей
          </span>

          <div className="flex items-center gap-2 flex-wrap flex-1">
            <select
              value={regionFilter}
              onChange={e => setRegionFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-md px-2.5 py-1.5 text-slate-700 bg-white hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            >
              <option value="">Все регионы</option>
              {regions.map(r => <option key={r} value={r}>{r}</option>)}
            </select>

            <select
              value={dirFilter}
              onChange={e => setDirFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-md px-2.5 py-1.5 text-slate-700 bg-white hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            >
              <option value="">Все направления</option>
              {directions.map(d => <option key={d} value={d}>{d}</option>)}
            </select>

            <label className="inline-flex items-center gap-2 cursor-pointer text-xs text-slate-600 select-none">
              <div
                onClick={() => setHiddenOnly(v => !v)}
                className={`w-8 rounded-full transition-colors duration-200 flex items-center px-0.5 cursor-pointer ${hiddenOnly ? 'bg-purple-500' : 'bg-slate-200'}`}
                style={{ height: '18px' }}
              >
                <div className={`w-3.5 h-3.5 bg-white rounded-full shadow-sm transition-transform duration-200 ${hiddenOnly ? 'translate-x-3.5' : 'translate-x-0'}`} />
              </div>
              Скрытые таланты
            </label>

            {hasFilters && (
              <button
                onClick={() => { setRegionFilter(''); setDirFilter(''); setHiddenOnly(false) }}
                className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 font-medium px-2 py-1 rounded-md hover:bg-slate-100 transition-colors"
              >
                <X size={11} /> Сбросить
              </button>
            )}
          </div>

          <button
            onClick={() => { downloadCSV(filtered); showToast({ message: 'Экспорт завершён', type: 'success' }) }}
            className="inline-flex items-center gap-1.5 text-xs bg-white border border-slate-200 text-slate-600 px-3 py-1.5 rounded-lg hover:bg-slate-50 hover:border-slate-300 transition-all duration-150 ml-auto"
          >
            <DownloadSimple size={13} /> CSV
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                {[
                  { label: '#', w: 'w-10' },
                  { label: 'Производитель', w: 'w-36' },
                  { label: 'Регион', w: '' },
                  { label: 'Направление', w: '' },
                  { label: 'ML Score', w: 'w-24' },
                  { label: 'FCFS Ранг', w: 'w-24' },
                  { label: 'Delta ↕', w: 'w-20', title: 'FCFS ранг − ML ранг. Положительное = ML оценивает выше FCFS' },
                  { label: 'Статус', w: 'w-28' },
                ].map(({ label, w, title }) => (
                  <th key={label} title={title} className={`text-left px-4 py-2.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider ${w} ${title ? 'cursor-help' : ''}`}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            {shortlistLoading
              ? <Skeleton variant="table" rows={8} />
              : (
                <tbody className="divide-y divide-slate-100">
                  {filtered.length === 0
                    ? (
                      <tr>
                        <td colSpan={8} className="px-4 py-14 text-center">
                          <p className="text-slate-400 text-sm">Нет данных по выбранным фильтрам</p>
                        </td>
                      </tr>
                    )
                    : filtered.map((p, i) => (
                      <tr
                        key={p.producer_id}
                        onClick={() => setSelectedId(p.producer_id)}
                        className="hover:bg-blue-50/40 transition-colors duration-100 cursor-pointer"
                      >
                        <td className="px-4 py-3.5 text-slate-300 text-xs tabular-nums">{i + 1}</td>
                        <td className="px-4 py-3.5 font-mono text-xs text-slate-800 font-semibold">{p.producer_id}</td>
                        <td className="px-4 py-3.5 text-slate-500 text-xs">{p.region || '—'}</td>
                        <td className="px-4 py-3.5 text-slate-500 text-xs">{p.direction || '—'}</td>
                        <td className="px-4 py-3.5">
                          <Badge variant={getScoreVariant(p.ml_score)}>{(p.ml_score * 100).toFixed(1)}%</Badge>
                        </td>
                        <td className="px-4 py-3.5 text-slate-400 text-xs tabular-nums">#{p.fcfs_rank}</td>
                        <td className="px-4 py-3.5"><DeltaCell delta={p.delta} /></td>
                        <td className="px-4 py-3.5">
                          {p.hidden_talent
                            ? <Badge variant="hidden_talent" />
                            : p.delta < -10
                              ? <Badge variant="at_risk">↓ Переоценён</Badge>
                              : p.ml_rank <= 20
                                ? <Badge variant="shortlisted">✓ Шортлист</Badge>
                                : null
                          }
                        </td>
                      </tr>
                    ))
                  }
                </tbody>
              )
            }
          </table>
        </div>
      </div>
    </div>
  )
}
