import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
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
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />
      <motion.div
        key="panel"
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-50 flex flex-col overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <span className="font-mono font-bold text-slate-800 text-sm">{producerId}</span>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            <X size={18} />
          </button>
        </div>

        {isLoading ? (
          <div className="p-5 space-y-3">
            <Skeleton variant="text" className="w-3/4" />
            <Skeleton variant="text" className="w-1/2" />
            <Skeleton variant="card" />
          </div>
        ) : producer ? (
          <div className="p-5 space-y-5 flex-1">
            {/* Основное */}
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Основное</p>
              <div className="flex items-center gap-2 text-sm text-slate-600 mb-1">
                <MapPin size={13} className="text-slate-400" />
                {producer.region}
              </div>
              <Badge variant="default" className="mt-1">{producer.direction}</Badge>
            </div>

            {/* Баллы */}
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Баллы</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-slate-50 rounded-lg p-2.5">
                  <p className="text-xs text-slate-500 mb-1">ML Score</p>
                  <Badge variant={getScoreVariant(producer.ml_score)}>{(producer.ml_score * 100).toFixed(1)}%</Badge>
                </div>
                <div className="bg-slate-50 rounded-lg p-2.5">
                  <p className="text-xs text-slate-500 mb-1">ML Ранг</p>
                  <p className="text-sm font-bold text-blue-600">#{producer.ml_rank}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-2.5">
                  <p className="text-xs text-slate-500 mb-1">FCFS Ранг</p>
                  <p className="text-sm font-bold text-slate-600">#{producer.fcfs_rank}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-2.5">
                  <p className="text-xs text-slate-500 mb-1">Delta</p>
                  <p className={`text-sm font-bold ${producer.delta > 0 ? 'text-green-600' : producer.delta < 0 ? 'text-red-600' : 'text-slate-400'}`}>
                    {producer.delta > 0 ? `↑ +${producer.delta}` : producer.delta < 0 ? `↓ ${producer.delta}` : '—'}
                  </p>
                </div>
              </div>
            </div>

            {/* SHAP топ-3 */}
            {producer.shap_values?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
                  <Sparkle size={12} className="inline mr-1" />Топ факторы SHAP
                </p>
                <div className="space-y-2">
                  {producer.shap_values.slice(0, 3).map((s) => (
                    <div key={s.feature} className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 w-32 truncate">{s.feature_label}</span>
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-2 rounded-full ${s.shap_value > 0 ? 'bg-green-500' : 'bg-red-500'}`}
                          style={{ width: `${Math.min(Math.abs(s.shap_value) * 300, 100)}%` }}
                        />
                      </div>
                      <span className={`text-xs font-medium w-10 text-right ${s.shap_value > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {s.shap_value > 0 ? '+' : ''}{s.shap_value.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}

        {/* Footer */}
        <div className="px-5 py-4 border-t border-slate-100">
          <button
            onClick={() => { navigate(`/producer/${producerId}`); onClose() }}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white text-sm font-medium py-2.5 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Открыть полный профиль
            <ArrowRight size={14} />
          </button>
        </div>
      </motion.div>
    </>
  )
}
