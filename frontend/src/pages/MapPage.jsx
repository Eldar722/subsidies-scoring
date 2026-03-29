import { useFairness } from '../hooks/useFairness'
import { Badge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'

function successVariant(rate) {
  if (rate >= 0.6) return 'success'
  if (rate >= 0.4) return 'warning'
  return 'error'
}

export default function MapPage() {
  const { data: fairness, isLoading } = useFairness()
  const regions = fairness?.regions ?? []

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Карта регионов</h1>

      {/* Map placeholder */}
      <div className="bg-slate-100 rounded-xl p-10 text-center text-slate-500 mb-6">
        <div className="text-4xl mb-3">🗺️</div>
        <p className="text-sm font-medium">Интерактивная карта будет добавлена в следующей итерации</p>
        <p className="text-xs text-slate-400 mt-1">React-Leaflet хороплет по регионам Казахстана</p>
      </div>

      {/* Regions Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Распределение по регионам</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Регион</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Заявок</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Успешность</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Ср. сумма (тг)</th>
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i} className="border-b border-slate-100">
                      {Array.from({ length: 4 }).map((_, j) => (
                        <td key={j} className="px-4 py-3"><Skeleton className="h-4 w-full" /></td>
                      ))}
                    </tr>
                  ))
                : regions
                    .slice()
                    .sort((a, b) => b.total_apps - a.total_apps)
                    .map(region => (
                      <tr key={region['Область']} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 text-slate-700 text-sm font-medium">{region['Область']}</td>
                        <td className="px-4 py-3 text-slate-600 text-sm">{region.total_apps?.toLocaleString()}</td>
                        <td className="px-4 py-3">
                          <Badge variant={successVariant(region.success_rate)}>
                            {(region.success_rate * 100).toFixed(1)}%
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-slate-600 text-sm">
                          {region.avg_amount ? region.avg_amount.toLocaleString('ru-RU', { maximumFractionDigits: 0 }) : '—'}
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
