import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Sparkle, Lightbulb } from '@phosphor-icons/react'
import { getProducerDetail, getProducerAdvice } from '../services/api'
import { Badge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import { SHAPBarChart } from '../components/charts/SHAPBarChart'
import { HistoryLineChart } from '../components/charts/HistoryLineChart'

function ScoreBadge({ score }) {
  if (score >= 0.8) return <Badge variant="success">{(score * 100).toFixed(1)}%</Badge>
  if (score >= 0.6) return <Badge variant="warning">{(score * 100).toFixed(1)}%</Badge>
  return <Badge variant="error">{(score * 100).toFixed(1)}%</Badge>
}

function DeltaBadge({ delta }) {
  if (delta > 0) return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 border border-green-200">
      ↑ +{delta} позиции
    </span>
  )
  if (delta < 0) return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200">
      ↓ {delta} позиции
    </span>
  )
  return <span className="text-slate-400 text-xs">Совпадает</span>
}

export default function ProducerPage() {
  const { id } = useParams()
  const navigate = useNavigate()

  const { data: producer, isLoading } = useQuery({
    queryKey: ['producer', id],
    queryFn: () => getProducerDetail(id),
    enabled: !!id,
  })

  const { data: advice, isLoading: adviceLoading } = useQuery({
    queryKey: ['advice', id],
    queryFn: () => getProducerAdvice(id),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2 space-y-4">
            <Skeleton className="h-64 rounded-xl" />
            <Skeleton className="h-48 rounded-xl" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-32 rounded-xl" />
            <Skeleton className="h-48 rounded-xl" />
          </div>
        </div>
      </div>
    )
  }

  if (!producer) return null

  const stats = producer.stats || {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-slate-400 hover:text-slate-600 text-sm flex items-center gap-1 transition-colors"
          >
            <ArrowLeft size={14} /> Назад
          </button>
          <h1 className="text-2xl font-bold text-slate-900 font-mono">{producer.producer_id}</h1>
          {producer.hidden_talent && <Badge variant="hidden">★ Скрытый талант</Badge>}
          {producer.at_risk && <Badge variant="error">↓ Переоценён</Badge>}
        </div>
      </div>

      {/* Meta row */}
      <div className="flex items-center gap-4 text-sm text-slate-500">
        <span>📍 {producer.region}</span>
        <span>•</span>
        <span>🐄 {producer.direction}</span>
      </div>

      {/* Metric badges */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 uppercase tracking-wide font-medium">ML Score</span>
          <ScoreBadge score={producer.ml_score} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 uppercase tracking-wide font-medium">ML Ранг</span>
          <span className="text-sm font-bold text-blue-600">#{producer.ml_rank}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 uppercase tracking-wide font-medium">FCFS Ранг</span>
          <span className="text-sm font-bold text-slate-500">#{producer.fcfs_rank}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 uppercase tracking-wide font-medium">Delta</span>
          <DeltaBadge delta={producer.delta} />
        </div>
      </div>

      {/* Stats grid 2x2 */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Заявок всего', value: stats.total_applications || '—', icon: '📋' },
          { label: 'Исполнено', value: stats.completed || '—', icon: '✅' },
          { label: 'Направлений', value: stats.directions_count || '—', icon: '🌾' },
          { label: 'Активных месяцев', value: stats.active_months || '—', icon: '📅' },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">{s.label}</span>
              <span>{s.icon}</span>
            </div>
            <div className="text-2xl font-bold text-slate-900">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Main 2-col layout */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left: SHAP + History */}
        <div className="col-span-2 space-y-6">
          {/* SHAP Chart */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Почему такой балл — SHAP</h2>
              <p className="text-xs text-slate-400 mt-0.5">Влияние каждого признака на ML Score</p>
            </div>
            <div className="p-6">
              <SHAPBarChart data={producer.shap_values} />
            </div>
          </div>

          {/* Gemini score explanation */}
          {(advice || adviceLoading) && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Sparkle size={13} className="text-blue-600" />
                <span className="text-blue-600 font-semibold text-sm">Gemini AI — объяснение балла</span>
              </div>
              {adviceLoading
                ? <Skeleton className="h-12 w-full" />
                : <p className="text-sm text-slate-700 leading-relaxed">{advice?.score_explanation}</p>
              }
            </div>
          )}

          {/* History */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">История заявок</h2>
            </div>
            <div className="p-6">
              <HistoryLineChart data={producer.history} />
            </div>
          </div>
        </div>

        {/* Right: Rankings + Recommendations */}
        <div className="space-y-4">
          {/* ML vs FCFS comparison */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">ML vs FCFS</h3>
            <div className="space-y-3">
              <div className="bg-blue-600 text-white rounded-lg p-4 text-center">
                <div className="text-xs opacity-80 mb-1">ML Ранг</div>
                <div className="text-3xl font-bold">#{producer.ml_rank}</div>
              </div>
              <div className="bg-slate-100 text-slate-600 rounded-lg p-4 text-center">
                <div className="text-xs font-medium mb-1">FCFS Ранг</div>
                <div className="text-3xl font-bold">#{producer.fcfs_rank}</div>
              </div>
            </div>
            {(advice || adviceLoading) && (
              <div className="mt-4 pt-4 border-t border-slate-100">
                {adviceLoading
                  ? <Skeleton className="h-16 w-full" />
                  : <p className="text-xs text-slate-500 leading-relaxed">{advice?.baseline_injustice}</p>
                }
              </div>
            )}
          </div>

          {/* Recommendations */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Что улучшить</h3>
            {adviceLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : (
              <div className="space-y-3">
                {(advice?.recommendations || []).map((rec, i) => (
                  <div key={i} className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <Lightbulb size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-xs text-slate-700 leading-relaxed">{rec.text}</p>
                        <span className="inline-block mt-1.5 px-2 py-0.5 bg-green-100 text-green-700 text-xs font-semibold rounded-full">
                          +{rec.impact}% к вероятности
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
