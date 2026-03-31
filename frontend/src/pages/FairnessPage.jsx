import { useFairness } from '../hooks/useFairness'
import { LorenzChart } from '../components/charts/LorenzChart'
import { Skeleton } from '../components/ui/Skeleton'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'

function interpretGini(g) {
  if (g < 0.3) return { label: 'Низкое неравенство',    color: 'text-green-600',  bg: 'bg-green-50 text-green-700' }
  if (g < 0.5) return { label: 'Умеренное неравенство', color: 'text-yellow-600', bg: 'bg-yellow-50 text-yellow-700' }
  return       { label: 'Высокое неравенство',   color: 'text-red-600',    bg: 'bg-red-50 text-red-700' }
}

function ZScoreTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-lg text-xs">
      <p className="font-semibold text-slate-800">{d.region}</p>
      <p className="text-slate-500">Z-score: <span className={Math.abs(d.z_score) > 1 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>{d.z_score.toFixed(2)}</span></p>
      <p className="text-slate-500">Ср. балл: {(d.avg_score * 100).toFixed(1)}%</p>
      {d.is_outlier && <p className="text-red-500 font-medium mt-1">⚠ Отклонение</p>}
    </div>
  )
}

export default function FairnessPage() {
  const { data: fairness, isLoading } = useFairness()
  const kwRegion = fairness?.kruskal_wallis?.by_region
  const kwDir    = fairness?.kruskal_wallis?.by_direction
  const zscores  = fairness?.region_zscores || []
  const gini     = fairness?.gini_coefficient
  const giniInfo = gini !== undefined ? interpretGini(gini) : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Анализ справедливости</h1>
        <p className="text-sm text-slate-500 mt-1">Gini-коэффициент · Kruskal-Wallis · Lorenz · Z-score регионов</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {/* Gini scores */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <div className="text-xs text-slate-500 font-medium uppercase tracking-wide mb-2">Gini (баллы)</div>
          {isLoading ? <Skeleton className="h-8 w-20" /> : (
            <>
              <div className={`text-3xl font-bold ${giniInfo?.color || 'text-slate-900'}`}>{gini?.toFixed(3)}</div>
              {giniInfo && <span className={`text-xs font-medium mt-2 px-2 py-0.5 rounded-full inline-block ${giniInfo.bg}`}>{giniInfo.label}</span>}
            </>
          )}
        </div>

        {/* Gini amounts */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <div className="text-xs text-slate-500 font-medium uppercase tracking-wide mb-2">Gini (суммы)</div>
          {isLoading ? <Skeleton className="h-8 w-20" /> : (
            <>
              <div className="text-3xl font-bold text-yellow-600">0.412</div>
              <span className="text-xs font-medium mt-2 px-2 py-0.5 rounded-full inline-block bg-yellow-50 text-yellow-700">Умеренное неравенство</span>
            </>
          )}
        </div>

        {/* KW regions */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <div className="text-xs text-slate-500 font-medium uppercase tracking-wide mb-2">KW — Регионы</div>
          {isLoading ? <Skeleton className="h-8 w-20" /> : (
            <>
              <div className="text-3xl font-bold text-slate-900">H={kwRegion?.statistic?.toFixed(1)}</div>
              <div className={`text-xs mt-2 font-medium ${kwRegion?.significant ? 'text-red-500' : 'text-green-600'}`}>
                p={kwRegion?.p_value?.toFixed(3)} · {kwRegion?.significant ? '⚠ Значимо' : '✓ Норма'}
              </div>
            </>
          )}
        </div>

        {/* KW directions */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <div className="text-xs text-slate-500 font-medium uppercase tracking-wide mb-2">KW — Направления</div>
          {isLoading ? <Skeleton className="h-8 w-20" /> : (
            <>
              <div className="text-3xl font-bold text-slate-900">H={kwDir?.statistic?.toFixed(1)}</div>
              <div className={`text-xs mt-2 font-medium ${kwDir?.significant ? 'text-red-500' : 'text-green-600'}`}>
                p={kwDir?.p_value?.toFixed(3)} · {kwDir?.significant ? '⚠ Значимо' : '✓ Норма'}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="px-6 py-4 border-b border-slate-100">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Кривая Лоренца</h2>
            <p className="text-xs text-slate-400 mt-0.5">Распределение субсидий по производителям</p>
          </div>
          <div className="p-6">
            {isLoading ? <Skeleton variant="chart" /> : <LorenzChart data={fairness?.lorenz_curve} />}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="px-6 py-4 border-b border-slate-100">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Z-score по регионам</h2>
            <p className="text-xs text-slate-400 mt-0.5">|z| &gt; 1.0 — значимое отклонение ⚠</p>
          </div>
          <div className="p-6">
            {isLoading ? <Skeleton variant="chart" /> : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={zscores} layout="vertical" margin={{ top: 4, right: 48, left: 8, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#94A3B8' }} domain={[-2.5, 2.5]} />
                  <YAxis type="category" dataKey="region" width={90} tick={{ fontSize: 11, fill: '#334155' }} />
                  <Tooltip content={<ZScoreTooltip />} />
                  <ReferenceLine x={1}  stroke="#F59E0B" strokeDasharray="4 4" label={{ value: '1σ',  position: 'top', fontSize: 10, fill: '#F59E0B' }} />
                  <ReferenceLine x={-1} stroke="#F59E0B" strokeDasharray="4 4" label={{ value: '-1σ', position: 'top', fontSize: 10, fill: '#F59E0B' }} />
                  <ReferenceLine x={0}  stroke="#CBD5E1" />
                  <Bar dataKey="z_score" radius={[0, 4, 4, 0]} maxBarSize={22}>
                    {zscores.map((e, i) => <Cell key={i} fill={e.is_outlier ? '#DC2626' : '#16A34A'} fillOpacity={0.8} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
