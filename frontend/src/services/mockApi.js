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
      {
        problem: 'Низкая диверсификация направлений',
        cause: 'Производитель работает только в одном виде животноводства, что снижает балл диверсификации на -0.07 SHAP',
        action: 'Добавить второе направление (например, птицеводство) — это увеличит балл диверсификации',
        impact: 22,
      },
      {
        problem: 'Заявки подаются в конце периода',
        cause: 'Более 60% заявок поданы после 15-го числа месяца, что ухудшает FCFS-ранг',
        action: 'Подавать заявки в первые 3–5 дней открытия периода для улучшения FCFS-позиции',
        impact: 12,
      },
      {
        problem: 'Региональный фактор снижает балл',
        cause: 'Регион имеет z-score = -0.8, что негативно влияет на предсказание модели',
        action: 'Добиться увеличения числа одобренных заявок в регионе — это повысит региональный коэффициент',
        impact: 8,
      },
    ],
  }
}

export const getFairness = async () => {
  await delay(500)

  // Flat heatmap: [{region, direction, avg_score}]
  const heatmap = []
  DIRECTIONS.slice(0, 6).forEach(dir => {
    REGIONS.slice(0, 8).forEach(reg => {
      heatmap.push({
        region: reg,
        direction: dir,
        avg_score: parseFloat((0.45 + seeded((dir.charCodeAt(0) * reg.charCodeAt(0)) % 99) * 0.45).toFixed(2)),
      })
    })
  })

  const regional_stats = REGIONS.map((name, i) => ({
    region: name,
    total_apps: Math.floor(1000 + seeded(i * 11) * 5000),
    success_rate: parseFloat((0.45 + seeded(i * 7) * 0.4).toFixed(3)),
    avg_amount: Math.floor(50000 + seeded(i * 13) * 200000),
    total_amount: Math.floor(5_000_000 + seeded(i * 17) * 50_000_000),
    avg_ml_score: parseFloat((0.55 + seeded(i * 3) * 0.35).toFixed(3)),
  }))

  return {
    gini_coefficient: 0.34,
    gini_coefficient_amounts: 0.41,
    gini_interpretation: 'Умеренное неравенство',
    lorenz_curve: Array.from({ length: 21 }, (_, i) => ({
      population: i / 20,
      cumulative_share: Math.pow(i / 20, 1.65),
    })),
    kruskal_wallis: {
      by_region:    { statistic: 24.3, p_value: 0.08, significant: false },
      by_direction: { statistic: 31.1, p_value: 0.02, significant: true },
    },
    region_zscores: [
      { region: 'Алматы',    z_score:  1.4, avg_score: 0.76, is_outlier: true  },
      { region: 'Астана',    z_score:  0.3, avg_score: 0.69, is_outlier: false },
      { region: 'Шымкент',   z_score: -0.8, avg_score: 0.61, is_outlier: false },
      { region: 'Актобе',    z_score: -1.2, avg_score: 0.57, is_outlier: true  },
      { region: 'Қарағанды', z_score:  0.6, avg_score: 0.71, is_outlier: false },
      { region: 'Атырау',    z_score:  1.1, avg_score: 0.74, is_outlier: true  },
      { region: 'Павлодар',  z_score: -0.4, avg_score: 0.65, is_outlier: false },
      { region: 'Костанай',  z_score:  0.2, avg_score: 0.68, is_outlier: false },
      { region: 'Семей',     z_score: -1.5, avg_score: 0.54, is_outlier: true  },
      { region: 'Тараз',     z_score:  0.7, avg_score: 0.72, is_outlier: false },
    ],
    heatmap,
    regional_stats,
    // legacy key kept for backward compatibility
    regions: regional_stats,
  }
}

