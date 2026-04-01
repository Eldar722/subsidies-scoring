import { useFairness } from '../hooks/useFairness'
import { LorenzChart } from '../components/charts/LorenzChart'
import { Skeleton } from '../components/ui/Skeleton'
import { CardHeader } from '../components/ui/Card'
import { Scales, ChartBar, GitBranch, Polygon } from '@phosphor-icons/react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'

function interpretGini(g) {
  if (g < 0.3) return { label: 'Низкое неравенство',    color: 'text-green-600',  bg: 'bg-green-50 text-green-700 border border-green-100' }
  if (g < 0.5) return { label: 'Умеренное неравенство', color: 'text-amber-600',  bg: 'bg-amber-50 text-amber-700 border border-amber-100' }
  return       { label: 'Высокое неравенство',           color: 'text-red-600',    bg: 'bg-red-50 text-red-700 border border-red-100' }
}

function ZScoreTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-md text-xs">
      <p className="font-semibold text-slate-800 mb-1">{d.region}</p>
      <p className="text-slate-500">
        Z-score:{' '}
        <span className={Math.abs(d.z_score) > 1 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
          {d.z_score.toFixed(2)}
        </span>
      </p>
      <p className="text-slate-400 mt-0.5">Ср. балл: {(d.avg_score * 100).toFixed(1)}%</p>
      {d.is_outlier && <p className="text-red-500 font-medium mt-1.5 flex items-center gap-1">⚠ Отклонение</p>}
    </div>
  )
}

function MetricCard({ icon, iconBg, iconColor, label, isLoading, children }) {
  const Icon = icon
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs text-slate-500 font-medium">{label}</p>
        <div className={`w-8 h-8 rounded-lg ${iconBg} flex items-center justify-center flex-shrink-0`}>
          <Icon size={15} className={iconColor} weight="bold" />
        </div>
      </div>
      {isLoading ? <Skeleton className="h-8 w-20" /> : children}
    </div>
  )
}

export default function FairnessPage() {
  const { data: fairness, isLoading } = useFairness()
  const kwRegion = fairness?.kruskal_wallis?.by_region
  const kwDir    = fairness?.kruskal_wallis?.by_direction
  const zscores  = fairness?.region_zscores || []
  const gini     = fairness?.gini_coefficient
  const giniAmt  = fairness?.gini_coefficient_amounts
  const giniInfo = gini !== undefined ? interpretGini(gini) : null
  const giniAmtInfo = giniAmt !== undefined ? interpretGini(giniAmt) : null

  const chartH = Math.max(240, zscores.length * 26)

  return (
    <div className="space-y-5 max-w-full">
      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={Scales}    iconBg="bg-blue-100"  iconColor="text-blue-600"  label="Gini (баллы)"     isLoading={isLoading}>
          <div className={`text-2xl font-bold ${giniInfo?.color || 'text-slate-900'}`}>{gini?.toFixed(3) ?? '—'}</div>
          {giniInfo && <span className={`text-xs font-medium mt-2 px-2 py-0.5 rounded-full inline-block ${giniInfo.bg}`}>{giniInfo.label}</span>}
        </MetricCard>

        <MetricCard icon={Polygon}   iconBg="bg-amber-100" iconColor="text-amber-600" label="Gini (суммы)"     isLoading={isLoading}>
          <div className={`text-2xl font-bold ${giniAmtInfo?.color || 'text-slate-900'}`}>{giniAmt?.toFixed(3) ?? '—'}</div>
          {giniAmtInfo && <span className={`text-xs font-medium mt-2 px-2 py-0.5 rounded-full inline-block ${giniAmtInfo.bg}`}>{giniAmtInfo.label}</span>}
        </MetricCard>

        <MetricCard icon={ChartBar}  iconBg="bg-slate-100" iconColor="text-slate-600" label="KW — Регионы"     isLoading={isLoading}>
          <div className="text-2xl font-bold text-slate-900">H={kwRegion?.statistic?.toFixed(1) ?? '—'}</div>
          <div className={`text-xs mt-2 font-medium ${kwRegion?.significant ? 'text-red-500' : 'text-green-600'}`}>
            p={kwRegion?.p_value?.toFixed(3) ?? '—'} · {kwRegion?.significant ? '⚠ Различия значимы' : '✓ Однородные группы'}
          </div>
        </MetricCard>

        <MetricCard icon={GitBranch} iconBg="bg-purple-100" iconColor="text-purple-600" label="KW — Направления" isLoading={isLoading}>
          <div className="text-2xl font-bold text-slate-900">H={kwDir?.statistic?.toFixed(1) ?? '—'}</div>
          <div className={`text-xs mt-2 font-medium ${kwDir?.significant ? 'text-red-500' : 'text-green-600'}`}>
            p={kwDir?.p_value?.toFixed(3) ?? '—'} · {kwDir?.significant ? '⚠ Различия значимы' : '✓ Однородные группы'}
          </div>
        </MetricCard>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Lorenz */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <CardHeader
            title="Кривая Лоренца"
            subtitle="Распределение субсидий по производителям"
          />
          <div className="p-5">
            {isLoading ? <Skeleton variant="chart" /> : <LorenzChart data={fairness?.lorenz_curve} />}
          </div>
        </div>

        {/* Z-scores */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <CardHeader
            title="Z-score по регионам"
            subtitle="|z| > 1.0 — значимое отклонение от среднего"
          />
          <div className="p-5 overflow-x-auto">
            {isLoading ? <Skeleton variant="chart" /> : (
              zscores.length === 0
                ? <p className="text-slate-400 text-sm text-center py-8">Нет данных по регионам</p>
                : (
                  <div style={{ height: chartH }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={zscores} layout="vertical" margin={{ top: 4, right: 52, left: 4, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                        <XAxis type="number" tick={{ fontSize: 10, fill: '#94A3B8' }} domain={[-3, 3]} />
                        <YAxis type="category" dataKey="region" width={96} tick={{ fontSize: 11, fill: '#475569' }} />
                        <Tooltip content={<ZScoreTooltip />} />
                        <ReferenceLine x={1}  stroke="#F59E0B" strokeDasharray="4 4" label={{ value: '+1σ', position: 'insideTopRight', fontSize: 9, fill: '#D97706' }} />
                        <ReferenceLine x={-1} stroke="#F59E0B" strokeDasharray="4 4" label={{ value: '-1σ', position: 'insideBottomRight', fontSize: 9, fill: '#D97706' }} />
                        <ReferenceLine x={0}  stroke="#E2E8F0" />
                        <Bar dataKey="z_score" radius={[0, 4, 4, 0]} maxBarSize={20}>
                          {zscores.map((e, i) => (
                            <Cell key={i} fill={e.is_outlier ? '#DC2626' : '#16A34A'} fillOpacity={0.85} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
