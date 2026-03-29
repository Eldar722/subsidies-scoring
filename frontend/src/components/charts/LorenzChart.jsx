import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const EQUALITY_LINE = [
  { population: 0, cumulative_share: 0 },
  { population: 1, cumulative_share: 1 },
]

export function LorenzChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="text-slate-400 text-sm p-4 text-center">Нет данных</div>
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
        <XAxis
          dataKey="population"
          type="number"
          domain={[0, 1]}
          tickFormatter={v => `${Math.round(v * 100)}%`}
          label={{ value: 'Доля производителей', position: 'insideBottom', offset: -10, fontSize: 12, fill: '#64748B' }}
          tick={{ fontSize: 11, fill: '#94A3B8' }}
        />
        <YAxis
          dataKey="cumulative_share"
          type="number"
          domain={[0, 1]}
          tickFormatter={v => `${Math.round(v * 100)}%`
          }
          label={{ value: 'Доля субсидий', angle: -90, position: 'insideLeft', offset: 10, fontSize: 12, fill: '#64748B' }}
          tick={{ fontSize: 11, fill: '#94A3B8' }}
        />
        <Tooltip
          formatter={(value) => [`${(value * 100).toFixed(2)}%`]}
          labelFormatter={(v) => `Производители: ${(v * 100).toFixed(2)}%`}
        />
        <Legend
          verticalAlign="top"
          wrapperStyle={{ fontSize: 12, paddingBottom: 8 }}
        />
        <Line
          data={data}
          dataKey="cumulative_share"
          name="Реальное распределение"
          stroke="#2563EB"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
        <Line
          data={EQUALITY_LINE}
          dataKey="cumulative_share"
          name="Идеальное равенство"
          stroke="#94A3B8"
          strokeWidth={1.5}
          strokeDasharray="5 5"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
