# План разработки + промпты для Claude Code
## 🟣 Фронтендер — React UI + интеграция + Vercel
## AI для справедливых субсидий — Decentrathon 5.0

> Твоя зона: `frontend/` целиком
> Запускай `claude` из папки `D:\Decenthrathon\subsidies-scoring\frontend`
> С Дня 1 работаешь на моках — НЕ ждёшь бэкенд.

Вот сайт с которого нужно брать ui-компоненты для дизайна:
https://ui.shadcn.com

На выбор даны две библиотеки иконок, выбери для дизайна
https://heroicons.com
https://phosphoricons.com/

Ориентируйся на дизайн и UX следующих продуктов: Vercel, Linear, Stripe, Supabase.

---

## ДЕНЬ 1 — 27 марта | Инициализация проекта

### 🎯 Цель дня: Vite стартует, роутинг работает, Sidebar рендерится
### ✅ Критерий готовности: `http://localhost:5173/dashboard` открывается без ошибок в консоли

---

### ПРОМПТ 1.1 — Инициализация проекта

```
Ты настраиваешь React-проект с нуля. Выполни шаги последовательно и после каждого шага сообщай статус.

ШАГ 1. Создай Vite + React 18 проект (если папка frontend уже существует — работай внутри неё, не пересоздавай):
npm create vite@latest . -- --template react
npm install

ШАГ 2. Установи зависимости одной командой:
npm install react-router-dom@6 axios @tanstack/react-query@5 recharts framer-motion @headlessui/react react-leaflet leaflet @supabase/supabase-js

ШАГ 3. Создай структуру папок (mkdir -p для каждой):
src/pages/
src/components/ui/
src/components/charts/
src/components/layout/
src/components/features/
src/hooks/
src/services/
src/styles/

ШАГ 4. Создай файлы-заглушки для всех страниц.
Каждый файл src/pages/XxxPage.jsx должен содержать:
export default function XxxPage() {
  return <div className="p-6"><h1>XxxPage</h1></div>
}
Создай: DashboardPage, ProducerPage, SimulatorPage, FairnessPage, MapPage.

ШАГ 5. Настрой src/App.jsx с React Router v6:
- Импортируй BrowserRouter, Routes, Route, Navigate
- Маршруты:
  /dashboard → DashboardPage
  /producer/:id → ProducerPage
  /simulator → SimulatorPage
  /fairness → FairnessPage
  /map → MapPage
  / → <Navigate to="/dashboard" replace />
- Оберни всё в <BrowserRouter>

ШАГ 6. Создай src/main.jsx — стандартный Vite + React entrypoint.

ШАГ 7. Запусти npm run dev и подтверди что сервер стартовал на порту 5173.

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: переход на /dashboard показывает текст "DashboardPage", остальные роуты аналогично.
```

---

### ПРОМПТ 1.2 — Дизайн-система

```
Настрой дизайн-систему проекта. Выполни точно в таком порядке.

ШАГ 1. В index.html внутри <head> добавь строго перед закрывающим тегом:
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
ВАЖНО: @import в CSS файлах не использовать — PostCSS выдаст ошибку.

ШАГ 2. Установи Tailwind CSS:
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

ШАГ 3. В tailwind.config.js замени содержимое на:
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#2563EB',
        surface: '#FFFFFF',
        hidden: '#7C3AED',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

ШАГ 4. Создай src/styles/globals.css с точно таким содержимым:
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --color-white: #DBE2EF;
  --color-bg: #F9F7F7;
  --color-surface: #3F72AF;
  --color-border: #112D4E;
  --color-text: #0F172A;
  --color-success: #16A34A;
  --color-warning: #F59E0B;
  --color-error: #DC2626;
  --color-hidden: #7C3AED;
}

body {
  font-family: 'Inter', sans-serif;
  background-color: #F9F7F7;
  color: #0F172A;
}

ШАГ 5. В src/main.jsx добавь импорт:
import './styles/globals.css'

ШАГ 6. Перезапусти dev-сервер. Проверь что шрифт Inter загружается (вкладка Network в DevTools → Fonts).

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: страница использует Inter, фон #F9F7F7.
```

---

### ПРОМПТ 1.3 — Layout (Sidebar + Header)

```
Создай компоненты layout. Каждый файл создавай отдельно и полностью.

ФАЙЛ 1: src/components/layout/Sidebar.jsx

Требования:
- position: fixed, left: 0, top: 0, height: 100vh, width: 240px
- background: white, border-right: 1px solid #E2E8F0
- z-index: 40

Структура JSX:
<aside> (fixed w-60 h-screen bg-white border-r border-slate-200 flex flex-col z-40)
  <div> (лого: p-6 border-b border-slate-200)
    <span> "⚡ AI Субсидии" (text-lg font-bold text-blue-600)
  <nav> (flex-1 p-4 space-y-1)
    5 NavLink компонентов (см. ниже)

Пункты меню — массив объектов:
[
  { icon: '📊', label: 'Дашборд', to: '/dashboard' },
  { icon: '🎮', label: 'Симулятор', to: '/simulator' },
  { icon: '⚖️', label: 'Справедливость', to: '/fairness' },
  { icon: '🗺️', label: 'Карта', to: '/map' },
]

Каждый NavLink:
- базовые классы: flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150
- неактивный: text-slate-600 hover:bg-slate-100 hover:text-slate-900
- активный (className функция NavLink): bg-blue-50 text-blue-700 border-r-2 border-blue-600

ФАЙЛ 2: src/components/layout/Header.jsx

Требования:
- sticky top-0, height: 64px, z-index: 30
- background: white, border-bottom: 1px solid #E2E8F0
- Использует useLocation() для определения заголовка страницы

Логика заголовка:
const titles = {
  '/dashboard': 'Дашборд',
  '/simulator': 'Симулятор',
  '/fairness': 'Справедливость',
  '/map': 'Карта регионов',
}
Если путь начинается с /producer/ → 'Профиль производителя'

Структура JSX:
<header> (sticky top-0 h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 z-30)
  <h1> (text-lg font-semibold text-slate-900) — название страницы
  <button> — "▶ Запустить пайплайн" (bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700)
  onClick пока console.log('pipeline run')

ФАЙЛ 3: src/components/layout/Layout.jsx

import Sidebar from './Sidebar'
import Header from './Header'

export default function Layout({ children }) {
  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 ml-60 min-h-screen flex flex-col">
        <Header />
        <main className="flex-1 p-6 bg-slate-50">
          {children}
        </main>
      </div>
    </div>
  )
}

ФАЙЛ 4: обнови src/App.jsx — оберни все <Route element={}> в <Layout>:
<Route path="/dashboard" element={<Layout><DashboardPage /></Layout>} />
(и так для каждой страницы)

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: все страницы показывают Sidebar слева и Header сверху. Активный пункт меню подсвечивается синим.
```

---

### ПРОМПТ 1.4 — Mock API + API сервис

