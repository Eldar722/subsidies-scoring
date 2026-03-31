const delay = (ms) => new Promise(r => setTimeout(r, ms))

const REGIONS = ['Алматы', 'Астана', 'Шымкент', 'Актобе', 'Қарағанды', 'Атырау', 'Павлодар', 'Костанай', 'Семей', 'Тараз']
const DIRECTIONS = ['Скотоводство', 'Птицеводство', 'Овцеводство', 'Свиноводство', 'Коневодство', 'Верблюдоводство', 'Пчеловодство', 'Рыбоводство', 'Кролиководство']

function seeded(seed) {
  let x = Math.sin(seed + 1) * 10000
  return x - Math.floor(x)
}

const MOCK_PRODUCERS = Array.from({ length: 100 }, (_, i) => ({
  producer_id: `P${String(1000 + i).padStart(4, '0')}`,
  region: REGIONS[i % REGIONS.length],
  direction: DIRECTIONS[i % DIRECTIONS.length],
  ml_score: parseFloat((0.42 + seeded(i * 7) * 0.55).toFixed(3)),
  ml_rank: i + 1,
  fcfs_rank: Math.floor(seeded(i * 13) * 100) + 1,
  delta: Math.floor(seeded(i * 17) * 40) - 20,
  hidden_talent: i % 7 === 0,
  at_risk: i % 11 === 0,
  completion_rate: parseFloat((0.5 + seeded(i * 3) * 0.5).toFixed(3)),
  total_applications: Math.floor(seeded(i * 5) * 50) + 5,
}))

export const getHealth = async () => {
  await delay(200)
  return { status: 'ok', db: 'connected', model: 'loaded' }
}

export const getStats = async () => {
  await delay(300)
  return {
    total_producers: 15008,
    shortlisted_count: 20,
    hidden_talents_count: 7,
    avg_ml_score: 0.73,
  }
}

export const getShortlist = async (topN = 20) => {
  await delay(400)
  const items = MOCK_PRODUCERS.slice(0, topN).sort((a, b) => b.ml_score - a.ml_score)
  return {
    shortlist: items,
    total_producers: topN,
    hidden_talents_count: items.filter(p => p.hidden_talent).length,
    avg_ml_score: parseFloat((items.reduce((s, p) => s + p.ml_score, 0) / items.length).toFixed(3)),
  }
}

export const getProducers = async (params = {}) => {
  await delay(400)
  let items = [...MOCK_PRODUCERS]
  if (params.region) items = items.filter(p => p.region === params.region)
  if (params.direction) items = items.filter(p => p.direction === params.direction)
  if (params.min_score) items = items.filter(p => p.ml_score >= parseFloat(params.min_score))
  if (params.hidden_only) items = items.filter(p => p.hidden_talent)
  return {
    total: items.length,
    page: params.page || 1,
    per_page: 20,
    items: items.slice(0, 20),
  }
}

