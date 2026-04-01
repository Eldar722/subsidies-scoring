import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AnimatePresence } from 'framer-motion'
import { DownloadSimple, Buildings, ListChecks, Star, TrendUp, X } from '@phosphor-icons/react'
import { getStats } from '../services/api'
import { useShortlist } from '../hooks/useShortlist'
import { Badge, getScoreVariant } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import { useToast } from '../components/ui/Toast'
import { ProducerSidePanel } from '../components/features/ProducerSidePanel'

function DeltaCell({ delta }) {
  if (delta > 0) return (
    <span title={`Недооценён FCFS на ${delta} позиций`} className="inline-flex items-center gap-1 text-green-700 font-semibold text-xs bg-green-50 border border-green-100 px-2 py-0.5 rounded-full">
      ↑ +{delta}
    </span>
  )
  if (delta < 0) return (
    <span title={`Переоценён FCFS на ${Math.abs(delta)} позиций`} className="inline-flex items-center gap-1 text-red-600 font-semibold text-xs bg-red-50 border border-red-100 px-2 py-0.5 rounded-full">
      ↓ {delta}
    </span>
  )
  return <span className="text-slate-300 text-xs font-medium">—</span>
}

function downloadCSV(data) {
  const h = ['ID', 'Регион', 'Направление', 'ML Score', 'ML Ранг', 'FCFS Ранг', 'Delta', 'Скрытый талант']
  const rows = data.map(p => [
    p.producer_id, p.region, p.direction,
    (p.ml_score * 100).toFixed(1) + '%',
    p.ml_rank, p.fcfs_rank, p.delta,
    p.hidden_talent ? 'Да' : 'Нет',
  ])
  const csv = [h, ...rows].map(r => r.join(',')).join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'shortlist.csv'
  a.click()
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

  const { data: stats, isLoading: statsLoading } = useQuery({ queryKey: ['stats'], queryFn: getStats, staleTime: 30_000 })
  const { data: shortlistData, isLoading: shortlistLoading } = useShortlist(20)

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

  const regions = [...new Set(allProducers.map(p => p.region))].sort()
  const directions = [...new Set(allProducers.map(p => p.direction))].sort()
  const hasFilters = regionFilter || dirFilter || hiddenOnly
  const isLoading = statsLoading || shortlistLoading

  const kpiValues = {
    producers: stats ? stats.total_producers.toLocaleString() : '—',
    shortlist: allProducers.length || '—',
    hidden: (hiddenCount ?? 0) || '—',
    score: avgScore ? avgScore + '%' : '—',
  }

  return (
    <div className="space-y-5 max-w-full">
      <AnimatePresence>
        {selectedId && <ProducerSidePanel producerId={selectedId} onClose={() => setSelectedId(null)} />}
      </AnimatePresence>

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
                : <div className={`text-2xl font-bold ${KPI_COLORS[cfg.key]}`}>{kpiValues[cfg.key]}</div>
              }
            </div>
          )
        })}
      </div>

      {/* Table card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Toolbar */}
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-2 flex-wrap bg-white">
          <span className="text-sm font-semibold text-slate-800 mr-1">Топ-20</span>

          <div className="flex items-center gap-2 flex-wrap flex-1">
            <select
              value={regionFilter}
              onChange={e => setRegionFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-md px-2.5 py-1.5 text-slate-700 bg-white hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 transition-colors"
            >
              <option value="">Все регионы</option>
              {regions.map(r => <option key={r} value={r}>{r}</option>)}
            </select>

            <select
              value={dirFilter}
              onChange={e => setDirFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-md px-2.5 py-1.5 text-slate-700 bg-white hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 transition-colors"
            >
              <option value="">Все направления</option>
              {directions.map(d => <option key={d} value={d}>{d}</option>)}
            </select>

            <label className="inline-flex items-center gap-2 cursor-pointer text-xs text-slate-600 select-none">
              <div
                onClick={() => setHiddenOnly(v => !v)}
                className={`w-8 h-4.5 rounded-full transition-colors duration-200 flex items-center px-0.5 cursor-pointer ${hiddenOnly ? 'bg-purple-500' : 'bg-slate-200'}`}
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
                  { label: 'ID производителя', w: 'w-36' },
                  { label: 'Регион', w: '' },
                  { label: 'Направление', w: '' },
                  { label: 'ML Score', w: 'w-24' },
                  { label: 'FCFS Ранг', w: 'w-24' },
                  { label: 'Delta', w: 'w-20' },
                  { label: '', w: 'w-12' },
                ].map(({ label, w }) => (
                  <th key={label} className={`text-left px-4 py-2.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider ${w}`}>
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
                        <td className="px-4 py-3.5 text-right">
                          {p.hidden_talent && <Badge variant="hidden_talent" />}
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