```
Создай два сервисных файла: mockApi.js (для разработки) и api.js (для продакшна).

ФАЙЛ 1: src/services/mockApi.js

Все функции возвращают Promise.resolve(data) с задержкой 300-800ms для реалистичности:
const delay = (ms) => new Promise(r => setTimeout(r, ms))

Реализуй с точно такими полями:

getProducers(params = {}) — возвращает:
{
  total: 15008,
  page: params.page || 1,
  per_page: 20,
  items: Array.from({ length: 20 }, (_, i) => ({
    producer_id: `P${1000 + i}`,
    region: ['Алматы', 'Астана', 'Шымкент', 'Актобе', 'Қарағанды'][i % 5],
    direction: ['Растениеводство', 'Животноводство', 'Переработка', 'Аквакультура'][i % 4],
    ml_score: parseFloat((0.45 + Math.random() * 0.5).toFixed(2)),
    ml_rank: i + 1,
    fcfs_rank: Math.floor(Math.random() * 50) + 1,
    delta: Math.floor(Math.random() * 20) - 10,
    hidden_talent: i % 7 === 0,
    at_risk: i % 11 === 0,
  }))
}

getShortlist(topN = 20) — возвращает:
{
  total_producers: topN,
  hidden_talents_count: 7,
  avg_ml_score: 0.73,
  items: [] // те же поля что у getProducers items
}

getProducerDetail(id) — возвращает:
{
  producer_id: id,
  region: 'Алматы',
  direction: 'Животноводство',
  ml_score: 0.81,
  ml_rank: 3,
  fcfs_rank: 18,
  delta: 15,
  hidden_talent: true,
  at_risk: false,
  shap_values: [
    { feature: 'completion_rate', feature_label: 'Исполнение заявок', shap_value: 0.18, raw_value: 0.92 },
    { feature: 'approval_rate', feature_label: 'Одобряемость', shap_value: 0.12, raw_value: 0.85 },
    { feature: 'diversity', feature_label: 'Диверсификация', shap_value: -0.07, raw_value: 0.3 },
    { feature: 'activity', feature_label: 'Активность подачи', shap_value: 0.09, raw_value: 14 },
    { feature: 'working_hours', feature_label: 'Рабочие часы', shap_value: 0.04, raw_value: 220 },
  ],
  history: Array.from({ length: 12 }, (_, i) => ({
    month: `2024-${String(i + 1).padStart(2, '0')}`,
    applications: Math.floor(Math.random() * 5) + 1,
  })),
  stats: { total_applications: 47, completed: 41, directions_count: 3, active_months: 11 }
}

getProducerAdvice(id) — возвращает:
{
  score_explanation: 'Производитель показывает высокую исполнительность (92%) — это главный фактор роста балла. Одобряемость заявок выше среднего по региону.',
  baseline_injustice: 'По системе FCFS этот производитель занял бы #18 из-за позднего времени подачи. ML-модель исправляет это смещение и ставит его на #3.',
  recommendations: [
    { text: 'Подавать заявки в первые 3 дня периода для повышения FCFS-ранга', impact: 12 },
    { text: 'Расширить диверсификацию до 2+ направлений', impact: 8 },
  ]
}

getFairness() — возвращает:
{
  gini_scores: 0.34,
  gini_amounts: 0.41,
  lorenz_scores: Array.from({ length: 11 }, (_, i) => ({ x: i / 10, y: Math.pow(i / 10, 1.6) })),
  kw_regions: { H: 24.3, p_value: 0.08 },
  kw_directions: { H: 31.1, p_value: 0.02 },
  region_zscores: [
    { region: 'Алматы', z_score: 1.4, is_outlier: true },
    { region: 'Астана', z_score: 0.3, is_outlier: false },
    { region: 'Шымкент', z_score: -0.8, is_outlier: false },
    { region: 'Актобе', z_score: -1.2, is_outlier: true },
    { region: 'Қарағанды', z_score: 0.6, is_outlier: false },
  ],
  heatmap: [] // заглушка, заполним в День 6
}

getMapRegions() — возвращает массив 17 объектов:
[
  { region_id: 'KZ-ALA', name: 'Алматы', avg_ml_score: 0.71, producers_count: 2341, hidden_talents_count: 12, z_score: 1.1, is_outlier: true },
  // ... остальные 16 регионов аналогично с разными значениями
]

runSimulation(weights, topN = 20) — возвращает:
{
  shortlist: [], // массив производителей, те же поля
  entered: [{ producer_id: 'P1003', ... }], // вошли в шортлист
  left: [{ producer_id: 'P1007', ... }], // вышли из шортлиста
  hidden_talent_count: 8,
  weights_used: weights
}

getMetrics() — возвращает:
{
  roc_auc: 0.72,
  best_f1: 0.68,
  precision: 0.71,
  recall: 0.65,
  model_version: '1.0.0',
  trained_at: '2024-03-15T10:00:00Z'
}

runPipeline() — возвращает после 2000ms задержки:
{ status: 'success', message: 'Пайплайн выполнен', processed: 15008, duration_seconds: 47 }

ФАЙЛ 2: src/services/api.js

import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || error.message || 'Неизвестная ошибка'
    console.error('[API Error]', error.config?.url, message)
    return Promise.reject(new Error(message))
  }
)

export const getHealth = () => api.get('/health')
export const getProducers = (params) => api.get('/api/producers', { params })
export const getProducerDetail = (id) => api.get(`/api/producers/${id}`)
export const getProducerAdvice = (id) => api.get(`/api/producers/${id}/advice`)
export const getShortlist = (topN = 20) => api.get('/api/shortlist', { params: { top_n: topN } })
export const getFairness = () => api.get('/api/fairness')
export const getMetrics = () => api.get('/api/metrics')
export const getMapRegions = () => api.get('/api/map/regions')
export const runSimulation = (weights, topN = 20) => api.post('/api/simulate', { weights, top_n: topN })
export const runPipeline = () => api.post('/api/pipeline/run')

ФАЙЛ 3: src/.env (создай в корне frontend/, не в src/):
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=

ФАЙЛ 4: frontend/.env.example (копия .env но с плейсхолдерами):
VITE_API_URL=https://your-railway-url.up.railway.app
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: вызов mockApi.getProducers() в консоли браузера возвращает объект с полем items длиной 20.
```

---

## ДЕНЬ 2 — 28 марта | UI компоненты

### 🎯 Цель дня: все базовые UI компоненты готовы
### ✅ Критерий готовности: можно импортировать из `components/ui/index.js` и получить все компоненты без ошибок

---

### ПРОМПТ 2.1 — Button + Badge

```
Создай два базовых UI компонента. Используй только Tailwind классы, без inline-стилей.

ФАЙЛ: src/components/ui/Button.jsx

Props:
- variant: 'primary' | 'secondary' | 'ghost' | 'danger' (default: 'primary')
- size: 'sm' | 'md' | 'lg' (default: 'md')
- loading: boolean (default: false)
- disabled: boolean (default: false)
- onClick: function
- children: ReactNode
- className: string (для расширения)

Классы по variant:
primary:   'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800'
secondary: 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'
ghost:     'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
danger:    'bg-red-600 text-white hover:bg-red-700 active:bg-red-800'

Классы по size:
sm: 'px-3 py-1.5 text-xs'
md: 'px-4 py-2 text-sm'
lg: 'px-6 py-3 text-base'

Базовые классы всегда: 'inline-flex items-center gap-2 font-medium rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1'
Disabled/loading: 'opacity-50 cursor-not-allowed pointer-events-none'

Спиннер (при loading=true, перед children):
<svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
</svg>

ФАЙЛ: src/components/ui/Badge.jsx

Props:
- variant: 'hidden_talent' | 'shortlisted' | 'at_risk' | 'score_high' | 'score_mid' | 'score_low'
- children: ReactNode (если не передан — используй label по умолчанию)

Маппинг variant → классы + дефолтный label:
hidden_talent: 'bg-purple-100 text-purple-800 border border-purple-200' → '★ Скрытый талант'
shortlisted:   'bg-green-100 text-green-800 border border-green-200'   → '✓ Шортлист'
at_risk:       'bg-red-100 text-red-800 border border-red-200'         → '↓ Переоценён'
score_high:    'bg-green-100 text-green-800'                            → (показывай children)
score_mid:     'bg-yellow-100 text-yellow-800'                          → (показывай children)
score_low:     'bg-red-100 text-red-800'                                → (показывай children)

Базовые классы: 'inline-flex items-center rounded-full text-xs font-semibold px-2.5 py-0.5'

Хелпер функция (экспортируй отдельно):
export function getScoreVariant(score) {
  if (score >= 0.8) return 'score_high'
  if (score >= 0.6) return 'score_mid'
  return 'score_low'
}
```

---

### ПРОМПТ 2.2 — Card + Table + Skeleton

