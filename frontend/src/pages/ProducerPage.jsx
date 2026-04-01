import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Sparkle, Lightbulb, FileText, CheckCircle, TreeStructure, CalendarBlank } from '@phosphor-icons/react'
import { getProducerDetail, getProducerAdvice } from '../services/api'
import { Badge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import { CardHeader } from '../components/ui/Card'
import { SHAPBarChart } from '../components/charts/SHAPBarChart'
import { HistoryLineChart } from '../components/charts/HistoryLineChart'

function ScoreBadge({ score }) {
  if (score >= 0.8) return <Badge variant="success">{(score * 100).toFixed(1)}%</Badge>
  if (score >= 0.6) return <Badge variant="warning">{(score * 100).toFixed(1)}%</Badge>
  return <Badge variant="error">{(score * 100).toFixed(1)}%</Badge>
}

function DeltaBadge({ delta }) {
  if (delta > 0) return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-50 text-green-700 border border-green-200">
      ↑ +{delta} позиции
    </span>
  )
  if (delta < 0) return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
      ↓ {delta} позиции
    </span>
  )
  return <span className="text-slate-400 text-xs font-medium">Совпадает</span>
}

function ImpactBadge({ impact }) {
  const n = parseInt(impact)
  if (n > 20) return <span className="inline-block mt-1.5 px-2 py-0.5 bg-green-50 text-green-700 border border-green-200 text-xs font-semibold rounded-full">+{impact}% к вероятности</span>
  if (n > 10) return <span className="inline-block mt-1.5 px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 text-xs font-semibold rounded-full">+{impact}% к вероятности</span>
  return <span className="inline-block mt-1.5 px-2 py-0.5 bg-slate-100 text-slate-600 text-xs font-semibold rounded-full">+{impact}% к вероятности</span>
}

