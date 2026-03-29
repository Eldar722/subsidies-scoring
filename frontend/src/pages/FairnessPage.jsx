import { useFairness } from '../hooks/useFairness'
import { LorenzChart } from '../components/charts/LorenzChart'
import { Skeleton } from '../components/ui/Skeleton'

export default function FairnessPage() {
  const { data: fairness, isLoading } = useFairness()

  const kw = fairness?.kruskal_wallis?.by_region

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Анализ справедливости</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="text-xs text-slate-500 font-medium uppercase tracking-wide mb-2">Коэффициент Джини</div>
          {isLoading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <>
              <div className="text-3xl font-bold text-slate-900">{fairness?.gini_coefficient?.toFixed(4)}</div>
              <div className="text-xs text-slate-500 mt-1">{fairness?.gini_interpretation}</div>
            </>
          )}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="text-xs text-slate-500 font-medium uppercase tracking-wide mb-2">Kruskal-Wallis (регионы)</div>
          {isLoading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <>
              <div className="text-3xl font-bold text-slate-900">
                {kw?.statistic?.toFixed(2)}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                p-value: {kw?.p_value?.toFixed(6)} · {kw?.significant ? '⚠ Различия значимы' : '✓ Различия незначимы'}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Lorenz Curve */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">Кривая Лоренца — распределение субсидий по регионам</h2>
        {isLoading
          ? <Skeleton className="h-80 w-full" />
          : <LorenzChart data={fairness?.lorenz_curve} />
        }
      </div>
    </div>
  )
}
