function scoreToHeat(score) {
  if (score === undefined || score === null) return '#F1F5F9'
  const t = Math.max(0, Math.min(1, (score - 0.4) / 0.5))
  const r = Math.round(248 - t * (248 - 22))
  const g = Math.round(250 - t * (250 - 163))
  const b = Math.round(252 - t * (252 - 74))
  return `rgb(${r},${g},${b})`
}

function textColor(score) {
  return score >= 0.7 ? '#fff' : '#334155'
}

export function HeatMap({ data }) {
  if (!data || data.length === 0) {
    return <div className="text-slate-400 text-sm p-4 text-center">Нет данных тепловой карты</div>
  }

  const regions = data[0]?.data?.map(d => d.region) || []

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            <th className="text-left px-3 py-2 text-slate-500 font-medium w-36 bg-white">Направление</th>
            {regions.map(reg => (
              <th key={reg} className="px-2 py-2 text-slate-500 font-medium text-center min-w-[80px] bg-white">
                {reg}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr key={row.direction}>
              <td className="px-3 py-1.5 text-slate-700 font-medium bg-slate-50 border border-slate-100">
                {row.direction}
              </td>
              {row.data.map(cell => (
                <td
                  key={cell.region}
                  className="px-2 py-1.5 text-center border border-white font-semibold"
                  style={{
                    backgroundColor: scoreToHeat(cell.avg_score),
                    color: textColor(cell.avg_score),
                  }}
                  title={`${row.direction} × ${cell.region}: ${(cell.avg_score * 100).toFixed(1)}%`}
                >
                  {(cell.avg_score * 100).toFixed(0)}%
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center gap-2 mt-3">
        <span className="text-xs text-slate-500">Ср. ML Score:</span>
        <div className="w-24 h-3 rounded-full" style={{ background: 'linear-gradient(to right, #F8FAFC, #16A34A)' }} />
        <span className="text-xs text-slate-400">низкий → высокий</span>
      </div>
    </div>
  )
}
