import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion' // eslint-disable-line no-unused-vars
import { X, MapPin, ArrowRight, Sparkle } from '@phosphor-icons/react'
import { useQuery } from '@tanstack/react-query'
import { getProducerDetail } from '../../services/api'
import { Badge, getScoreVariant } from '../ui/Badge'
import { Skeleton } from '../ui/Skeleton'

export function ProducerSidePanel({ producerId, onClose }) {
  const navigate = useNavigate()
  const { data: producer, isLoading } = useQuery({
    queryKey: ['producer', producerId],
    queryFn: () => getProducerDetail(producerId),
    enabled: !!producerId,
  })

  return (
    <>
      <motion.div
        key="overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/25 backdrop-blur-[2px] z-40"
        onClick={onClose}
      />
      <motion.div
        key="panel"
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 28, stiffness: 220 }}
        className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl z-50 flex flex-col border-l border-slate-100"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div>
            <p className="font-mono font-bold text-slate-900 text-sm leading-snug">{producerId}</p>
            {producer && <p className="text-xs text-slate-400 mt-0.5">{producer.region} · {producer.direction}</p>}
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-md flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {isLoading ? (
          <div className="p-5 space-y-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton variant="card" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        ) : producer ? (
          <div className="flex-1 overflow-y-auto">
            <div className="p-5 space-y-5">
              {/* Badges */}
              <div className="flex items-center gap-2 flex-wrap">
                {producer.hidden_talent && <Badge variant="hidden_talent" />}
                {producer.at_risk && <Badge variant="at_risk" />}
              </div>

              {/* Scores grid */}
              <div>
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Показатели</p>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-50 rounded-lg p-3">
                    <p className="text-[10px] text-slate-400 font-medium mb-1.5">ML Score</p>
                    <Badge variant={getScoreVariant(producer.ml_score)}>{(producer.ml_score * 100).toFixed(1)}%</Badge>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <p className="text-[10px] text-slate-400 font-medium mb-1.5">ML Ранг</p>
                    <p className="text-sm font-bold text-blue-600">#{producer.ml_rank}</p>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <p className="text-[10px] text-slate-400 font-medium mb-1.5">FCFS Ранг</p>
                    <p className="text-sm font-bold text-slate-500">#{producer.fcfs_rank}</p>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <p className="text-[10px] text-slate-400 font-medium mb-1.5">Delta</p>
                    <p className={`text-sm font-bold ${producer.delta > 0 ? 'text-green-600' : producer.delta < 0 ? 'text-red-500' : 'text-slate-400'}`}>
                      {producer.delta > 0 ? `↑ +${producer.delta}` : producer.delta < 0 ? `↓ ${producer.delta}` : '—'}
                    </p>
                  </div>
                </div>
              </div>

              {/* SHAP top-3 */}
              {producer.shap_values?.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2 flex items-center gap-1">
                    <Sparkle size={10} className="text-blue-400" weight="fill" /> Топ факторы SHAP
                  </p>
                  <div className="space-y-2.5">
                    {producer.shap_values.slice(0, 3).map((s) => (
                      <div key={s.feature} className="flex items-center gap-2.5">
                        <span className="text-[11px] text-slate-500 w-28 truncate flex-shrink-0">{s.feature_label || s.feature}</span>
                        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full transition-all duration-300 ${s.shap_value > 0 ? 'bg-green-500' : 'bg-red-400'}`}
                            style={{ width: `${Math.min(Math.abs(s.shap_value) * 300, 100)}%` }}
                          />
                        </div>
                        <span className={`text-[11px] font-semibold w-10 text-right flex-shrink-0 ${s.shap_value > 0 ? 'text-green-600' : 'text-red-500'}`}>
                          {s.shap_value > 0 ? '+' : ''}{s.shap_value.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : null}

        {/* Footer */}
        <div className="px-5 py-4 border-t border-slate-100 bg-slate-50/50">
          <button
            onClick={() => { navigate(`/producer/${producerId}`); onClose() }}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white text-xs font-semibold py-2.5 rounded-lg hover:bg-blue-700 active:scale-[0.98] transition-all duration-150 shadow-sm"
          >
            Открыть полный профиль
            <ArrowRight size={13} />
          </button>
        </div>
      </motion.div>
    </>
  )
}
