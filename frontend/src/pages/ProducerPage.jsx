import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Sparkle, FileText, CheckCircle, TreeStructure, CalendarBlank, Warning, ArrowRight, Gauge, GitFork, Info, Lightbulb, MapPin, Signpost } from '@phosphor-icons/react'
import { getProducerDetail, getProducerAdvice, getProducerConfidence, getCounterfactual, getProducerRisk } from '../services/api'
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

function CounterfactualTooltip() {
  return (
    <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 mb-4">
      <div className="flex items-start gap-2">
        <Info size={13} className="text-blue-500 mt-0.5 flex-shrink-0" weight="fill" />
        <div>
          <p className="text-[11px] font-semibold text-blue-800 mb-0.5">Что такое контрфактуальный анализ?</p>
          <p className="text-[11px] text-blue-700 leading-relaxed">
            Ответ на вопрос: <strong>«Что нужно изменить, чтобы получить одобрение?»</strong> Система находит минимальные изменения в ваших данных, которые переведут скор через порог одобрения.
          </p>
        </div>
      </div>
    </div>
  )
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

  const { data: confidence } = useQuery({
    queryKey: ['confidence', id],
    queryFn: () => getProducerConfidence(id),
    enabled: !!id,
    staleTime: 300_000,
  })

  const { data: counterfactual } = useQuery({
    queryKey: ['counterfactual', id],
    queryFn: () => getCounterfactual(id),
    enabled: !!id,
    staleTime: 300_000,
    retry: 1,
  })

  const { data: advice, isLoading: adviceLoading, isError: adviceError, refetch: refetchAdvice } = useQuery({
    queryKey: ['advice', id],
    queryFn: () => getProducerAdvice(id),
    enabled: !!id,
    retry: 2,
    staleTime: 300_000,
  })

  const { data: riskProfile } = useQuery({
    queryKey: ['risk', id],
    queryFn: () => getProducerRisk(id),
    enabled: !!id,
    staleTime: 300_000,
    retry: 1,
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
          <button
            onClick={() => navigate(`/dashboard?region=${encodeURIComponent(producer.region)}`)}
            className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 hover:underline transition-colors cursor-pointer"
            title={`Фильтр по региону: ${producer.region}`}
          >
            <MapPin size={12} weight="fill" />
            {producer.region}
          </button>
          <span className="text-xs text-slate-300">·</span>
          <button
            onClick={() => navigate(`/dashboard?direction=${encodeURIComponent(producer.direction)}`)}
            className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 hover:underline transition-colors cursor-pointer"
            title={`Фильтр по направлению: ${producer.direction}`}
          >
            <Signpost size={12} weight="fill" />
            {producer.direction}
          </button>
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

      {/* Drift Confidence Banner */}
      {confidence && confidence.is_low_confidence && (
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
          <Gauge size={15} className="text-amber-500 flex-shrink-0 mt-0.5" weight="fill" />
          <div>
            <p className="text-xs font-semibold text-amber-800">
              Низкая уверенность модели — {(confidence.confidence_score * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-amber-700 mt-0.5 leading-relaxed">{confidence.explanation}</p>
            {confidence.anomalous_features?.length > 0 && (
              <div className="flex gap-1.5 mt-1.5 flex-wrap">
                {confidence.anomalous_features.map(f => (
                  <span key={f} className="text-[10px] font-medium bg-amber-100 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full">{f}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

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

          <div className={`border rounded-xl p-5 ${
            advice?._ai_status === 'not_configured'
              ? 'bg-amber-50 border-amber-200'
              : 'bg-blue-50 border-blue-200'
          }`}>
            <div className="flex items-center justify-between mb-2.5">
              <div className="flex items-center gap-2">
                <Sparkle size={13} className={
                  advice?._ai_status === 'not_configured' ? 'text-amber-600' : 'text-blue-600'
                } weight="fill" />
                <span className={`font-semibold text-xs tracking-wide ${
                  advice?._ai_status === 'not_configured' ? 'text-amber-700' : 'text-blue-700'
                }`}>
                  SubsidyLens AI — объяснение балла
                  {advice?._ai_status === 'not_configured' && (
                    <span className="ml-2 px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-[9px] font-bold uppercase">Не настроен</span>
                  )}
                </span>
              </div>
              {adviceError && (
                <button
                  onClick={() => refetchAdvice()}
                  className="text-[10px] font-medium text-blue-600 hover:text-blue-800 px-2 py-1 rounded-md hover:bg-blue-100 transition-colors"
                >
                  Повторить
                </button>
              )}
            </div>
            {adviceLoading
              ? <div className="space-y-2"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-4/5" /></div>
              : adviceError
                ? <p className="text-sm text-blue-600 leading-relaxed opacity-70">Не удалось получить объяснение от SubsidyLens AI. Проверьте соединение и попробуйте снова.</p>
                : (
                  <div>
                    <p className={`text-sm leading-relaxed ${
                      advice?._ai_status === 'not_configured' ? 'text-amber-800' : 'text-slate-700'
                    }`}>{advice?.score_explanation}</p>
                    {advice?._ai_status === 'not_configured' && (
                      <p className="text-xs text-amber-700 mt-2 leading-relaxed">{advice?.baseline_injustice}</p>
                    )}
                  </div>
                )
            }
          </div>

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

          {/* Counterfactual Explanations */}
          {counterfactual && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <CardHeader
                title="Контрфактуальный анализ"
                subtitle={`Минимальные изменения для прохода порога ${(counterfactual.threshold * 100).toFixed(1)}%`}
              />
              <div className="p-5">
                <CounterfactualTooltip />
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex-1 bg-slate-100 rounded-lg p-2.5 text-center">
                    <div className="text-[10px] text-slate-400 font-medium mb-1">Сейчас</div>
                    <div className="text-base font-bold text-red-600">{(counterfactual.current_score * 100).toFixed(1)}%</div>
                  </div>
                  <ArrowRight size={14} className="text-slate-300 flex-shrink-0" />
                  <div className="flex-1 bg-green-50 border border-green-200 rounded-lg p-2.5 text-center">
                    <div className="text-[10px] text-green-600 font-medium mb-1">Цель</div>
                    <div className="text-base font-bold text-green-700">{(counterfactual.target_score * 100).toFixed(1)}%</div>
                  </div>
                </div>
                <div className="space-y-2.5">
                  {(counterfactual.changes || []).map((ch, i) => (
                    <div key={i} className="rounded-xl border border-slate-100 overflow-hidden">
                      <div className="flex items-center gap-2 px-3 py-2 bg-slate-50">
                        <GitFork size={11} className="text-slate-400" weight="fill" />
                        <span className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider">{ch.feature}</span>
                        <span className="ml-auto text-[10px] font-bold text-green-600">+{ch.impact_pct}%</span>
                      </div>
                      <div className="px-3 py-2 space-y-1">
                        <div className="flex items-center gap-2 text-xs">
                          <span className="text-slate-400 w-20 flex-shrink-0">Сейчас:</span>
                          <span className="font-medium text-red-600 line-through">{ch.current}</span>
                          <ArrowRight size={10} className="text-slate-300" />
                          <span className="font-semibold text-green-700">{ch.recommended}</span>
                        </div>
                        <p className="text-[11px] text-slate-500 leading-relaxed">{ch.explanation}</p>
                      </div>
                    </div>
                  ))}
                </div>
                {!counterfactual.achievable && (
                  <p className="text-xs text-slate-400 text-center mt-3">Достижение порога через управляемые признаки недоступно</p>
                )}
              </div>
            </div>
          )}

          {/* Risk Profile */}
          {riskProfile && riskProfile.signal_count > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <CardHeader
                title="Индикаторы риска"
                subtitle={`Уровень: ${riskProfile.risk_level === 'low' ? 'Низкий' : riskProfile.risk_level === 'medium' ? 'Средний' : riskProfile.risk_level === 'high' ? 'Высокий' : 'Критический'}`}
              />
              <div className="p-5">
                {/* Overall risk bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-slate-500 font-medium">Общий риск</span>
                    <span className={`text-sm font-bold ${
                      riskProfile.overall_risk < 20 ? 'text-green-600' :
                      riskProfile.overall_risk < 45 ? 'text-amber-600' :
                      riskProfile.overall_risk < 70 ? 'text-orange-600' : 'text-red-600'
                    }`}>
                      {riskProfile.overall_risk}/100
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-500 ${
                        riskProfile.overall_risk < 20 ? 'bg-green-500' :
                        riskProfile.overall_risk < 45 ? 'bg-amber-500' :
                        riskProfile.overall_risk < 70 ? 'bg-orange-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(100, riskProfile.overall_risk)}%` }}
                    />
                  </div>
                </div>
                {/* Individual signals */}
                <div className="space-y-2">
                  {(riskProfile.signals || []).map((signal, i) => (
                    <div key={i} className="rounded-lg border border-slate-100 overflow-hidden">
                      <div className="flex items-center gap-2 px-3 py-2 bg-slate-50">
                        <Warning size={11} className={`${
                          signal.severity > 70 ? 'text-red-500' : signal.severity > 40 ? 'text-amber-500' : 'text-slate-400'
                        }`} weight="fill" />
                        <span className="text-xs font-semibold text-slate-700 flex-1">{signal.title}</span>
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          signal.severity > 70 ? 'bg-red-50 text-red-600' :
                          signal.severity > 40 ? 'bg-amber-50 text-amber-600' : 'bg-slate-100 text-slate-500'
                        }`}>
                          {signal.severity}
                        </span>
                      </div>
                      <div className="px-3 py-2">
                        <p className="text-[11px] text-slate-600 leading-relaxed">{signal.description}</p>
                        <p className="text-[10px] text-green-700 mt-1 font-medium">→ {signal.action}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="bg-gradient-to-br from-slate-50 to-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <CardHeader title="Что улучшить" subtitle="Конкретные шаги для роста ML-балла" />
            <div className="p-5">
              {adviceLoading ? (
                <div className="space-y-2.5">
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                </div>
              ) : (
                <div className="space-y-3">
                  {(advice?.recommendations || []).map((rec, i) => {
                    // Support both structured {problem,cause,action} and legacy {text} formats
                    const hasPCA = rec.problem && rec.cause && rec.action
                    return (
                      <div key={i} className="rounded-xl border overflow-hidden bg-white shadow-sm hover:shadow-md transition-shadow duration-200" style={{ borderColor: '#FDE68A' }}>
                        {/* Header: problem */}
                        <div className="flex items-start gap-2.5 px-3.5 pt-3 pb-2" style={{ background: 'linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)' }}>
                          <Warning size={13} className="text-amber-500 mt-0.5 flex-shrink-0" weight="fill" />
                          <p className="text-xs font-semibold text-amber-800 leading-snug flex-1">
                            {hasPCA ? rec.problem : rec.text}
                          </p>
                          <ImpactBadge impact={rec.impact} />
                        </div>
                        {hasPCA && (
                          <div className="px-3.5 pb-3 pt-1.5 space-y-2" style={{ background: '#FFFBEB' }}>
                            {/* Cause */}
                            <div className="flex items-start gap-2">
                              <span className="text-[9px] font-bold text-amber-500 uppercase tracking-wider mt-0.5 w-14 flex-shrink-0">Причина</span>
                              <p className="text-xs text-slate-600 leading-relaxed">{rec.cause}</p>
                            </div>
                            {/* Action */}
                            <div className="flex items-start gap-2 pt-1.5 border-t border-amber-100">
                              <span className="text-[9px] font-bold text-green-600 uppercase tracking-wider mt-0.5 w-14 flex-shrink-0 flex items-center gap-0.5">
                                <ArrowRight size={9} weight="bold" />Действие
                              </span>
                              <p className="text-xs font-medium text-slate-700 leading-relaxed">{rec.action}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                  {(!advice?.recommendations || advice.recommendations.length === 0) && (
                    <div className="text-center py-6">
                      <Lightbulb size={24} className="text-slate-300 mx-auto mb-2" />
                      <p className="text-xs text-slate-400">Нет рекомендаций</p>
                    </div>
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