export const getProducerDetail = async (id) => {
  await delay(350)
  const base = MOCK_PRODUCERS.find(p => p.producer_id === id) || MOCK_PRODUCERS[0]
  return {
    ...base,
    shap_values: [
      { feature: 'completion_rate', feature_label: 'Исполнение заявок', shap_value: 0.18, raw_value: 0.92 },
      { feature: 'approval_rate', feature_label: 'Одобряемость', shap_value: 0.12, raw_value: 0.85 },
      { feature: 'apps_per_month', feature_label: 'Активность подачи', shap_value: 0.09, raw_value: 14 },
      { feature: 'diversity', feature_label: 'Диверсификация', shap_value: -0.07, raw_value: 0.3 },
      { feature: 'working_hours', feature_label: 'Рабочие часы', shap_value: 0.04, raw_value: 220 },
      { feature: 'region_score', feature_label: 'Региональный фактор', shap_value: -0.03, raw_value: 0.61 },
    ],
    history: Array.from({ length: 14 }, (_, i) => {
      const date = new Date(2025, 0 + i, 1)
      return {
        month: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`,
        label: date.toLocaleString('ru-RU', { month: 'short', year: '2-digit' }),
        applications: Math.floor(seeded((base.producer_id.charCodeAt(1) || 1) * i + 1) * 5) + 1,
        amount: Math.floor(seeded((base.producer_id.charCodeAt(2) || 2) * i + 2) * 500000) + 50000,
      }
    }),
    stats: {
      total_applications: base.total_applications || 47,
      completed: Math.floor((base.total_applications || 47) * (base.completion_rate || 0.85)),
      directions_count: 3,
      active_months: 11,
    },
  }
}

export const getProducerAdvice = async (_id) => {
  await delay(600)
  return {
    score_explanation: 'Производитель показывает высокую исполнительность (92%) — это главный фактор роста балла. Одобряемость заявок выше среднего по региону на 18 п.п. Регулярная активность подачи (14 заявок/мес) подтверждает устойчивость бизнеса.',
    baseline_injustice: 'По системе FCFS этот производитель занял бы #18 из-за позднего времени подачи. ML-модель исправляет это смещение, учитывая реальные результаты, и ставит производителя на #3 — справедливую позицию.',
    recommendations: [
      { text: 'Подавать заявки в первые 3 дня периода для повышения FCFS-ранга', impact: 12 },
      { text: 'Расширить диверсификацию до 2+ направлений животноводства', impact: 8 },
    ],
  }
}

export const getFairness = async () => {
  await delay(500)
  return {
    gini_coefficient: 0.34,
    gini_interpretation: 'Умеренное неравенство',
    lorenz_curve: Array.from({ length: 21 }, (_, i) => ({
      population: i / 20,
      cumulative_share: Math.pow(i / 20, 1.65),
    })),
    kruskal_wallis: {
      by_region: { statistic: 24.3, p_value: 0.08, significant: false },
      by_direction: { statistic: 31.1, p_value: 0.02, significant: true },
    },
    region_zscores: [
      { region: 'Алматы', z_score: 1.4, avg_score: 0.76, is_outlier: true },
      { region: 'Астана', z_score: 0.3, avg_score: 0.69, is_outlier: false },
      { region: 'Шымкент', z_score: -0.8, avg_score: 0.61, is_outlier: false },
      { region: 'Актобе', z_score: -1.2, avg_score: 0.57, is_outlier: true },
      { region: 'Қарағанды', z_score: 0.6, avg_score: 0.71, is_outlier: false },
      { region: 'Атырау', z_score: 1.1, avg_score: 0.74, is_outlier: true },
      { region: 'Павлодар', z_score: -0.4, avg_score: 0.65, is_outlier: false },
      { region: 'Костанай', z_score: 0.2, avg_score: 0.68, is_outlier: false },
      { region: 'Семей', z_score: -1.5, avg_score: 0.54, is_outlier: true },
      { region: 'Тараз', z_score: 0.7, avg_score: 0.72, is_outlier: false },
    ],
    heatmap: DIRECTIONS.slice(0, 5).map(dir => ({
      direction: dir,
      data: REGIONS.slice(0, 6).map(reg => ({
        region: reg,
        avg_score: parseFloat((0.45 + Math.random() * 0.45).toFixed(2)),
      })),
    })),
    regions: REGIONS.map((name, i) => ({
      'Область': name,
      total_apps: Math.floor(1000 + seeded(i * 11) * 5000),
      success_rate: parseFloat((0.45 + seeded(i * 7) * 0.4).toFixed(3)),
      avg_amount: Math.floor(50000 + seeded(i * 13) * 200000),
      avg_ml_score: parseFloat((0.55 + seeded(i * 3) * 0.35).toFixed(3)),
    })),
  }
}

export const getMapRegions = async () => {
  await delay(400)
  return REGIONS.map((name, i) => ({
    region_id: `KZ-${i}`,
    name,
    avg_ml_score: parseFloat((0.55 + seeded(i * 3) * 0.35).toFixed(3)),
    producers_count: Math.floor(500 + seeded(i * 11) * 2000),
    hidden_talents_count: Math.floor(seeded(i * 7) * 20),
    z_score: parseFloat(((seeded(i * 5) * 4) - 2).toFixed(2)),
    is_outlier: Math.abs((seeded(i * 5) * 4) - 2) > 1,
  }))
}

export const runSimulation = async (weights, topN = 20) => {
  await delay(600)
  const scored = MOCK_PRODUCERS.map(p => {
    const w = weights || {}
    const score =
      (p.ml_score * (w.completion_rate || 35) / 100) +
      (p.completion_rate * (w.approval_rate || 25) / 100) +
      (seeded(p.ml_rank) * (w.diversification || 20) / 100) +
      (seeded(p.fcfs_rank) * (w.activity || 10) / 100) +
      (seeded(p.delta || 0) * (w.working_hours || 10) / 100)
    return { ...p, sim_score: score }
  }).sort((a, b) => b.sim_score - a.sim_score)

  const newShortlist = scored.slice(0, topN)
  const baseIds = new Set(MOCK_PRODUCERS.slice(0, topN).map(p => p.producer_id))
  const newIds = new Set(newShortlist.map(p => p.producer_id))

  return {
    shortlist: newShortlist,
    entered: newShortlist.filter(p => !baseIds.has(p.producer_id)),
    left: MOCK_PRODUCERS.slice(0, topN).filter(p => !newIds.has(p.producer_id)),
    hidden_talent_count: newShortlist.filter(p => p.hidden_talent).length,
    weights_used: weights,
  }
}

export const getMetrics = async () => {
  await delay(300)
  return {
    roc_auc: 0.782,
    best_f1: 0.791,
    precision: 0.813,
    recall: 0.771,
    model_version: '1.0.0',
    trained_at: '2025-03-15T10:00:00Z',
    train_size: 32723,
    val_size: 3928,
  }
}

export const runPipeline = async () => {
  await delay(2000)
  return { status: 'success', message: 'Пайплайн выполнен успешно', processed: 15008, duration_seconds: 47 }
}