```
Создай три структурных компонента.

ФАЙЛ: src/components/ui/Card.jsx

Props: title (string, опционально), children, className, action (ReactNode — кнопка в правом углу заголовка)

JSX структура:
<div className={`bg-white rounded-xl border border-slate-200 shadow-sm ${className}`}>
  {title && (
    <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
      <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">{title}</h2>
      {action && <div>{action}</div>}
    </div>
  )}
  <div className="p-6">{children}</div>
</div>

ФАЙЛ: src/components/ui/Table.jsx

Props:
- columns: Array<{ key: string, header: string, width?: string, render?: (value, row) => ReactNode }>
- data: Array<object>
- onRowClick?: (row) => void
- loading?: boolean
- emptyText?: string (default: 'Нет данных')

Структура:
<div className="overflow-hidden rounded-xl border border-slate-200 shadow-sm">
  <div className="overflow-x-auto">
    <table className="w-full text-sm">
      <thead className="bg-slate-50 border-b border-slate-200 sticky top-0">
        — заголовки: text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3 text-left
      <tbody>
        — строки: чётные bg-white, нечётные bg-slate-50/40
        — hover: hover:bg-blue-50/50 transition-colors duration-100
        — cursor-pointer если есть onRowClick
        — ячейки: px-4 py-3 text-slate-700
    Если data.length === 0 и не loading:
      <tr><td colSpan={columns.length}> <EmptyState />

ВАЖНО: если передан render в column — используй render(row[column.key], row), иначе row[column.key].

ФАЙЛ: src/components/ui/Skeleton.jsx

Props:
- variant: 'text' | 'card' | 'table' | 'chart' | 'circle'
- rows?: number (только для variant='table', default: 5)
- className?: string

Базовый элемент: <div className="animate-pulse bg-slate-200 rounded-md" />

Варианты:
text:   h-4 w-full (одна строка)
card:   h-24 w-full rounded-xl
chart:  h-48 w-full rounded-xl
circle: h-10 w-10 rounded-full

table:  рендери {rows} строк, каждая строка:
<div className="flex gap-4 px-4 py-3 border-b border-slate-100">
  <div className="animate-pulse bg-slate-200 rounded h-4 w-8" />    (номер)
  <div className="animate-pulse bg-slate-200 rounded h-4 w-32" />   (имя)
  <div className="animate-pulse bg-slate-200 rounded h-4 w-20" />   (регион)
  <div className="animate-pulse bg-slate-200 rounded h-4 w-16" />   (балл)
  <div className="animate-pulse bg-slate-200 rounded h-4 w-16" />   (статус)
</div>
```

---

### ПРОМПТ 2.3 — Toast + EmptyState + ErrorState + barrel export

```
Создай финальные UI компоненты и barrel export.

ФАЙЛ: src/components/ui/Toast.jsx

Реализация через React Context + useReducer:

1. ToastContext с провайдером ToastProvider
2. Хук useToast() — возвращает функцию toast(message, type)
3. type: 'success' | 'error' | 'info'
4. Каждый тост: { id: Date.now(), message, type }
5. Auto-dismiss: setTimeout 3000ms → dispatch({ type: 'REMOVE', id })

Цвета:
success: 'bg-green-600'
error:   'bg-red-600'
info:    'bg-blue-600'

Иконки (текст):
success: '✓'
error:   '✕'
info:    'ℹ'

JSX для рендера тостов (портал через document.body через ReactDOM.createPortal):
<div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
  {toasts.map(t =>
    <motion.div
      key={t.id}
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 10 }}
      className={`flex items-center gap-3 px-4 py-3 rounded-lg text-white text-sm font-medium shadow-lg min-w-64 ${colorMap[t.type]}`}
    >
      <span>{iconMap[t.type]}</span>
      <span>{t.message}</span>
      <button onClick={() => remove(t.id)} className="ml-auto opacity-70 hover:opacity-100">✕</button>
    </motion.div>
  )}
</div>

6. AnimatePresence из framer-motion вокруг списка тостов.
7. ToastProvider оберни в src/main.jsx вокруг App.

ФАЙЛ: src/components/ui/EmptyState.jsx

Props: title, description, actionLabel, onAction, icon (default: '📭')

JSX:
<div className="flex flex-col items-center justify-center py-16 text-center">
  <div className="text-5xl mb-4">{icon}</div>
  <h3 className="text-lg font-semibold text-slate-700 mb-1">{title}</h3>
  {description && <p className="text-sm text-slate-500 mb-4 max-w-sm">{description}</p>}
  {actionLabel && onAction && <Button variant="secondary" size="sm" onClick={onAction}>{actionLabel}</Button>}
</div>

ФАЙЛ: src/components/ui/ErrorState.jsx

Props: message, onRetry

JSX:
<div className="flex flex-col items-center justify-center py-12 text-center bg-red-50 border border-red-200 rounded-xl">
  <div className="text-4xl mb-3">⚠️</div>
  <h3 className="text-base font-semibold text-red-800 mb-1">Что-то пошло не так</h3>
  {message && <p className="text-sm text-red-600 mb-4 max-w-sm">{message}</p>}
  {onRetry && <Button variant="danger" size="sm" onClick={onRetry}>↺ Попробовать снова</Button>}
</div>

ФАЙЛ: src/components/ui/index.js

export { default as Button } from './Button'
export { default as Badge, getScoreVariant } from './Badge'
export { default as Card } from './Card'
export { default as Table } from './Table'
export { default as Skeleton } from './Skeleton'
export { default as EmptyState } from './EmptyState'
export { default as ErrorState } from './ErrorState'
export { ToastProvider, useToast } from './Toast'

ФИНАЛЬНАЯ ПРОВЕРКА: импортируй все компоненты в DashboardPage и убедись что нет ошибок импорта.
```

---

## ДЕНЬ 3 — 29 марта | Dashboard Page | ⚑ СДАЧА #1

### 🎯 Цель дня: Dashboard рендерится с моками, таблица и фильтры работают
### ✅ Критерий готовности: 4 KPI карточки + таблица 20 строк + фильтры + slide-in панель

---

### ПРОМПТ 3.1 — React Query + хуки данных

```
Настрой React Query и создай все хуки данных. Пока хуки работают только на mockApi.

ШАГ 1. Обнови src/main.jsx:
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

Оберни <App /> в <QueryClientProvider client={queryClient}>

ШАГ 2. Создай следующие хуки (все в src/hooks/):

src/hooks/useProducers.js
import { useQuery } from '@tanstack/react-query'
import { getProducers } from '../services/mockApi'

export function useProducers(filters = {}) {
  return useQuery({
    queryKey: ['producers', filters],
    queryFn: () => getProducers(filters),
  })
}

src/hooks/useShortlist.js — queryKey: ['shortlist', topN], queryFn: getShortlist(topN)
src/hooks/useMetrics.js — queryKey: ['metrics'], queryFn: getMetrics
src/hooks/useFairness.js — queryKey: ['fairness'], queryFn: getFairness
src/hooks/useMapRegions.js — queryKey: ['map-regions'], queryFn: getMapRegions

src/hooks/useProducerDetail.js
export function useProducerDetail(id) {
  return useQuery({
    queryKey: ['producer', id],
    queryFn: () => getProducerDetail(id),
    enabled: !!id, // не запускать если id не задан
  })
}

src/hooks/useProducerAdvice.js — аналогично, queryKey: ['producer-advice', id]

src/hooks/useSimulator.js
import { useMutation } from '@tanstack/react-query'
import { runSimulation } from '../services/mockApi'

export function useSimulator() {
  return useMutation({
    mutationFn: ({ weights, topN }) => runSimulation(weights, topN),
  })
}

ШАГ 3. В DashboardPage временно добавь:
const { data, isLoading, error } = useProducers()
console.log('[Dashboard]', { data, isLoading, error })

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: в консоли видны данные с полем items.
```

