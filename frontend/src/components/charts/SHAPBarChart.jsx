import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-lg text-xs">
      <p className="font-semibold text-slate-800 mb-1">{d.feature_label}</p>
      <p className="text-slate-500">SHAP: <span className={d.shap_value >= 0 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>{d.shap_value >= 0 ? '+' : ''}{d.shap_value.toFixed(4)}</span></p>
      <p className="text-slate-500">Значение: <span className="font-medium">{d.raw_value}</span></p>
    </div>
  )
}

export function SHAPBarChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="text-slate-400 text-sm p-4 text-center">Нет данных SHAP</div>
  }

  const sorted = [...data].sort((a, b) => b.shap_value - a.shap_value)

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, sorted.length * 44)}>
      <BarChart
        data={sorted}
        layout="vertical"
        margin={{ top: 4, right: 60, left: 8, bottom: 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: '#94A3B8' }}
          tickFormatter={v => v.toFixed(2)}
          domain={['dataMin - 0.02', 'dataMax + 0.02']}
        />
        <YAxis
          type="category"
          dataKey="feature_label"
          width={160}
          tick={{ fontSize: 12, fill: '#334155' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine x={0} stroke="#CBD5E1" strokeWidth={1.5} />
        <Bar dataKey="shap_value" radius={[0, 4, 4, 0]} maxBarSize={28}>
          {sorted.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.shap_value >= 0 ? '#16A34A' : '#DC2626'}
              fillOpacity={0.85}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
