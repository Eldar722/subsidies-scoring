import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import { useMapRegions } from '../hooks/useMapRegions'
import { useFairness } from '../hooks/useFairness'
import { Badge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import { CardHeader } from '../components/ui/Card'
import { X, Warning } from '@phosphor-icons/react'
import 'leaflet/dist/leaflet.css'

function getColor(score) {
  if (score >= 0.8) return '#15803D'
  if (score >= 0.6) return '#22C55E'
  if (score >= 0.4) return '#86EFAC'
  if (score >= 0.2) return '#BBF7D0'
  return '#F0FDF4'
}

function StatMini({ label, value, color = 'text-slate-800' }) {
  return (
    <div className="bg-slate-50 rounded-lg p-3">
      <div className="text-[10px] text-slate-400 font-medium mb-1 uppercase tracking-wide">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
    </div>
  )
}

function RegionSidePanel({ region, onClose }) {
  if (!region) return null
  const isOutlier = Math.abs(region.z_score || 0) > 1
  return (
    <div className="absolute right-0 top-0 h-full w-72 bg-white border-l border-slate-100 shadow-xl z-[1000] flex flex-col">
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
        <div>
          <h3 className="font-semibold text-slate-900 text-sm leading-snug">{region.name}</h3>
          {isOutlier && <p className="text-[10px] text-amber-600 font-medium mt-0.5">⚠ Значимое отклонение</p>}
        </div>
        <button
          onClick={onClose}
          className="w-7 h-7 rounded-md flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
        >
          <X size={14} />
        </button>
      </div>

      <div className="p-4 space-y-3 overflow-y-auto flex-1">
        <div className="grid grid-cols-2 gap-2">
          <StatMini
            label="Средний ML Score"
            value={region.avg_ml_score !== undefined ? (region.avg_ml_score * 100).toFixed(1) + '%' : '—'}
            color="text-blue-700"
          />
          <StatMini
            label="Производителей"
            value={region.producers_count?.toLocaleString() || region.producer_count?.toLocaleString() || '—'}
          />
          <StatMini
            label="Скрытых талантов"
            value={region.hidden_talents_count ?? region.hidden_talent_count ?? '—'}
            color="text-purple-700"
          />
          <StatMini
            label="Z-score"
            value={region.z_score !== undefined ? region.z_score.toFixed(2) : '—'}
            color={isOutlier ? 'text-red-600' : 'text-green-700'}
          />
        </div>

        {isOutlier && (
          <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3">
            <Warning size={14} className="text-amber-500 mt-0.5 flex-shrink-0" weight="fill" />
            <p className="text-xs text-amber-700 leading-relaxed">
              Регион показывает значимое отклонение от среднего. Требует дополнительного анализа.
            </p>
          </div>
        )}

        <a
          href="/dashboard"
          className="flex items-center justify-center gap-1.5 w-full bg-blue-600 text-white text-xs font-medium py-2.5 rounded-lg hover:bg-blue-700 transition-colors"
        >
          Все производители → Дашборд
        </a>
      </div>
    </div>
  )
}

export default function MapPage() {
  const { data: mapRegions, isLoading } = useMapRegions()
  const { data: fairness } = useFairness()
  const [geoData, setGeoData]             = useState(null)
  const [selectedRegion, setSelectedRegion] = useState(null)

  useEffect(() => {
    fetch('/kz-regions.geojson').then(r => r.json()).then(setGeoData).catch(console.error)
  }, [])

  const regionMap = {}
  if (mapRegions) mapRegions.forEach(r => { regionMap[r.name] = r })
  const fairnessRegions = fairness?.regions || []
  fairnessRegions.forEach(r => {
    const k = r['Область']
    if (!regionMap[k]) regionMap[k] = { name: k, avg_ml_score: r.avg_ml_score || 0.65, producers_count: r.total_apps, hidden_talents_count: 0, z_score: 0 }
  })

  const styleFeature = (feature) => {
    const r = regionMap[feature.properties.name]
    return { fillColor: getColor(r?.avg_ml_score ?? 0), fillOpacity: 0.75, color: '#CBD5E1', weight: 1 }
  }

  const onEachFeature = (feature, layer) => {
    const name = feature.properties.name
    const r = regionMap[name]
    const isOutlier = r && Math.abs(r.z_score || 0) > 1
    layer.bindTooltip(
      `<div style="font-family:Inter,sans-serif;font-size:12px;line-height:1.7;padding:2px 0">
        <strong style="font-size:13px">${name}${isOutlier ? ' ⚠' : ''}</strong><br/>
        Производителей: ${r?.producer_count?.toLocaleString() || r?.producers_count?.toLocaleString() || '—'}<br/>
        Ср. балл: ${r?.avg_ml_score !== undefined ? (r.avg_ml_score * 100).toFixed(1) + '%' : '—'}<br/>
        Скрытых талантов: ${r?.hidden_talent_count ?? r?.hidden_talents_count ?? '—'}
      </div>`,
      { sticky: true, direction: 'top', offset: [0, -6] }
    )
    layer.on({
      mouseover(e) { e.target.setStyle({ fillOpacity: 0.92, weight: 2, color: '#2563EB' }) },
      mouseout(e)  { e.target.setStyle(styleFeature(feature)) },
      click()      { setSelectedRegion(r ? { ...r, name } : { name }) },
    })
  }

  const tableRegions = fairness?.regions || []

  return (
    <div className="space-y-5 max-w-full">
      {/* Map card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <CardHeader
          title="Карта регионов Казахстана"
          subtitle="Хороплет по среднему ML Score · Нажмите на регион для деталей"
        />
        <div className="relative" style={{ height: 460 }}>
          {!geoData ? (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-50">
              <div className="text-center">
                <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center mx-auto mb-3">
                  <span className="text-2xl">🗺️</span>
                </div>
                <p className="text-slate-400 text-sm">Загрузка карты...</p>
              </div>
            </div>
          ) : (
            <MapContainer center={[48.0, 68.0]} zoom={4} style={{ height: '100%', width: '100%' }} scrollWheelZoom={false}>
              <TileLayer attribution='© OSM' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" opacity={0.2} />
              <GeoJSON
                key={JSON.stringify(Object.keys(regionMap))}
                data={geoData}
                style={styleFeature}
                onEachFeature={onEachFeature}
              />
            </MapContainer>
          )}
          {selectedRegion && <RegionSidePanel region={selectedRegion} onClose={() => setSelectedRegion(null)} />}
        </div>

        {/* Legend */}
        <div className="px-5 py-3 border-t border-slate-100 flex items-center gap-5 flex-wrap bg-slate-50/50">
          <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">ML Score:</span>
          <div className="flex items-center gap-3 flex-wrap">
            {[['#15803D','≥80%'],['#22C55E','≥60%'],['#86EFAC','≥40%'],['#BBF7D0','≥20%'],['#F0FDF4','<20%']].map(([color, label]) => (
              <div key={label} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm border border-slate-200" style={{ backgroundColor: color }} />
                <span className="text-xs text-slate-500">{label}</span>
              </div>
            ))}
          </div>
          <span className="text-xs text-slate-400 ml-auto">⚠ = отклонение (|z| &gt; 1)</span>
        </div>
      </div>

      {/* Table card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <CardHeader title="Распределение по регионам" subtitle="Сортировка по количеству заявок" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                {['Регион', 'Заявок', 'Успешность', 'Ср. сумма (₸)', 'Ср. ML Score'].map(h => (
                  <th key={h} className="text-left px-4 py-2.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 5 }).map((_, j) => (
                        <td key={j} className="px-4 py-3.5"><Skeleton className="h-4 w-full" /></td>
                      ))}
                    </tr>
                  ))
                : tableRegions.slice().sort((a, b) => b.total_apps - a.total_apps).map(region => {
                    const name  = region['Область']
                    const mapR  = regionMap[name]
                    const isOut = mapR && Math.abs(mapR.z_score || 0) > 1
                    return (
                      <tr
                        key={name}
                        onClick={() => mapR && setSelectedRegion({ ...mapR, name })}
                        className="hover:bg-slate-50 transition-colors cursor-pointer"
                      >
                        <td className="px-4 py-3.5 text-slate-700 text-sm font-medium">
                          {isOut && <Warning size={12} className="text-amber-400 inline mr-1.5" weight="fill" />}
                          {name}
                        </td>
                        <td className="px-4 py-3.5 text-slate-500 text-xs tabular-nums">{region.total_apps?.toLocaleString()}</td>
                        <td className="px-4 py-3.5">
                          <Badge variant={region.success_rate >= 0.6 ? 'success' : region.success_rate >= 0.4 ? 'warning' : 'error'}>
                            {(region.success_rate * 100).toFixed(1)}%
                          </Badge>
                        </td>
                        <td className="px-4 py-3.5 text-slate-500 text-xs tabular-nums">
                          {region.avg_amount ? region.avg_amount.toLocaleString('ru-RU', { maximumFractionDigits: 0 }) : '—'}
                        </td>
                        <td className="px-4 py-3.5">
                          {region.avg_ml_score !== undefined && (
                            <Badge variant={region.avg_ml_score >= 0.7 ? 'success' : region.avg_ml_score >= 0.55 ? 'warning' : 'error'}>
                              {(region.avg_ml_score * 100).toFixed(1)}%
                            </Badge>
                          )}
                        </td>
                      </tr>
                    )
                  })
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
