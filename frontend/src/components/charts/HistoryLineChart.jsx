import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-lg text-xs">
      <p className="font-semibold text-slate-700 mb-1">{label}</p>
      <p className="text-blue-600">Заявок: <span className="font-semibold">{payload[0]?.value}</span></p>
    </div>
  )
}

export function HistoryLineChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="text-slate-400 text-sm p-4 text-center">Нет данных истории</div>
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2563EB" stopOpacity={0.12} />
            <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 10, fill: '#94A3B8' }}
          interval={1}
          angle={-30}
          textAnchor="end"
          height={36}
        />
        <YAxis tick={{ fontSize: 10, fill: '#94A3B8' }} />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="applications"
          stroke="#2563EB"
          strokeWidth={2}
          fill="url(#histGrad)"
          dot={{ r: 3, fill: '#2563EB', strokeWidth: 0 }}
          activeDot={{ r: 5 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