---

### ПРОМПТ 3.2 — Dashboard KPI + таблица производителей

```
Реализуй основной контент DashboardPage.

ФАЙЛ: src/pages/DashboardPage.jsx

Импорты: useProducers, useShortlist, Card, Badge, Skeleton, Table, getScoreVariant

СЕКЦИЯ 1: KPI строка
<div className="grid grid-cols-4 gap-4 mb-6">
  4 карточки, каждая:
  <Card className="!p-0">
    <div className="p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-slate-500">{label}</span>
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="text-3xl font-bold {colorClass}">{value}</div>
      <div className="text-xs text-slate-400 mt-1">{subtitle}</div>
    </div>
  </Card>

Карточки:
1. label="Производителей всего", icon="👥", value=producers.data?.total?.toLocaleString(), color=text-slate-900
2. label="В шортлисте", icon="✅", value=shortlist.data?.total_producers, color=text-green-600
3. label="Скрытых талантов", icon="★", value=shortlist.data?.hidden_talents_count, color=text-purple-600
4. label="Средний ML score", icon="📈", value=`${Math.round((shortlist.data?.avg_ml_score || 0) * 100)}%`, color=text-blue-600

При загрузке: <Skeleton variant="card" /> вместо карточки.

ФАЙЛ: src/components/features/ProducerTable.jsx

Columns для Table:
[
  { key: 'index', header: '#', width: '50px', render: (_, __, i) => i + 1 },
  { key: 'producer_id', header: 'ID', render: (v) => <span className="font-mono text-xs">{v}</span> },
  { key: 'region', header: 'Регион' },
  { key: 'direction', header: 'Направление' },
  {
    key: 'ml_score',
    header: 'ML Score',
    render: (v) => <Badge variant={getScoreVariant(v)}>{Math.round(v * 100)}%</Badge>
  },
  { key: 'fcfs_rank', header: 'FCFS Ранг', render: (v) => `#${v}` },
  {
    key: 'delta',
    header: 'Delta',
    render: (v) => v > 0
      ? <span className="text-green-600 font-medium">↑ +{v}</span>
      : v < 0
      ? <span className="text-red-600 font-medium">↓ {v}</span>
      : <span className="text-slate-400">—</span>
  },
  {
    key: 'status',
    header: 'Статус',
    render: (_, row) => row.hidden_talent
      ? <Badge variant="hidden_talent" />
      : row.at_risk
      ? <Badge variant="at_risk" />
      : <Badge variant="shortlisted" />
  },
]

Props ProducerTable: data, loading, onRowClick
При loading: Skeleton variant="table" rows={8}
```

---

### ПРОМПТ 3.3 — Фильтры + Slide-in панель

```
Добавь фильтры и панель детализации в Dashboard.

ФАЙЛ: src/components/features/ProducerFilters.jsx

State: { region: '', direction: '', minScore: 0, hiddenOnly: false }
Debounce: onChange обновляет локальный state немедленно, но вызывает onFiltersChange через 300ms (useEffect + clearTimeout).

Компоненты:
1. Dropdown "Регион" — нативный <select> с классами Tailwind (border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white):
   options: ['', 'Алматы', 'Астана', 'Шымкент', 'Актобе', 'Қарағанды']
   placeholder: "Все регионы"

2. Dropdown "Направление" — аналогично:
   options: ['', 'Растениеводство', 'Животноводство', 'Переработка', 'Аквакультура']

3. Range slider "Мин. балл":
   <label className="text-sm text-slate-600">Мин. балл: {minScore}%</label>
   <input type="range" min="0" max="100" step="5" value={minScore} onChange={...}
     className="w-32 accent-blue-600" />

4. Toggle "Только скрытые таланты":
   — простая реализация без headlessui: div с onClick, который переключает state
   className активного: bg-purple-600, неактивного: bg-slate-300
   Стиль: <div onClick={toggle} className={`relative w-10 h-5 rounded-full cursor-pointer transition-colors ${active ? 'bg-purple-600' : 'bg-slate-300'}`}>
     <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${active ? 'left-5' : 'left-0.5'}`} />
   </div>

5. Кнопка "Сбросить" — показывать только если хоть один фильтр активен:
   isActive = region || direction || minScore > 0 || hiddenOnly
   <Button variant="ghost" size="sm" onClick={onReset}>✕ Сбросить</Button>

ФАЙЛ: src/components/features/ProducerSidePanel.jsx

Props: producer (объект из таблицы), onClose, onOpenFull

Анимация Framer Motion:
<AnimatePresence>
  {producer && (
    <>
      {/* Overlay */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />
      {/* Panel */}
      <motion.div
        initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-50 flex flex-col overflow-y-auto"
      >
```

Содержимое панели:
- Шапка: producer_id + кнопка ✕ (onClick={onClose})
- Раздел "Основное": регион, направление, направление в виде badge
- Раздел "Баллы": ML score badge + ML ранг + FCFS ранг + Delta badge
- Раздел "Топ-3 фактора" (мини SHAP):
  Из shap_values берём первые 3.
  Для каждого:
  <div className="flex items-center gap-2 py-1">
    <span className="text-xs text-slate-500 w-32 truncate">{feature_label}</span>
    <div className="flex-1 h-2 bg-slate-100 rounded-full">
      <div style={{ width: `${Math.abs(shap_value) * 200}%` }}
           className={`h-2 rounded-full ${shap_value > 0 ? 'bg-green-500' : 'bg-red-500'}`} />
    </div>
    <span className={`text-xs font-medium w-10 text-right ${shap_value > 0 ? 'text-green-600' : 'text-red-600'}`}>
      {shap_value > 0 ? '+' : ''}{shap_value.toFixed(2)}
    </span>
  </div>
  ВАЖНО: shap_values может отсутствовать в данных таблицы — показывай заглушку "Загрузка факторов...".

- Кнопка внизу: <Button onClick={() => onOpenFull(producer.producer_id)}>Открыть полный профиль →</Button>

Интеграция в DashboardPage:
- State: selectedProducer = null
- ProducerTable onRowClick={row => setSelectedProducer(row)}
- ProducerSidePanel producer={selectedProducer} onClose={() => setSelectedProducer(null)} onOpenFull={id => navigate(`/producer/${id}`)}
```

---

## ДЕНЬ 4 — 30 марта | SHAP Chart + ProducerPage

### 🎯 Цель дня: ProducerPage полностью готова
### ✅ Критерий готовности: все 6 карточек рендерятся, SHAP чарт показывает данные, история заявок работает

---

### ПРОМПТ 4.1 — SHAPBarChart

```
Создай компонент графика SHAP values.

ФАЙЛ: src/components/charts/SHAPBarChart.jsx

Props:
- data: Array<{ feature_label: string, shap_value: number, raw_value: number }>
- maxItems: number (default: 5)
- height: number (default: 300)

Подготовка данных:
- Берём первые maxItems элементов
- Сортируем по Math.abs(shap_value) убыванию
- Для Recharts нужно добавить цвет: data.map(d => ({ ...d, fill: d.shap_value > 0 ? '#16A34A' : '#DC2626' }))

Recharts компонент:
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, LabelList, ResponsiveContainer, Cell } from 'recharts'

