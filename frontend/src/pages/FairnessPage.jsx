import { useFairness } from '../hooks/useFairness'
import { LorenzChart } from '../components/charts/LorenzChart'
import { Skeleton } from '../components/ui/Skeleton'
import { CardHeader } from '../components/ui/Card'
import { Scales, ChartBar, GitBranch, Polygon, MapPin, Table, Warning, Lightbulb, Info } from '@phosphor-icons/react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine,
} from 'recharts'

function interpretGini(g) {
  if (g < 0.3) return { label: 'Низкое', color: 'text-green-600', bg: 'bg-green-50 text-green-700 border border-green-100' }
  if (g < 0.5) return { label: 'Умеренное', color: 'text-amber-600', bg: 'bg-amber-50 text-amber-700 border border-amber-100' }
  return { label: 'Высокое', color: 'text-red-600', bg: 'bg-red-50 text-red-700 border border-red-100' }
}

function ZScoreTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const absZ = Math.abs(d.z_score || 0)
  const severity = absZ > 2 ? 'КРИТИЧЕСКОЕ' : absZ > 1.5 ? 'Сильное' : absZ > 1 ? 'Умеренное' : 'В норме'
  const severityColor = absZ > 2 ? 'text-red-700' : absZ > 1.5 ? 'text-red-600' : absZ > 1 ? 'text-amber-600' : 'text-green-600'
  const advice = absZ > 2
    ? 'Рекомендуется: пересмотреть критерии оценки в регионе, проверить качество данных'
    : absZ > 1.5
      ? 'Рекомендуется: проанализировать региональные особенности'
      : absZ > 1
        ? 'Рекомендуется: мониторинг в следующем периоде'
        : 'Регион работает в пределах нормы'

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-md text-xs max-w-[260px]">
      <p className="font-semibold text-slate-800 mb-1">{d.region}</p>
      <p className="text-slate-500 mb-1">
        Z-score:{' '}
        <span className={Math.abs(d.z_score) > 1 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
          {d.z_score?.toFixed(2)}
        </span>
        <span className={`ml-2 font-semibold ${severityColor}`}>({severity})</span>
      </p>
      <p className="text-slate-400">Ср. балл: {((d.avg_score || 0) * 100).toFixed(1)}%</p>
      <div className="mt-2 pt-2 border-t border-slate-100">
        <p className="text-[10px] text-slate-500 leading-relaxed">{advice}</p>
      </div>
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

// ── Direction short names for heatmap ──
function shortDir(dir) {
  if (!dir) return dir
  const l = dir.toLowerCase()
  if (l.includes('верблюдовод')) return 'Верблюдовод.'
  if (l.includes('козовод'))     return 'Козовод.'
  if (l.includes('коневод'))     return 'Коневод.'
  if (l.includes('овцевод'))     return 'Овцевод.'
  if (l.includes('птицевод'))    return 'Птицевод.'
  if (l.includes('пчеловод'))    return 'Пчеловод.'
  if (l.includes('свиновод'))    return 'Свиновод.'
  if (l.includes('скотовод'))    return 'Скотовод.'
  if (l.includes('осемен'))      return 'Осеменение'
  // fallback — last word
  const words = dir.split(' ')
  const last = words[words.length - 1]
  return last.length > 10 ? last.slice(0, 10) + '…' : last
}

// ── Heatmap component ──
function HeatmapCell({ value, min, max }) {
  const norm = max === min ? 0.5 : (value - min) / (max - min)
  const r = Math.round(220 - norm * 180)
  const g = Math.round(60 + norm * 130)
  const b = Math.round(60 + norm * 20)
  return (
    <div
      className="flex items-center justify-center text-[10px] font-semibold text-white rounded-sm"
      style={{
        background: `rgba(${r},${g},${b},0.85)`,
        minHeight: 28,
        minWidth: 52,
      }}
    >
      {(value * 100).toFixed(0)}%
    </div>
  )
}

function Heatmap({ data }) {
  if (!data || data.length === 0) return <p className="text-slate-400 text-sm text-center py-6">Нет данных</p>

  const regions = [...new Set(data.map(d => d.region))].sort()
  const directions = [...new Set(data.map(d => d.direction))].sort()
  const scores = data.map(d => d.avg_score)
  const minScore = Math.min(...scores)
  const maxScore = Math.max(...scores)

  const lookup = {}
  data.forEach(d => { lookup[`${d.region}__${d.direction}`] = d.avg_score })

  return (
    <div className="overflow-x-auto">
      <div style={{ minWidth: directions.length * 60 + 140 }}>
        {/* Header row */}
        <div className="flex mb-1">
          <div style={{ width: 140 }} className="flex-shrink-0" />
          {directions.map(dir => (
            <div key={dir} title={dir} style={{ minWidth: 60, flex: 1 }} className="text-[9px] text-slate-400 font-medium text-center px-0.5 leading-tight cursor-help">
              {shortDir(dir)}
            </div>
          ))}
        </div>
        {/* Data rows */}
        {regions.map(region => (
          <div key={region} className="flex items-center mb-0.5">
            <div style={{ width: 140 }} className="flex-shrink-0 text-[10px] text-slate-500 pr-2 text-right leading-tight truncate">
              {region}
            </div>
            {directions.map(dir => {
              const val = lookup[`${region}__${dir}`]
              return (
                <div key={dir} style={{ minWidth: 60, flex: 1 }} className="px-0.5">
                  {val !== undefined
                    ? <HeatmapCell value={val} min={minScore} max={maxScore} />
                    : <div className="rounded-sm bg-slate-50" style={{ minHeight: 28 }} />
                  }
                </div>
              )
            })}
          </div>
        ))}
      </div>
      {/* Legend */}
      <div className="flex items-center gap-3 mt-3 pl-36">
        <div className="h-2 flex-1 rounded-full" style={{
          background: 'linear-gradient(to right, rgba(220,60,60,0.85), rgba(80,190,80,0.85))'
        }} />
        <span className="text-[10px] text-slate-400 flex-shrink-0">{(minScore*100).toFixed(0)}% → {(maxScore*100).toFixed(0)}%</span>
      </div>
    </div>
  )
}

// ── Regional Stats Table ──
function RegionalTable({ data, isLoading }) {
  if (isLoading) return <Skeleton variant="table" rows={5} />
  if (!data || data.length === 0) return <p className="text-slate-400 text-sm text-center py-6">Нет данных</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-100">
            {['Регион', 'Заявок', 'Успешность', 'Ср. сумма', 'Итого'].map(h => (
              <th key={h} className="text-left px-3 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50">
          {data.sort((a, b) => b.total_apps - a.total_apps).map((row, i) => (
            <tr key={i} className="hover:bg-slate-50 transition-colors">
              <td className="px-3 py-2.5 text-slate-700 font-medium max-w-[160px] truncate">{row.region}</td>
              <td className="px-3 py-2.5 text-slate-500 tabular-nums">{row.total_apps?.toLocaleString()}</td>
              <td className="px-3 py-2.5 tabular-nums">
                <span className={`font-semibold ${row.success_rate > 0.7 ? 'text-green-600' : row.success_rate > 0.4 ? 'text-amber-600' : 'text-red-500'}`}>
                  {((row.success_rate || 0) * 100).toFixed(1)}%
                </span>
              </td>
              <td className="px-3 py-2.5 text-slate-500 tabular-nums">{Math.round(row.avg_amount || 0).toLocaleString()} ₸</td>
              <td className="px-3 py-2.5 text-slate-400 tabular-nums text-xs">{Math.round((row.total_amount || 0) / 1_000_000)}M ₸</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function FairnessPage() {
  const { data: fairness, isLoading } = useFairness()

  // Правильные ключи (после адаптации в backend)
  const kwRegion = fairness?.kruskal_wallis?.by_region
  const kwDir    = fairness?.kruskal_wallis?.by_direction
  const zscores  = fairness?.region_zscores || []
  const gini     = fairness?.gini_coefficient
  const giniAmt  = fairness?.gini_coefficient_amounts
  const heatmap  = fairness?.heatmap || []
  const regions  = fairness?.regional_stats || []

  const giniInfo    = gini !== undefined ? interpretGini(gini) : null
  const giniAmtInfo = giniAmt !== undefined ? interpretGini(giniAmt) : null

  const chartH = Math.max(260, zscores.length * 28)

  return (
    <div className="space-y-5 max-w-full animate-fade-in">
      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={Scales} iconBg="bg-blue-100" iconColor="text-blue-600" label="Gini  (баллы)" isLoading={isLoading}>
          <div className={`text-2xl font-bold ${giniInfo?.color || 'text-slate-900'}`}>{gini?.toFixed(3) ?? '—'}</div>
          {giniInfo && <span className={`text-xs font-medium mt-2 px-2 py-0.5 rounded-full inline-block ${giniInfo.bg}`}>{giniInfo.label} неравенство</span>}
          <p className="text-[10px] text-slate-400 mt-1.5 leading-snug">0 = равенство, 1 = монополия</p>
        </MetricCard>

        <MetricCard icon={Polygon} iconBg="bg-amber-100" iconColor="text-amber-600" label="Gini (суммы)" isLoading={isLoading}>
          <div className={`text-2xl font-bold ${giniAmtInfo?.color || 'text-slate-900'}`}>{giniAmt?.toFixed(3) ?? '—'}</div>
          {giniAmtInfo && <span className={`text-xs font-medium mt-2 px-2 py-0.5 rounded-full inline-block ${giniAmtInfo.bg}`}>{giniAmtInfo.label} неравенство</span>}
          <p className="text-[10px] text-slate-400 mt-1.5 leading-snug">Распределение сумм субсидий</p>
        </MetricCard>

        <MetricCard icon={ChartBar} iconBg="bg-slate-100" iconColor="text-slate-600" label="Kruskal-Wallis — Регионы" isLoading={isLoading}>
          <div className="text-2xl font-bold text-slate-900">H={kwRegion?.statistic?.toFixed(1) ?? '—'}</div>
          <div className={`text-xs mt-2 font-medium ${kwRegion?.significant ? 'text-red-500' : 'text-green-600'}`}>
            p={kwRegion?.p_value?.toFixed(3) ?? '—'} · {kwRegion?.significant ? '⚠ Bias значим' : '✓ Однородно'}
          </div>
          <p className="text-[10px] text-slate-400 mt-1.5 leading-snug">Тест: одинаков ли ML-балл по регионам?</p>
          {kwRegion?.significant && kwRegion?.p_value < 0.001 && (
            <div className="mt-2 p-2 bg-slate-50 rounded-md border border-slate-100">
              <p className="text-[9px] text-slate-500 leading-relaxed">
                <Info size={9} className="inline mr-1" weight="fill" />
                При большом N даже малые различия становятся значимыми. Смотрите на эффект, а не только на p-value.
              </p>
            </div>
          )}
        </MetricCard>

        <MetricCard icon={GitBranch} iconBg="bg-purple-100" iconColor="text-purple-600" label="Kruskal-Wallis — Направления" isLoading={isLoading}>
          <div className="text-2xl font-bold text-slate-900">H={kwDir?.statistic?.toFixed(1) ?? '—'}</div>
          <div className={`text-xs mt-2 font-medium ${kwDir?.significant ? 'text-red-500' : 'text-green-600'}`}>
            p={kwDir?.p_value?.toFixed(3) ?? '—'} · {kwDir?.significant ? '⚠ Bias значим' : '✓ Однородно'}
          </div>
          <p className="text-[10px] text-slate-400 mt-1.5 leading-snug">Тест: одинаков ли балл по видам животноводства?</p>
          {kwDir?.significant && kwDir?.p_value < 0.001 && (
            <div className="mt-2 p-2 bg-slate-50 rounded-md border border-slate-100">
              <p className="text-[9px] text-slate-500 leading-relaxed">
                <Info size={9} className="inline mr-1" weight="fill" />
                Разные направления имеют разную экономику. Это ожидаемо.
              </p>
            </div>
          )}
        </MetricCard>
      </div>

      {/* Charts row — Lorenz + Z-score */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Lorenz */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <CardHeader
            title="Кривая Лоренца"
            subtitle="Распределение субсидий по производителям"
          />
          <div className="p-5">
            <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-100 text-xs text-blue-800 leading-relaxed">
              <span className="font-semibold">Кривая Лоренца</span> показывает, насколько равномерно
              распределены субсидии между производителями.
              {' '}Если бы все получали поровну — это была бы <span className="font-semibold">линия равенства</span> (диагональ).
              {' '}Чем больше кривая отклоняется от диагонали, тем <span className="font-semibold">неравномернее</span> распределение.
              {' '}<br /><br />
              <span className="font-semibold">Gini = 0</span> — полное равенство · <span className="font-semibold">Gini = 1</span> — всё одному производителю.
              {' '}Текущий Gini: <strong>{gini?.toFixed(3) ?? '—'}</strong> ({giniInfo?.label ?? '—'} неравенство).
            </div>
            {isLoading ? <Skeleton variant="chart" /> : <LorenzChart data={fairness?.lorenz_curve} />}
          </div>
        </div>

        {/* Z-scores — visual component */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <CardHeader
            title="Z-score по регионам"
            subtitle="|z| > 1.0 — систематическое отклонение от среднего"
          />
          <div className="p-5 overflow-x-auto">
            <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-100 text-xs text-blue-800 leading-relaxed">
              <span className="font-semibold">Z-score</span> показывает отклонение региона от среднего значения ML-балла.
              {' '}Рассчитывается как <span className="font-mono">(балл_региона − среднее) / σ</span>.
              {' '}<span className="font-semibold">z &gt; 0</span> — выше среднего, <span className="font-semibold">z &lt; 0</span> — ниже.
              {' '}|z| &gt; 1 (красный) — систематическое отклонение, требует анализа.
            </div>
            {isLoading ? <Skeleton variant="chart" /> : (
              zscores.length === 0
                ? <p className="text-slate-400 text-sm text-center py-8">Нет данных по регионам</p>
                : (
                  <div style={{ height: chartH }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={zscores} layout="vertical" margin={{ top: 4, right: 56, left: 4, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
                        <XAxis type="number" tick={{ fontSize: 10, fill: '#94A3B8' }} domain={[-3.5, 3.5]} />
                        <YAxis type="category" dataKey="region" width={110} tick={{ fontSize: 10, fill: '#475569' }} />
                        <Tooltip content={<ZScoreTooltip />} />
                        <ReferenceLine x={1}  stroke="#F59E0B" strokeDasharray="4 4" label={{ value: '+1σ', position: 'insideTopRight', fontSize: 9, fill: '#D97706' }} />
                        <ReferenceLine x={-1} stroke="#F59E0B" strokeDasharray="4 4" label={{ value: '-1σ', position: 'insideBottomRight', fontSize: 9, fill: '#D97706' }} />
                        <ReferenceLine x={0}  stroke="#E2E8F0" />
                        <Bar dataKey="z_score" radius={[0, 4, 4, 0]} maxBarSize={22}>
                          {zscores.map((e, i) => (
                            <Cell key={i} fill={e.is_outlier ? '#DC2626' : '#16A34A'} fillOpacity={0.82} />
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

      {/* Heatmap */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <CardHeader
          title="Тепловая карта: Регион × Направление"
          subtitle="Средний ML-балл производителей в разрезе регион / тип животноводства"
        />
        <div className="p-5 overflow-hidden">
          {isLoading ? <Skeleton variant="chart" /> : <Heatmap data={heatmap} />}
        </div>
      </div>

      {/* Regional Stats Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <CardHeader
          title="Статистика по регионам"
          subtitle="Реальные данные о заявках, успешности и суммах субсидий"
        />
        <RegionalTable data={regions} isLoading={isLoading} />
      </div>
    </div>
  )
}
