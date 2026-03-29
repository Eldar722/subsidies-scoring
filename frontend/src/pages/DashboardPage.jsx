import { useQuery } from '@tanstack/react-query'
import { getStats } from '../services/api'
import { useShortlist } from '../hooks/useShortlist'
import { Badge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'

function mlScoreVariant(score) {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'error'
}

function DeltaCell({ delta }) {
  if (delta > 0.001) return <span className="text-green-600 font-semibold">↑ +{delta.toFixed(3)}</span>
  if (delta < -0.001) return <span className="text-red-600 font-semibold">↓ {delta.toFixed(3)}</span>
  return <span className="text-slate-400">—</span>
}

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    staleTime: 30_000,
  })
  const { data: shortlistData, isLoading: shortlistLoading } = useShortlist(20)

  const isLoading = statsLoading || shortlistLoading
  const shortlist = shortlistData?.shortlist ?? []
  const hiddenCount = shortlist.filter(p => p.hidden_talent).length
  const avgScore = shortlist.length
    ? (shortlist.reduce((s, p) => s + p.ml_score, 0) / shortlist.length * 100).toFixed(1)
    : null

  const kpiCards = [
    { label: 'Производителей', value: stats ? stats.total_producers.toLocaleString() : '—', color: 'text-slate-900', icon: '🏭' },
    { label: 'В шортлисте', value: shortlist.length || '—', color: 'text-green-600', icon: '✅' },
    { label: 'Скрытых талантов', value: hiddenCount || '—', color: 'text-purple-600', icon: '★' },
    { label: 'Средний ML score', value: avgScore ? `${avgScore}%` : '—', color: 'text-blue-600', icon: '🎯' },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Дашборд</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {kpiCards.map(card => (
          <div key={card.label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">{card.label}</span>
              <span className="text-lg">{card.icon}</span>
            </div>
            {isLoading
              ? <Skeleton className="h-8 w-24 mt-1" />
              : <div className={`text-3xl font-bold ${card.color}`}>{card.value}</div>
            }
          </div>
        ))}
      </div>

      {/* Producer Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Топ-20 производителей</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide w-10">#</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">ID производителя</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Регион</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Направление</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">ML Score</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Delta</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide"></th>
              </tr>
            </thead>
            <tbody>
              {shortlistLoading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} className="border-b border-slate-100">
                      {Array.from({ length: 7 }).map((_, j) => (
                        <td key={j} className="px-4 py-3"><Skeleton className="h-4 w-full" /></td>
                      ))}
                    </tr>
                  ))
                : shortlist.map((producer, idx) => (
                    <tr
                      key={producer.producer_id}
                      className="border-b border-slate-100 hover:bg-blue-50/50 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3 text-slate-400 text-xs">{idx + 1}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-700">{producer.producer_id}</td>
                      <td className="px-4 py-3 text-slate-600 text-xs">{producer.region || '—'}</td>
                      <td className="px-4 py-3 text-slate-600 text-xs">{producer.direction || '—'}</td>
                      <td className="px-4 py-3">
                        <Badge variant={mlScoreVariant(producer.ml_score)}>
                          {(producer.ml_score * 100).toFixed(1)}%
                        </Badge>
                      </td>
                      <td className="px-4 py-3"><DeltaCell delta={producer.delta} /></td>
                      <td className="px-4 py-3">
                        {producer.hidden_talent && <Badge variant="hidden">★ Скрытый талант</Badge>}
                      </td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
