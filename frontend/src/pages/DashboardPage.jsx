import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AnimatePresence } from 'framer-motion'
import { DownloadSimple } from '@phosphor-icons/react'
import { getStats } from '../services/api'
import { useShortlist } from '../hooks/useShortlist'
import { Badge, getScoreVariant } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import { useToast } from '../components/ui/Toast'
import { ProducerSidePanel } from '../components/features/ProducerSidePanel'

function DeltaCell({ delta }) {
  if (delta > 0) return <span className="text-green-600 font-semibold text-xs">↑ +{delta}</span>
  if (delta < 0) return <span className="text-red-600 font-semibold text-xs">↓ {delta}</span>
  return <span className="text-slate-400 text-xs">—</span>
}

function downloadCSV(data) {
  const h = ['ID', 'Регион', 'Направление', 'ML Score', 'ML Ранг', 'FCFS Ранг', 'Delta', 'Скрытый талант']
  const rows = data.map(p => [p.producer_id, p.region, p.direction, (p.ml_score * 100).toFixed(1) + '%', p.ml_rank, p.fcfs_rank, p.delta, p.hidden_talent ? 'Да' : 'Нет'])
  const csv = [h, ...rows].map(r => r.join(',')).join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'shortlist.csv'
  a.click()
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
  const hiddenCount = allProducers.filter(p => p.hidden_talent).length
  const avgScore = allProducers.length
    ? (allProducers.reduce((s, p) => s + p.ml_score, 0) / allProducers.length * 100).toFixed(1)
    : null
  const regions = [...new Set(allProducers.map(p => p.region))].sort()
  const directions = [...new Set(allProducers.map(p => p.direction))].sort()
  const hasFilters = regionFilter || dirFilter || hiddenOnly
  const isLoading = statsLoading || shortlistLoading

  const kpi = [
    { label: 'Производителей',   value: stats ? stats.total_producers.toLocaleString() : '—', color: 'text-slate-900', icon: '🏭' },
    { label: 'В шортлисте',      value: allProducers.length || '—', color: 'text-green-600', icon: '✅' },
    { label: 'Скрытых талантов', value: hiddenCount || '—', color: 'text-purple-600', icon: '★' },
    { label: 'Средний ML Score', value: avgScore ? avgScore + '%' : '—', color: 'text-blue-600', icon: '📈' },
  ]

  return (
    <div className="space-y-6">
      <AnimatePresence>
        {selectedId && (
          <ProducerSidePanel producerId={selectedId} onClose={() => setSelectedId(null)} />
        )}
      </AnimatePresence>

      <div className="grid grid-cols-4 gap-4">
        {kpi.map(c => (
          <div key={c.label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">{c.label}</span>
              <span className="text-lg">{c.icon}</span>
            </div>
            {isLoading
              ? <Skeleton className="h-8 w-24 mt-1" />
              : <div className={`text-3xl font-bold ${c.color}`}>{c.value}</div>
            }
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-3 flex-wrap">
          <h2 className="text-sm font-semibold text-slate-700 mr-2">Топ-20 производителей</h2>

          <select value={regionFilter} onChange={e => setRegionFilter(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-3 py-1.5 text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">Все регионы</option>
            {regions.map(r => <option key={r} value={r}>{r}</option>)}
          </select>

          <select value={dirFilter} onChange={e => setDirFilter(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-3 py-1.5 text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">Все направления</option>
            {directions.map(d => <option key={d} value={d}>{d}</option>)}
          </select>

          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-600">
            <input type="checkbox" checked={hiddenOnly} onChange={e => setHiddenOnly(e.target.checked)}
              className="accent-purple-600 w-3.5 h-3.5" />
            Только скрытые таланты
          </label>

          {hasFilters && (
            <button
              onClick={() => { setRegionFilter(''); setDirFilter(''); setHiddenOnly(false) }}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium">
              × Сбросить
            </button>
          )}

          <div className="ml-auto">
            <button
              onClick={() => { downloadCSV(filtered); showToast({ message: 'Экспорт завершён', type: 'success' }) }}
              className="flex items-center gap-1.5 text-xs bg-white border border-slate-200 text-slate-600 px-3 py-1.5 rounded-lg hover:bg-slate-50 transition-colors">
              <DownloadSimple size={13} /> Экспорт CSV
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                {['#', 'ID производителя', 'Регион', 'Направление', 'ML Score', 'FCFS Ранг', 'Delta', ''].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            {shortlistLoading
              ? <Skeleton variant="table" rows={8} />
              : <tbody>
                  {filtered.length === 0
                    ? <tr><td colSpan={8} className="px-4 py-12 text-center text-slate-400 text-sm">Нет данных по фильтрам</td></tr>
                    : filtered.map((p, i) => (
                        <tr key={p.producer_id} onClick={() => setSelectedId(p.producer_id)}
                          className="border-b border-slate-100 hover:bg-blue-50/50 transition-colors cursor-pointer">
                          <td className="px-4 py-3 text-slate-400 text-xs">{i + 1}</td>
                          <td className="px-4 py-3 font-mono text-xs text-slate-700">{p.producer_id}</td>
                          <td className="px-4 py-3 text-slate-600 text-xs">{p.region || '—'}</td>
                          <td className="px-4 py-3 text-slate-600 text-xs">{p.direction || '—'}</td>
                          <td className="px-4 py-3">
                            <Badge variant={getScoreVariant(p.ml_score)}>{(p.ml_score * 100).toFixed(1)}%</Badge>
                          </td>
                          <td className="px-4 py-3 text-slate-600 text-xs">#{p.fcfs_rank}</td>
                          <td className="px-4 py-3"><DeltaCell delta={p.delta} /></td>
                          <td className="px-4 py-3">{p.hidden_talent && <Badge variant="hidden_talent" />}</td>
                        </tr>
                      ))
                  }
                </tbody>
            }
          </table>
        </div>
      </div>
    </div>
  )
}