export const getMapRegions = async () => {
  await delay(400)
  return REGIONS.map((name, i) => ({
    region_id: `KZ-${i}`,
    region: name,
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
  const newIds  = new Set(newShortlist.map(p => p.producer_id))

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
    roc_auc:    0.782,
    best_f1:    0.791,
    precision:  0.813,
    recall:     0.771,
    cv_auc_mean: 0.8499,
    model_version: '1.0.0',
    trained_at: '2025-03-15T10:00:00Z',
    train_size: 32723,
    val_size:   3928,
  }
}

export const runPipeline = async () => {
  await delay(2000)
  return { status: 'success', message: 'Пайплайн выполнен успешно', processed: 15008, duration_seconds: 47 }
}

// ── Feature 1: Drift Monitor ───────────────────────────────────

export const getDriftStatus = async () => {
  await delay(400)
  return {
    status: 'warning',
    psi_score: 0.18,
    low_confidence_pct: 23.4,
    drifted_features: ['avg_amount', 'apps_per_month', 'working_hours'],
    recommendation: 'Рекомендуется переобучить модель на данных 2026',
    last_train_date: '2025-03-15',
    checked_at: new Date().toISOString(),
  }
}

export const getProducerConfidence = async (_id) => {
  await delay(300)
  const conf = 0.45 + seeded(parseInt(_id?.slice(-2) || '50', 10)) * 0.5
  return {
    confidence_score: parseFloat(conf.toFixed(3)),
    is_low_confidence: conf < 0.4,
    anomalous_features: conf < 0.5 ? ['avg_amount', 'apps_per_month'] : [],
    explanation: conf < 0.4
      ? 'Входные данные производителя значительно отличаются от обучающей выборки. Рекомендуется ручная проверка.'
      : 'Данные производителя соответствуют обучающей выборке. Предсказание надёжно.',
  }
}

// ── Feature 2: Fair Reranking ──────────────────────────────────

export const getFairShortlist = async (params = {}) => {
  await delay(700)
  const topN = params.top_n || 20
  const shortlist = MOCK_PRODUCERS.slice(0, topN)
    .sort((a, b) => b.ml_score - a.ml_score)
  const swaps = [
    { removed: MOCK_PRODUCERS[3].producer_id, added: MOCK_PRODUCERS[22].producer_id, reason: 'Алматы перепредставлена (+3 vs ожидаемых)', group: 'Алматы' },
    { removed: MOCK_PRODUCERS[7].producer_id, added: MOCK_PRODUCERS[31].producer_id, reason: 'Семей недопредставлена (-2 vs ожидаемых)', group: 'Семей' },
  ]
  return {
    shortlist,
    swaps,
    score_drop_pct: 7.9,
    representation_gap_before: 1.54,
    representation_gap_after: 0.42,
    hidden_talent_count: shortlist.filter(p => p.hidden_talent).length,
  }
}

// ── Feature 3: Counterfactual Explanations ────────────────────

export const getCounterfactual = async (_id) => {
  await delay(500)
  return {
    current_score: 0.169,
    target_score: 0.182,
    threshold: 0.182,
    achievable: true,
    changes: [
      {
        feature: 'submission_month',
        current: 'Август',
        recommended: 'Июль',
        impact_pct: 1.1,
        explanation: 'Заявки в июле имеют на 12% выше шанс одобрения исторически',
      },
      {
        feature: 'avg_amount',
        current: '45 000 ₸',
        recommended: '52 000 ₸',
        impact_pct: 0.8,
        explanation: 'Суммы ближе к среднему по региону повышают вероятность исполнения',
      },
    ],
    fixed_features: ['region', 'direction', 'producer_id'],
  }
}

// ── Analytics ─────────────────────────────────────────────────

export const getSubsidyEffectiveness = async () => {
  await delay(500)
  const producers = MOCK_PRODUCERS.slice(0, 40).map((p, i) => ({
    producer_id: p.producer_id,
    region: p.region,
    effectiveness_score: Math.round(40 + seeded(i * 3 + 7) * 55),
    improved: seeded(i * 11) > 0.45,
    needs_review: seeded(i * 13) < 0.25,
    deltas: {
      completion_rate: parseFloat((seeded(i * 7) * 0.4 - 0.1).toFixed(3)),
      avg_amount: Math.round((seeded(i * 9) - 0.4) * 80000),
      activity: parseFloat((seeded(i * 5) * 3 - 0.5).toFixed(1)),
    },
  }))
  const improved = producers.filter(p => p.improved)
  const needsReview = producers.filter(p => p.needs_review)
  return {
    total_analyzed: producers.length,
    improved_count: improved.length,
    needs_review_count: needsReview.length,
    avg_effectiveness_score: Math.round(producers.reduce((s, p) => s + p.effectiveness_score, 0) / producers.length),
    producers,
  }
}

export const getRedFlags = async () => {
  await delay(400)
  return {
    total_flags: 4,
    high_risk:   1,
    medium_risk: 2,
    flags: [
      {
        title: 'Концентрация заявок в конце периода',
        description: 'В регионах Алматы и Атырау 78% заявок поданы в последние 3 дня периода. Возможна координация или массовая подача через посредников.',
        risk_level: 'high',
        affected_count: 312,
        producer_ids: MOCK_PRODUCERS.slice(0, 8).map(p => p.producer_id),
      },
      {
        title: 'Региональное смещение по Жамбылской области',
        description: 'Z-score региона составляет -2.09 — систематически более низкие баллы по сравнению со средним. Рекомендуется проверка методологии оценки для данного региона.',
        risk_level: 'medium',
        affected_count: 147,
        producer_ids: MOCK_PRODUCERS.slice(8, 14).map(p => p.producer_id),
      },
      {
        title: 'Аномальный рост суммы заявок',
        description: 'У 23 производителей сумма заявки превышает исторический максимум в 3+ раза без видимых изменений в профиле деятельности.',
        risk_level: 'medium',
        affected_count: 23,
        producer_ids: MOCK_PRODUCERS.slice(14, 20).map(p => p.producer_id),
      },
      {
        title: 'Низкая диверсификация в шортлисте',
        description: 'Топ-20 шортлиста содержит 85% производителей из скотоводства. Справедливое представление остальных 8 направлений не обеспечено.',
        risk_level: 'low',
        affected_count: 0,
        producer_ids: [],
      },
    ],
  }
}
