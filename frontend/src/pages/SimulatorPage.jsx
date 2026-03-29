import { useState } from 'react'

const SLIDERS = [
  { key: 'completion_rate', label: 'Результативность', defaultValue: 35 },
  { key: 'approval_rate',   label: 'Одобряемость заявок', defaultValue: 25 },
  { key: 'diversification', label: 'Диверсификация направлений', defaultValue: 20 },
  { key: 'activity',        label: 'Активность', defaultValue: 10 },
  { key: 'working_hours',   label: 'Рабочее время', defaultValue: 10 },
]

const initialWeights = Object.fromEntries(SLIDERS.map(s => [s.key, s.defaultValue]))

export default function SimulatorPage() {
  const [weights, setWeights] = useState(initialWeights)

  const total = Object.values(weights).reduce((s, v) => s + v, 0)

  const handleChange = (key, value) => {
    setWeights(prev => ({ ...prev, [key]: Number(value) }))
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Симулятор весов</h1>

      <div className="flex gap-6">
        {/* Sliders Panel */}
        <div className="w-1/3">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <h2 className="text-sm font-semibold text-slate-700 mb-4">Веса факторов</h2>
            <div className="space-y-5">
              {SLIDERS.map(slider => (
                <div key={slider.key}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-slate-700">{slider.label}</span>
                    <span className="text-sm font-semibold text-blue-600">{weights[slider.key]}%</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={weights[slider.key]}
                    onChange={e => handleChange(slider.key, e.target.value)}
                    className="w-full accent-blue-600"
                  />
                </div>
              ))}
            </div>

            {/* Total indicator */}
            <div className={`mt-5 pt-4 border-t border-slate-100 flex justify-between items-center`}>
              <span className="text-sm text-slate-500">Сумма весов:</span>
              <span className={`text-sm font-semibold ${total === 100 ? 'text-green-600' : 'text-amber-600'}`}>
                {total}% {total !== 100 && '⚠'}
              </span>
            </div>
          </div>
        </div>

        {/* Results Panel */}
        <div className="w-2/3">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 h-full flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-3">🎮</div>
              <p className="text-slate-500 text-sm">
                Результаты появятся после подключения API симулятора
              </p>
              <p className="text-slate-400 text-xs mt-1">(P1 task)</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