const STAT_CONFIG = [
  { key: 'total_applications', label: 'Заявок всего',      icon: FileText,      iconBg: 'bg-blue-100',   iconColor: 'text-blue-600' },
  { key: 'completed',          label: 'Исполнено',          icon: CheckCircle,   iconBg: 'bg-green-100',  iconColor: 'text-green-600' },
  { key: 'directions_count',   label: 'Направлений',        icon: TreeStructure,     iconBg: 'bg-slate-100',  iconColor: 'text-slate-600' },
  { key: 'active_months',      label: 'Активных месяцев',   icon: CalendarBlank, iconBg: 'bg-purple-100', iconColor: 'text-purple-600' },
]

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
      <div className="space-y-5">
        <Skeleton className="h-6 w-48" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </div>
        <div className="grid grid-cols-3 gap-5">
          <div className="col-span-2 space-y-4">
            <Skeleton className="h-64 rounded-xl" />
            <Skeleton className="h-44 rounded-xl" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-36 rounded-xl" />
            <Skeleton className="h-48 rounded-xl" />
          </div>
        </div>
      </div>
    )
  }

  if (!producer) return null

  const stats = producer.stats || {}

  return (
    <div className="space-y-5 max-w-full">
      {/* Breadcrumb + title */}
      <div>
        <button
          onClick={() => navigate('/dashboard')}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition-colors mb-3 font-medium"
        >
          <ArrowLeft size={13} /> Назад к дашборду
        </button>
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-xl font-bold text-slate-900 font-mono tracking-tight">{producer.producer_id}</h1>
          <span className="text-xs text-slate-400 font-normal">·</span>
          <span className="text-sm text-slate-500">{producer.region}</span>
          <span className="text-xs text-slate-300">·</span>
          <span className="text-sm text-slate-500">{producer.direction}</span>
          {producer.hidden_talent && <Badge variant="hidden">★ Скрытый талант</Badge>}
          {producer.at_risk && <Badge variant="error">↓ Переоценён</Badge>}
        </div>
      </div>

      {/* Metric chips */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-2 shadow-xs">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">ML Score</span>
          <ScoreBadge score={producer.ml_score} />
        </div>
        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-2 shadow-xs">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">ML Ранг</span>
          <span className="text-sm font-bold text-blue-600">#{producer.ml_rank}</span>
        </div>
        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-2 shadow-xs">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">FCFS Ранг</span>
          <span className="text-sm font-bold text-slate-500">#{producer.fcfs_rank}</span>
        </div>
        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-2 shadow-xs">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Delta</span>
          <DeltaBadge delta={producer.delta} />
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CONFIG.map((cfg) => {
          const Icon = cfg.icon
          return (
            <div key={cfg.key} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <div className="flex items-start justify-between mb-2">
                <p className="text-xs text-slate-500 font-medium">{cfg.label}</p>
                <div className={`w-7 h-7 rounded-lg ${cfg.iconBg} flex items-center justify-center flex-shrink-0`}>
                  <Icon size={13} className={cfg.iconColor} weight="bold" />
                </div>
              </div>
              <div className="text-2xl font-bold text-slate-900">{stats[cfg.key] ?? '—'}</div>
            </div>
          )
        })}
      </div>

      {/* Main 2-col layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: SHAP + Gemini + History */}
        <div className="lg:col-span-2 space-y-5">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <CardHeader title="Почему такой балл — SHAP" subtitle="Влияние каждого признака на ML Score" />
            <div className="p-5">
              <SHAPBarChart data={producer.shap_values} />
            </div>
          </div>

          {(advice || adviceLoading) && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2.5">
                <Sparkle size={13} className="text-blue-600" weight="fill" />
                <span className="text-blue-700 font-semibold text-xs tracking-wide">Gemini AI — объяснение балла</span>
              </div>
              {adviceLoading
                ? <Skeleton className="h-12 w-full" />
                : <p className="text-sm text-slate-700 leading-relaxed">{advice?.score_explanation}</p>
              }
            </div>
          )}

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <CardHeader title="История заявок" subtitle="Активность по месяцам" />
            <div className="p-5">
              <HistoryLineChart data={producer.history} />
            </div>
          </div>
        </div>

        {/* Right: Rankings + Recommendations */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <CardHeader title="ML vs FCFS" subtitle="Сравнение систем ранжирования" />
            <div className="p-5 space-y-3">
              <div className="bg-blue-600 text-white rounded-xl p-4 text-center">
                <div className="text-[10px] font-medium opacity-70 uppercase tracking-widest mb-1.5">ML Ранг</div>
                <div className="text-3xl font-bold">#{producer.ml_rank}</div>
              </div>

              {producer.delta !== 0 && (
                <div className="flex items-center justify-center">
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                    producer.delta > 0
                      ? 'bg-green-50 text-green-700 border border-green-200'
                      : 'bg-red-50 text-red-700 border border-red-200'
                  }`}>
                    {producer.delta > 0 ? `↑ +${producer.delta}` : `↓ ${producer.delta}`} позиций
                  </span>
                </div>
              )}

              <div className="bg-slate-100 text-slate-600 rounded-xl p-4 text-center">
                <div className="text-[10px] font-medium text-slate-400 uppercase tracking-widest mb-1.5">FCFS Ранг</div>
                <div className="text-3xl font-bold">#{producer.fcfs_rank}</div>
              </div>

              {(advice || adviceLoading) && (
                <div className="pt-3 border-t border-slate-100">
                  {adviceLoading
                    ? <Skeleton className="h-16 w-full" />
                    : <p className="text-xs text-slate-500 leading-relaxed">{advice?.baseline_injustice}</p>
                  }
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <CardHeader title="Что улучшить" subtitle="Рекомендации по росту балла" />
            <div className="p-5">
              {adviceLoading ? (
                <div className="space-y-2.5">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : (
                <div className="space-y-3">
                  {(advice?.recommendations || []).map((rec, i) => (
                    <div key={i} className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                      <div className="flex items-start gap-2">
                        <Lightbulb size={13} className="text-amber-500 mt-0.5 flex-shrink-0" weight="fill" />
                        <div className="flex-1">
                          <p className="text-xs text-slate-700 leading-relaxed">{rec.text}</p>
                          <ImpactBadge impact={rec.impact} />
                        </div>
                      </div>
                    </div>
                  ))}
                  {(!advice?.recommendations || advice.recommendations.length === 0) && (
                    <p className="text-xs text-slate-400 text-center py-4">Рекомендации загружаются...</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