<ResponsiveContainer width="100%" height={height}>
  <BarChart data={sorted} layout="vertical" margin={{ top: 5, right: 60, left: 160, bottom: 5 }}>
    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
    <XAxis type="number" tickFormatter={v => v.toFixed(2)} tick={{ fontSize: 11 }} />
    <YAxis
      type="category"
      dataKey="feature_label"
      tick={{ fontSize: 12, fill: '#475569' }}
      width={155}
    />
    <Tooltip
      content={({ active, payload }) => {
        if (!active || !payload?.length) return null
        const d = payload[0].payload
        return (
          <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-lg text-xs">
            <p className="font-semibold text-slate-700 mb-1">{d.feature_label}</p>
            <p>SHAP: <span className={d.shap_value > 0 ? 'text-green-600' : 'text-red-600'}>
              {d.shap_value > 0 ? '+' : ''}{d.shap_value.toFixed(3)}
            </span></p>
            <p className="text-slate-500">Значение: {d.raw_value}</p>
          </div>
        )
      }}
    />
    <Bar dataKey="shap_value" radius={[0, 4, 4, 0]}>
      {sorted.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
      <LabelList
        dataKey="shap_value"
        position="right"
        formatter={v => `${v > 0 ? '+' : ''}${v.toFixed(2)}`}
        style={{ fontSize: 11, fill: '#64748B' }}
      />
    </Bar>
  </BarChart>
</ResponsiveContainer>

Если data пустой или undefined: показывай <EmptyState title="Нет данных SHAP" icon="📊" />
```

---

### ПРОМПТ 4.2 — ProducerPage полная

```
Реализуй полную страницу профиля производителя.

ФАЙЛ: src/pages/ProducerPage.jsx

Данные:
const { id } = useParams()
const detail = useProducerDetail(id)
const advice = useProducerAdvice(id)
const navigate = useNavigate()

Общее состояние loading: detail.isLoading || advice.isLoading
Состояние error: detail.error || advice.error

При error:
<div className="flex flex-col items-center pt-16">
  <ErrorState message={error.message} onRetry={() => { detail.refetch(); advice.refetch() }} />
  <Button variant="ghost" onClick={() => navigate(-1)} className="mt-4">← Назад</Button>
</div>

Основной layout (при успешной загрузке):
<div className="grid grid-cols-3 gap-6">

КАРТОЧКА 1 (col-span-2): "Основная информация"
- Шапка: producer_id (text-2xl font-bold) + регион + направление
- Строка бейджей: Badge hidden_talent (если true) + Badge at_risk (если true) + Badge shortlisted (если оба false)
- Grid 3 колонки: ML Score / ML Ранг / FCFS Ранг
  Каждый: заголовок (text-xs text-slate-500) + значение (text-2xl font-bold)
  ML Score: цвет по getScoreVariant
  Delta: отдельная ячейка — зелёный если > 0, красный если < 0, серый если 0

КАРТОЧКА 2 (col-span-2): "Факторы влияния (SHAP)"
- <SHAPBarChart data={detail.data?.shap_values} maxItems={5} height={300} />
- Блок bg-blue-50 rounded-lg p-4 mt-4:
  <p className="text-xs font-semibold text-blue-700 mb-1">💡 Интерпретация от AI</p>
  <p className="text-sm text-blue-800">{advice.data?.score_explanation}</p>
  При загрузке advice: <Skeleton variant="text" />

КАРТОЧКА 3 (col-span-2): "История заявок"
- Recharts LineChart:
  import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
  data={detail.data?.history}
  dataKey X: "month", dataKey Y: "applications"
  Line: stroke="#2563EB" strokeWidth={2} dot={{ fill: '#2563EB', r: 4 }}
  <ResponsiveContainer width="100%" height={200}>

КАРТОЧКА 4 (col-span-1): "ML vs FCFS сравнение"
- Два больших badge рядом: [ML Ранг #{ml_rank}] [FCFS Ранг #{fcfs_rank}]
- Стрелка delta: если delta > 0 → "↑ ML продвигает на {delta} позиций вверх" (text-green-600)
- Блок bg-amber-50 p-3 rounded-lg mt-3:
  <p className="text-xs font-semibold text-amber-700 mb-1">⚠️ Системное смещение</p>
  <p className="text-sm text-amber-800">{advice.data?.baseline_injustice}</p>

КАРТОЧКА 5 (col-span-1): "Рекомендации"
- advice.data?.recommendations.map(rec =>
  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-3">
    <div className="flex items-start gap-2">
      <span className="text-lg">🎯</span>
      <div>
        <p className="text-sm text-slate-700">{rec.text}</p>
        <Badge variant="score_high" className="mt-2">+{rec.impact}% к баллу</Badge>
      </div>
    </div>
  </div>

КАРТОЧКА 6 (col-span-1): "Статистика" (grid 2x2)
[Заявок всего: stats.total_applications] [Исполнено: stats.completed]
[Направлений: stats.directions_count] [Активных мес.: stats.active_months]
Каждая ячейка: bg-slate-50 rounded-lg p-3, число text-2xl font-bold, подпись text-xs text-slate-500

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: страница /producer/P1000 показывает все 6 карточек с данными.
```

---

## ДЕНЬ 5 — 31 марта | Supabase Realtime + реальный API

### 🎯 Цель дня: Realtime работает; при наличии Railway URL — переключиться
### ✅ Критерий готовности: строка мигает зелёным при обновлении; Network tab показывает реальные запросы

---

### ПРОМПТ 5.1 — Supabase Realtime

```
Добавь Supabase Realtime для live-обновлений таблицы.

ФАЙЛ: src/services/supabase.js

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// Если URL не задан — возвращаем null-клиент чтобы не падать в dev
export const supabase = supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey)
  : null

ФАЙЛ: src/hooks/useRealtimeScores.js

import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { supabase } from '../services/supabase'

export function useRealtimeScores() {
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!supabase) {
      console.log('[Realtime] Supabase не настроен, пропускаем подписку')
      return
    }

    const channel = supabase
      .channel('scores-changes')
      .on('postgres_changes', {
        event: 'UPDATE',
        schema: 'public',
        table: 'scores',
      }, (payload) => {
        const { producer_id, ml_score } = payload.new

        // Обновляем кеш React Query без перезагрузки
        queryClient.setQueryData(['producers'], (old) => {
          if (!old?.items) return old
          return {
            ...old,
            items: old.items.map(p =>
              p.producer_id === producer_id
                ? { ...p, ml_score, _updated: true }
                : p
            )
          }
        })

        // Убираем флаг _updated через 1.5 секунды
        setTimeout(() => {
          queryClient.setQueryData(['producers'], (old) => {
            if (!old?.items) return old
            return {
              ...old,
              items: old.items.map(p =>
                p.producer_id === producer_id
                  ? { ...p, _updated: false }
                  : p
              )
            }
          })
        }, 1500)
      })
      .subscribe()

    return () => supabase.removeChannel(channel)
  }, [queryClient])
}

