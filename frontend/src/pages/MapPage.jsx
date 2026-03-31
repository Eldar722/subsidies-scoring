import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import { useMapRegions } from '../hooks/useMapRegions'
import { useFairness } from '../hooks/useFairness'
import { Badge } from '../components/ui/Badge'
import { Skeleton } from '../components/ui/Skeleton'
import 'leaflet/dist/leaflet.css'

function getColor(score) {
  if (score >= 0.8) return '#15803D'
  if (score >= 0.6) return '#22C55E'
  if (score >= 0.4) return '#86EFAC'
  if (score >= 0.2) return '#BBF7D0'
  return '#F0FDF4'
}

function RegionSidePanel({ region, onClose }) {
  if (!region) return null
  const isOutlier = Math.abs(region.z_score || 0) > 1
  return (
    <div className="absolute right-0 top-0 h-full w-72 bg-white border-l border-slate-200 shadow-xl z-[1000] flex flex-col">
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
        <h3 className="font-semibold text-slate-900 text-sm">{region.name}</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">×</button>
      </div>
      <div className="p-5 space-y-4 overflow-y-auto flex-1">
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-blue-50 rounded-lg p-3">
            <div className="text-xs text-blue-600 font-medium mb-1">Средний ML Score</div>
            <div className="text-xl font-bold text-blue-700">{region.avg_ml_score !== undefined ? (region.avg_ml_score * 100).toFixed(1) + '%' : '—'}</div>
          </div>
          <div className="bg-slate-50 rounded-lg p-3">
            <div className="text-xs text-slate-500 font-medium mb-1">Производителей</div>
            <div className="text-xl font-bold text-slate-800">{region.producers_count?.toLocaleString() || '—'}</div>
          </div>
          <div className="bg-purple-50 rounded-lg p-3">
            <div className="text-xs text-purple-600 font-medium mb-1">Скрытых талантов</div>
            <div className="text-xl font-bold text-purple-700">{region.hidden_talents_count ?? '—'}</div>
          </div>
          <div className={`${isOutlier ? 'bg-red-50' : 'bg-green-50'} rounded-lg p-3`}>
            <div className={`text-xs font-medium mb-1 ${isOutlier ? 'text-red-500' : 'text-green-600'}`}>Z-score</div>
            <div className={`text-xl font-bold ${isOutlier ? 'text-red-700' : 'text-green-700'}`}>{region.z_score !== undefined ? region.z_score.toFixed(2) : '—'}</div>
          </div>
        </div>
        {isOutlier && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
            ⚠ Регион показывает значимое отклонение от среднего. Требует дополнительного анализа.
          </div>
        )}
        <a href="/dashboard" className="block w-full text-center bg-blue-600 text-white text-xs font-medium py-2 rounded-lg hover:bg-blue-700 transition-colors">
          Все производители → Дашборд
        </a>
      </div>
    </div>
  )
}

export default function MapPage() {
  const { data: mapRegions, isLoading } = useMapRegions()
  const { data: fairness } = useFairness()
  const [geoData, setGeoData] = useState(null)
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
    return { fillColor: getColor(r?.avg_ml_score ?? 0), fillOpacity: 0.75, color: '#64748B', weight: 1 }
  }

  const onEachFeature = (feature, layer) => {
    const name = feature.properties.name
    const r = regionMap[name]
    const isOutlier = r && Math.abs(r.z_score || 0) > 1
    layer.bindTooltip(
      `<div style="font-family:Inter,sans-serif;font-size:12px;line-height:1.6"><strong>${name}${isOutlier ? ' ⚠' : ''}</strong><br/>Производителей: ${r?.producers_count?.toLocaleString() || '—'}<br/>Ср. балл: ${r?.avg_ml_score !== undefined ? (r.avg_ml_score * 100).toFixed(1) + '%' : '—'}</div>`,
      { sticky: true, direction: 'top', offset: [0, -4] }
    )
    layer.on({
      mouseover(e) { e.target.setStyle({ fillOpacity: 0.95, weight: 2, color: '#2563EB' }) },
      mouseout(e)  { e.target.setStyle(styleFeature(feature)) },
      click()      { setSelectedRegion(r ? { ...r, name } : { name }) },
    })
  }

  const tableRegions = fairness?.regions || []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Карта регионов</h1>
        <p className="text-sm text-slate-500 mt-1">Хороплет по среднему ML Score · Нажмите на регион для деталей</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="relative" style={{ height: 460 }}>
          {!geoData ? (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-50">
              <div className="text-center"><div className="text-3xl mb-3">🗺️</div><p className="text-slate-400 text-sm">Загрузка карты...</p></div>
            </div>
          ) : (
            <MapContainer center={[48.0, 68.0]} zoom={4} style={{ height: '100%', width: '100%' }} scrollWheelZoom={false}>
              <TileLayer attribution='© OSM' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" opacity={0.25} />
              <GeoJSON key={JSON.stringify(Object.keys(regionMap))} data={geoData} style={styleFeature} onEachFeature={onEachFeature} />
            </MapContainer>
          )}
          {selectedRegion && <RegionSidePanel region={selectedRegion} onClose={() => setSelectedRegion(null)} />}
        </div>

        {/* Legend */}
        <div className="px-5 py-3 border-t border-slate-100 flex items-center gap-4 flex-wrap">
          <span className="text-xs text-slate-500 font-medium">ML Score:</span>
          {[['#15803D','≥80%'],['#22C55E','≥60%'],['#86EFAC','≥40%'],['#BBF7D0','≥20%'],['#F0FDF4','<20%']].map(([color,label])=>(
            <div key={label} className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-sm" style={{backgroundColor:color,border:'1px solid #CBD5E1'}} />
              <span className="text-xs text-slate-500">{label}</span>
            </div>
          ))}
          <span className="text-xs text-slate-400 ml-2">⚠ = отклонение (|z| &gt; 1)</span>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Распределение по регионам</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                {['Регион','Заявок','Успешность','Ср. сумма (тг)','Ср. ML Score'].map(h=>(
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({length:6}).map((_,i)=>(
                    <tr key={i} className="border-b border-slate-100">
                      {Array.from({length:5}).map((_,j)=><td key={j} className="px-4 py-3"><Skeleton className="h-4 w-full" /></td>)}
                    </tr>
                  ))
                : tableRegions.slice().sort((a,b)=>b.total_apps-a.total_apps).map(region => {
                    const name = region['Область']
                    const mapR = regionMap[name]
                    const isOutlier = mapR && Math.abs(mapR.z_score || 0) > 1
                    return (
                      <tr key={name} onClick={()=>mapR&&setSelectedRegion({...mapR,name})}
                        className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer">
                        <td className="px-4 py-3 text-slate-700 text-sm font-medium">
                          {isOutlier && <span className="text-amber-500 mr-1">⚠</span>}{name}
                        </td>
                        <td className="px-4 py-3 text-slate-600 text-sm">{region.total_apps?.toLocaleString()}</td>
                        <td className="px-4 py-3">
                          <Badge variant={region.success_rate>=0.6?'success':region.success_rate>=0.4?'warning':'error'}>
                            {(region.success_rate*100).toFixed(1)}%
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-slate-600 text-sm">{region.avg_amount?region.avg_amount.toLocaleString('ru-RU',{maximumFractionDigits:0}):'—'}</td>
                        <td className="px-4 py-3">{region.avg_ml_score!==undefined&&<Badge variant={region.avg_ml_score>=0.7?'success':region.avg_ml_score>=0.55?'warning':'error'}>{(region.avg_ml_score*100).toFixed(1)}%</Badge>}</td>
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