CSS в src/styles/globals.css — добавь в конец файла:
@keyframes highlight-green {
  0%   { background-color: #dcfce7; }
  70%  { background-color: #dcfce7; }
  100% { background-color: transparent; }
}
.row-updated {
  animation: highlight-green 1.5s ease-out forwards;
}

В ProducerTable.jsx добавь к строке:
className={`... ${row._updated ? 'row-updated' : ''}`}

В DashboardPage.jsx добавь: useRealtimeScores()

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: если Supabase не настроен — ничего не падает (null-check). Если настроен — строки мигают зелёным при обновлении.
```

---

### ПРОМПТ 5.2 — Переключение на реальный API

```
Бэкендер дал Railway URL. Переключаемся с моков на реальный API.

ШАГ 1. Обнови frontend/.env (замени значения реальными):
VITE_API_URL=https://RAILWAY_URL_СЮДА.up.railway.app
VITE_SUPABASE_URL=https://SUPABASE_URL_СЮДА.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...

ШАГ 2. В каждом хуке замени импорт mockApi на api:
В файлах: useProducers.js, useShortlist.js, useMetrics.js, useFairness.js,
useMapRegions.js, useProducerDetail.js, useProducerAdvice.js, useSimulator.js

// БЫЛО:
import { getXxx } from '../services/mockApi'
// СТАЛО:
import { getXxx } from '../services/api'

ШАГ 3. Перезапусти dev-сервер (Ctrl+C → npm run dev).

ШАГ 4. Проверки в браузере DevTools:
- Network → XHR: все запросы идут на Railway URL и возвращают 200
- Console: нет ошибок "CORS" или "Network Error"
- Dashboard: таблица заполнена реальными данными

ЕСЛИ CORS ошибка (Access-Control-Allow-Origin):
Сообщи бэкендеру точно такую строку:
"CORS ошибка: добавь http://localhost:5173 в список разрешённых origins на Railway.
В Railway переменная FRONTEND_URL=http://localhost:5173"

ЕСЛИ данные пустые или поля не совпадают:
Сравни поля из Network → Response с полями в mockApi.js и сообщи бэкендеру о расхождениях.

ШАГ 5. Делай git commit только после успешной проверки:
git add . && git commit -m "feat: switch to real API from Railway"
```

---

## ДЕНЬ 6 — 1 апреля | SimulatorPage + FairnessPage

### 🎯 Цель дня: обе страницы полностью готовы
### ✅ Критерий готовности: слайдеры нормируются до 100%, таблица анимируется, Lorenz кривая рендерится

---

### ПРОМПТ 6.1 — SimulatorPage

```
Реализуй страницу симулятора весов.

ФАЙЛ: src/pages/SimulatorPage.jsx

State весов (начальные значения должны давать сумму 100):
const [weights, setWeights] = useState({
  completion_rate: 35,
  approval_rate: 25,
  diversity: 20,
  activity: 10,
  working_hours: 10,
})

Конфигурация слайдеров (массив):
[
  { key: 'completion_rate', label: 'Результативность', emoji: '✅' },
  { key: 'approval_rate', label: 'Одобряемость заявок', emoji: '📋' },
  { key: 'diversity', label: 'Диверсификация', emoji: '🌿' },
  { key: 'activity', label: 'Активность подачи', emoji: '📨' },
  { key: 'working_hours', label: 'Рабочие часы', emoji: '⏱' },
]

Функция изменения веса с авто-нормировкой:
const handleWeightChange = (key, newValue) => {
  setWeights(prev => {
    const delta = newValue - prev[key]
    const otherKeys = Object.keys(prev).filter(k => k !== key)
    const otherSum = otherKeys.reduce((sum, k) => sum + prev[k], 0)
    if (otherSum === 0) return { ...prev, [key]: newValue }

    // Пропорционально уменьшаем/увеличиваем остальные
    const newWeights = { ...prev, [key]: newValue }
    otherKeys.forEach(k => {
      newWeights[k] = Math.max(0, Math.round(prev[k] - delta * (prev[k] / otherSum)))
    })
    // Корректируем погрешность округления
    const sum = Object.values(newWeights).reduce((a, b) => a + b, 0)
    if (sum !== 100) {
      const diff = 100 - sum
      const adjustKey = otherKeys[0]
      newWeights[adjustKey] = Math.max(0, newWeights[adjustKey] + diff)
    }
    return newWeights
  })
}

Simulation: useMutation + debounce 300ms
useEffect(() => {
  const t = setTimeout(() => {
    simulate.mutate({ weights, topN: 20 })
  }, 300)
  return () => clearTimeout(t)
}, [weights])

КОМПОНЕНТ WeightSlider (inline в файле или отдельный):
<div className="mb-4">
  <div className="flex justify-between items-center mb-1">
    <label className="text-sm font-medium text-slate-700">{emoji} {label}</label>
    <span className="text-sm font-bold text-blue-600 w-10 text-right">{value}%</span>
  </div>
  <input
    type="range" min="0" max="100" value={value}
    onChange={e => onChange(key, parseInt(e.target.value))}
    className="w-full h-2 rounded-full appearance-none cursor-pointer accent-blue-600"
  />
</div>

Индикатор суммы весов:
const total = Object.values(weights).reduce((a, b) => a + b, 0)
<div className={`text-sm font-semibold ${total === 100 ? 'text-green-600' : 'text-red-600'}`}>
  Сумма весов: {total}% {total === 100 ? '✓' : '— исправляется автоматически'}
</div>

Layout: grid grid-cols-3 gap-6
- Левая панель (col-span-1): Card "Настройка приоритетов" + слайдеры + индикатор суммы
- Правая панель (col-span-2): результаты симуляции

Правая панель:
Шапка (flex gap-4):
- "✅ Вошли: +{entered.length}" (text-green-600 font-bold text-lg)
- "❌ Вышли: −{left.length}" (text-red-600 font-bold text-lg)
- При загрузке: анимирующийся спиннер

Таблица с анимацией (Framer Motion):
<AnimatePresence mode="popLayout">
  {shortlist?.map(producer => (
    <motion.tr
      key={producer.producer_id}
      layout
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className={`
        ${entered.find(e => e.producer_id === producer.producer_id)
          ? 'border-l-4 border-green-500 bg-green-50'
          : left.find(l => l.producer_id === producer.producer_id)
          ? 'border-l-4 border-red-500 bg-red-50'
          : ''}
      `}
    >

Блок "Скрытых талантов":
<Card>
  <p className="text-sm text-slate-600 mb-2">Скрытых талантов в шортлисте:</p>
  <div className="flex items-center gap-3">
    <span className="text-3xl font-bold text-purple-600">{simulate.data?.hidden_talent_count}</span>
    <span className="text-slate-400">/20</span>
  </div>
  <div className="w-full bg-slate-100 rounded-full h-2 mt-3">
    <div
      className="bg-purple-600 h-2 rounded-full transition-all duration-500"
      style={{ width: `${(simulate.data?.hidden_talent_count / 20) * 100}%` }}
    />
  </div>
</Card>
```

---

### ПРОМПТ 6.2 — FairnessPage

```
Реализуй страницу анализа справедливости.

ФАЙЛ: src/pages/FairnessPage.jsx

Данные: useFairness() hook

СЕКЦИЯ 1: KPI карточки (grid grid-cols-4 gap-4 mb-6)

Функция интерпретации Gini:
const interpretGini = (g) => g < 0.3
  ? { label: 'Низкое неравенство', color: 'text-green-600', bg: 'bg-green-50' }
  : g < 0.5
  ? { label: 'Умеренное неравенство', color: 'text-yellow-600', bg: 'bg-yellow-50' }
  : { label: 'Высокое неравенство', color: 'text-red-600', bg: 'bg-red-50' }

Карточка Gini:
<Card>
  <p className="text-xs text-slate-500 mb-1">{title}</p>
  <p className={`text-3xl font-bold ${gini_info.color}`}>{value.toFixed(2)}</p>
  <p className={`text-xs font-medium mt-2 px-2 py-0.5 rounded-full inline-block ${gini_info.bg} ${gini_info.color}`}>
    {gini_info.label}
  </p>
</Card>

Карточка KW-тест:
<Card>
  <p className="text-xs text-slate-500 mb-1">{title}</p>
  <p className="text-2xl font-bold text-slate-800">H={data.H.toFixed(1)}</p>
  <p className={`text-xs mt-2 font-medium ${data.p_value > 0.05 ? 'text-green-600' : 'text-red-600'}`}>
    p={data.p_value.toFixed(3)} — {data.p_value > 0.05 ? '✓ Различий нет' : '⚠ Значимые различия'}
  </p>
</Card>

СЕКЦИЯ 2: Lorenz кривая (Card col-span-2 in grid grid-cols-2 gap-4)

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Legend, ResponsiveContainer } from 'recharts'

Данные: объединяем lorenz_scores и диагональ:
const lorenzData = fairness.data?.lorenz_scores.map((point, i, arr) => ({
  x: point.x,
  actual: point.y,
  equal: point.x, // диагональ идеального равенства
}))

<ResponsiveContainer width="100%" height={280}>
  <LineChart data={lorenzData} margin={{ top: 5, right: 20, bottom: 20, left: 20 }}>
    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
    <XAxis dataKey="x" tickFormatter={v => `${Math.round(v*100)}%`}
           label={{ value: 'Доля производителей', position: 'insideBottom', offset: -10, fontSize: 11 }} />
    <YAxis tickFormatter={v => `${Math.round(v*100)}%`}
           label={{ value: 'Доля баллов', angle: -90, position: 'insideLeft', fontSize: 11 }} />
    <Tooltip formatter={(v, name) => [`${Math.round(v*100)}%`, name === 'actual' ? 'Реальное' : 'Равенство']} />
    <Legend />
    <Line dataKey="equal" stroke="#CBD5E1" strokeDasharray="5 5" dot={false} name="Идеальное равенство" />
    <Line dataKey="actual" stroke="#2563EB" strokeWidth={2} dot={false} name="Реальное распределение" />
  </LineChart>
</ResponsiveContainer>

СЕКЦИЯ 3: Z-score регионов (Card col-span-2)

<BarChart data={fairness.data?.region_zscores} margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
  — каждый бар: Cell fill по is_outlier: '#DC2626' или '#16A34A'
  — ReferenceLine y={1} stroke="#94A3B8" strokeDasharray="3 3" label="1σ"
  — ReferenceLine y={-1} stroke="#94A3B8" strokeDasharray="3 3" label="-1σ"
  — Tooltip: показывать is_outlier ? '⚠️ Статистическое отклонение' : ''

СЕКЦИЯ 4: Тепловая карта (Card col-span-2, mt-4)

ФАЙЛ: src/components/charts/HeatMap.jsx

Props: data (массив { region, direction, avg_score })
— Если data пустой (заглушка в mockApi) — показывай EmptyState с кнопкой "Данные появятся после запуска пайплайна"

Реализация (SVG):
- Уникальные регионы = строки, уникальные направления = столбцы
- Функция цвета: interpolate от белого #FFFFFF (score=0) до зелёного #15803D (score=1)
  const color = (score) => {
    const r = Math.round(255 - score * 234)
    const g = Math.round(255 - score * 127)
    const b = Math.round(255 - score * 234)
    return `rgb(${r},${g},${b})` // белый → зелёный
  }
- Каждая ячейка 50×36px
- Tooltip: title атрибут на SVG rect для простоты
- overflow-x: auto на контейнере
- Легенда: flex полоска белый → зелёный + подписи "Низкий" "Высокий"
```

---

## ДЕНЬ 7 — 2 апреля | MapPage + финализация | ⚑ СДАЧА #2

### 🎯 Цель дня: карта работает, экспорт CSV, pipeline кнопка, все состояния проверены
### ✅ Критерий готовности: npm run build без ошибок, все 5 страниц открываются

---

### ПРОМПТ 7.1 — MapPage

```
Реализуй карту регионов Казахстана с хороплетом.

ШАГ 1. Скачай GeoJSON регионов Казахстана:
Найди файл "Kazakhstan regions GeoJSON" с 17 областями или используй эту ссылку:
https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries.geojson
ВАЖНО: тебе нужен файл именно с областями (регионами) Казахстана, не страной целиком.
Сохрани в frontend/public/kz-regions.geojson

Если не можешь найти — создай заглушку с несколькими регионами для демонстрации.

ШАГ 2. Добавь CSS leaflet в index.html:
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />

ФАЙЛ: src/pages/MapPage.jsx

import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import { useEffect, useState } from 'react'
import { useMapRegions } from '../hooks/useMapRegions'

Логика:
- geoData = useState(null) — загружаем GeoJSON через fetch('/kz-regions.geojson')
- mapRegions = useMapRegions()
- selectedRegion = useState(null) — для панели

Хелпер цвета хороплета:
const getColor = (score) => {
  if (score >= 0.8) return '#15803D'
  if (score >= 0.6) return '#22C55E'
  if (score >= 0.4) return '#86EFAC'
  if (score >= 0.2) return '#BBF7D0'
  return '#F0FDF4'
}

style для каждого региона GeoJSON:
(feature) => {
  const regionData = mapRegions.data?.find(r =>
    r.name === feature.properties.name || r.region_id === feature.properties.id
  )
  return {
    fillColor: regionData ? getColor(regionData.avg_ml_score) : '#E2E8F0',
    weight: 1,
    color: '#94A3B8',
    fillOpacity: 0.7,
  }
}

onEachFeature — добавляем tooltip и обработчик клика:
(feature, layer) => {
  const regionData = mapRegions.data?.find(r => r.name === feature.properties.name)
  if (regionData) {
    layer.bindTooltip(`
      <strong>${regionData.name}</strong><br/>
      Производителей: ${regionData.producers_count}<br/>
      Средний балл: ${Math.round(regionData.avg_ml_score * 100)}%<br/>
      Скрытых талантов: ${regionData.hidden_talents_count}
    `, { sticky: true })
  }
  layer.on('click', () => setSelectedRegion(regionData || null))
}

JSX:
<div className="relative h-[calc(100vh-112px)] rounded-xl overflow-hidden border border-slate-200">
  <MapContainer
    center={[48.0196, 66.9237]} zoom={5}
    className="h-full w-full"
    zoomControl={true}
  >
    <TileLayer
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      attribution='© OpenStreetMap'
    />
    {geoData && (
      <GeoJSON key={JSON.stringify(mapRegions.data)} data={geoData} style={styleFunc} onEachFeature={onEachFeature} />
    )}
  </MapContainer>

  {/* Легенда */}
  <div className="absolute bottom-4 left-4 bg-white rounded-lg p-3 shadow-lg z-[1000] text-xs">
    <p className="font-semibold mb-2 text-slate-700">Средний ML балл</p>
    {[0.8, 0.6, 0.4, 0.2, 0].map(v => (
      <div key={v} className="flex items-center gap-2 mb-1">
        <div style={{ backgroundColor: getColor(v + 0.01) }} className="w-4 h-4 rounded" />
        <span className="text-slate-600">{Math.round(v*100)}%+</span>
      </div>
    ))}
  </div>

  {/* Панель региона */}
  {selectedRegion && <RegionPanel region={selectedRegion} onClose={() => setSelectedRegion(null)} />}
</div>

ФАЙЛ: src/components/features/RegionPanel.jsx

position: absolute right-4 top-4 z-[1000]
width: 300px, bg-white, rounded-xl, shadow-xl, p-4

Содержимое:
- Шапка: {region.name} + кнопка ✕
- Grid 2x2: Производителей | Средний балл | Скрытых талантов | Z-score
- Если region.is_outlier:
  <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-3 text-xs text-red-700">
    ⚠️ Статистическое отклонение — балл значимо отличается от среднего
  </div>
- Кнопка "Смотреть в Dashboard →":
  onClick={() => navigate(`/dashboard?region=${encodeURIComponent(region.name)}`)}
```

---

### ПРОМПТ 7.2 — Экспорт CSV + Pipeline кнопка + финальная проверка

```
Добавь финальные функции и проверь все состояния.

ЧАСТЬ 1: Экспорт CSV

Создай src/utils/exportCsv.js:
export function exportToCsv(data, filename) {
  const headers = ['producer_id', 'region', 'direction', 'ml_score', 'ml_rank', 'fcfs_rank', 'delta', 'hidden_talent']
  const rows = data.map(p => [
    p.producer_id, p.region, p.direction,
    (p.ml_score * 100).toFixed(1) + '%',
    p.ml_rank, p.fcfs_rank, p.delta,
    p.hidden_talent ? 'Да' : 'Нет'
  ])
  const csv = [headers, ...rows].map(r => r.join(',')).join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' }) // \ufeff для Excel
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

В Header.jsx добавь кнопку экспорта рядом с "Запустить пайплайн":
- Кнопка "⬇ Экспорт" только на /dashboard странице (useLocation)
- onClick: получить данные из React Query cache:
  const queryClient = useQueryClient()
  const producers = queryClient.getQueryData(['producers'])
  exportToCsv(producers?.items || [], `subsidies-${new Date().toISOString().slice(0,10)}.csv`)
  toast('✓ Файл скачан', 'success')

ЧАСТЬ 2: Pipeline кнопка в Header

В Header.jsx обнови onClick кнопки "Запустить пайплайн":
import { runPipeline } from '../services/api' // или mockApi
import { useToast } from '../components/ui'

const [pipelineLoading, setPipelineLoading] = useState(false)

const handlePipeline = async () => {
  setPipelineLoading(true)
  try {
    const result = await runPipeline()
    toast(`✓ Пайплайн выполнен за ${result.duration_seconds}с`, 'success')
  } catch (err) {
    toast(`Ошибка: ${err.message}`, 'error')
  } finally {
    setPipelineLoading(false)
  }
}

Кнопка: loading={pipelineLoading} disabled={pipelineLoading}

ЧАСТЬ 3: Чеклист финальных состояний

Пройдись по каждой странице и убедись:

DashboardPage:
✓ loading → 4 Skeleton card + Skeleton table
✓ empty → EmptyState "Нет производителей"
✓ error → ErrorState + кнопка Retry

ProducerPage:
✓ loading → Skeleton во всех 6 карточках
✓ error → ErrorState + кнопка "← Назад"
✓ advice.loading → Skeleton в блоках AI-текста

SimulatorPage:
✓ loading mutation → спиннер в шапке таблицы
✓ empty result → EmptyState "Запустите симуляцию"

FairnessPage:
✓ loading → Skeleton card × 4 + Skeleton chart × 3
✓ empty heatmap → EmptyState с описанием

MapPage:
✓ loading map regions → показывай карту без цвета хороплета
✓ geoData loading → спиннер по центру карты
✓ region panel → закрывается по ✕ и при клике на пустое место

ЧАСТЬ 4: Проверка консоли
- Нет красных ошибок
- Нет React предупреждений "Each child in a list should have a unique key prop"
- Нет "Cannot read properties of undefined" — все опциональные цепочки (a?.b?.c) используются
```

---

### ПРОМПТ 7.3 — Vercel деплой

```
Подготовь проект к деплою.

ШАГ 1. Создай frontend/vercel.json:
{
  "rewrites": [{ "source": "/(.*)", "destination": "/" }],
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist"
}

ШАГ 2. Проверь vite.config.js — должен содержать:
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1000, // Recharts + Leaflet тяжёлые
  },
  server: { port: 5173 },
})

ШАГ 3. Проверь .gitignore в корне frontend/:
node_modules/
dist/
.env
.env.local

ШАГ 4. Запусти билд:
npm run build

Если ошибка "Cannot find module X" → npm install X
Если warning "chunk size > 500kb" → это нормально для Recharts + Leaflet, игнорируем

ШАГ 5. Проверь production сборку локально:
npm run preview
Открой http://localhost:4173 и проверь все 5 роутов.

ШАГ 6. Финальный коммит:
git add .
git commit -m "feat: frontend complete v1.0 - all pages ready"
git push

Сообщи бэкендеру что фронт готов к деплою — он запустит Vercel.
```

---

## ДНИ 9-10 — 4-5 апреля | Полировка + финал | ⚑ 23:59

---

### ПРОМПТ 9.1 — Тепловая карта + UI полировка

```
Доделай тепловую карту и проведи финальную полировку UI.

ЧАСТЬ 1: HeatMap.jsx финальная версия

Ожидаем что в mockApi/реальном API появились данные heatmap:
[{ region: 'Алматы', direction: 'Растениеводство', avg_score: 0.73 }, ...]

Если данных всё ещё нет — генерируй в mockApi:
const REGIONS = ['Алматы', 'Астана', 'Шымкент', 'Актобе', 'Қарағанды', 'Атырау', 'Павлодар']
const DIRECTIONS = ['Растениеводство', 'Животноводство', 'Переработка', 'Аквакультура']
heatmap: REGIONS.flatMap(r => DIRECTIONS.map(d => ({
  region: r, direction: d,
  avg_score: parseFloat((0.3 + Math.random() * 0.7).toFixed(2))
})))

Размеры ячеек: минимум 48×40px (чтобы текст помещался)
Заголовки столбцов: rotate(-45deg) для длинных названий направлений
Заголовки строк: text-xs text-slate-600 font-medium text-right pr-2
Tooltip: HTML title атрибут: `${region} · ${direction}\nБалл: ${Math.round(score*100)}%`
Легенда: горизонтальная полоска 200px × 12px с градиентом + метки "0%" "50%" "100%"

ЧАСТЬ 2: UI полировка всех 5 страниц

Единый стиль заголовков страниц (если не задан через Header):
Убедись что все страницы НЕ имеют своих h1 — заголовок в Header.

Единый отступ контента:
Все страницы: <div className="max-w-7xl mx-auto"> — для широких экранов

Hover эффекты:
- Все кликабельные карточки: hover:shadow-md transition-shadow duration-150
- Все кнопки уже имеют transition — проверь

Disabled состояния:
- Слайдеры в SimulatorPage при loading: opacity-50 pointer-events-none
- Кнопки при loading: уже обработано в Button компоненте

ЧАСТЬ 3: Консоль браузера — финальная проверка
Открой каждую страницу и убедись:
- Вкладка Console: 0 ошибок, 0 предупреждений
- Вкладка Network: нет failed запросов (красных строк)
- React DevTools: нет предупреждений в компонентах
```

---

### ПРОМПТ 9.2 — Финальный аудит

```
Финальный аудит перед сдачей.

ЧЕКЛИСТ — выполни каждый пункт и поставь ✓:

БЕЗОПАСНОСТЬ И КОНФИГУРАЦИЯ:
□ Нет хардкодированных URL — только import.meta.env.VITE_*
□ .env в .gitignore (проверь git status — не должен быть в staged)
□ .env.example присутствует с плейсхолдерами
□ Нет console.log для дебага (разрешены только console.error в перехватчиках)

КОД:
□ Все компоненты используют опциональные цепочки: data?.field вместо data.field
□ Все списки имеют уникальный key prop
□ useEffect зависимости полные (нет eslint предупреждений)
□ Нет неиспользуемых импортов

ФУНКЦИОНАЛЬНОСТЬ:
□ /dashboard — таблица, фильтры, slide-in панель работают
□ /producer/P1000 — все 6 карточек с данными
□ /simulator — слайдеры нормируются, таблица анимируется
□ /fairness — 4 KPI, Lorenz кривая, Z-score бары
□ /map — карта рендерится, регион panel открывается
□ Экспорт CSV — файл скачивается
□ Pipeline кнопка — success/error toast показывается

СБОРКА:
□ npm run build — 0 ошибок (warnings допустимы)
□ npm run preview — все 5 роутов открываются
□ Бандл не > 2MB (check dist/assets/)

ФИНАЛЬНЫЙ КОММИТ:
git add .
git commit -m "feat: final frontend v1.0 - ready for demo"
git push

СООБЩИ КОМАНДЕ: "Фронт готов. Собирается без ошибок. URL для демо: [vercel url]"
```

---

## БЫСТРЫЕ СОВЕТЫ

### Если что-то сломалось:
1. `npm run dev` → смотри ошибку в терминале, не в браузере
2. Ошибка импорта → проверь путь и регистр файла (Linux чувствителен к регистру)
3. Tailwind классы не применяются → перезапусти dev-сервер

### Когда переключаться на реальный API:
- Бэкендер скажет Railway URL → меняешь VITE_API_URL в .env
- Если CORS ошибка → бэкендеру нужно добавить http://localhost:5173 в allowed origins
- Если данные не совпадают по полям → сравни с mockApi.js и сообщи бэкендеру

### Порядок работы каждый день:
```powershell
cd D:\Decenthrathon\subsidies-scoring\frontend
claude
# закидываешь промпт
# проверяешь в браузере http://localhost:5173
git add . && git commit -m "feat: day X - описание"
```
