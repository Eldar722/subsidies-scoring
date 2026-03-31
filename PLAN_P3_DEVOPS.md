# План разработки + промпты для Claude Code
## 🟢 P3 — Full-stack / DevOps
## AI для справедливых субсидий — Decentrathon 5.0

> Твоя роль: мост между P1 и P2. Работаешь в корне монорепо.
> Запускай `claude` из папки `D:\Decenthrathon\subsidies-scoring`
> Промпты закидывай последовательно. Ты первый кто начинает работу — День 1 критически важен для P1 и P2.

---

## ДЕНЬ 1 — 27 марта | GitHub + окружение + CORS | ТЫ НАЧИНАЕШЬ ПЕРВЫМ

### 🎯 Цель дня: монорепо настроено, P1 и P2 могут начать работу

---

### ПРОМПТ 1.1 — GitHub монорепо
```
Инициализируй GitHub монорепо для проекта AI субсидий.

Создай структуру папок в корне:
subsidies-scoring/
├── backend/          (P1 зона — не трогать)
├── frontend/         (P2 зона — не трогать)
├── ml/               (P1 зона — ноутбуки EDA)
├── data/             (xlsx файлы — не в git)
├── docs/
│   ├── architecture.md
│   └── demo_script.md
├── .gitignore
├── .env.example
└── README.md

Создай .gitignore:
# Python
__pycache__/
*.pyc
venv/
.env
*.pkl

# Node
node_modules/
dist/
.env.local

# Data (не коммитим реальные данные)
data/*.xlsx
data/*.csv

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

Создай .env.example с плейсхолдерами:
# Backend (P1)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
GEMINI_API_KEY=AIza...
FRONTEND_URL=https://your-app.vercel.app

# Frontend (P2)
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...

Создай пустой README.md с заголовком и структурой проекта.
Сделай первый git commit: "init: project structure"
```

---

### ПРОМПТ 1.2 — CORS в FastAPI
```
Настрой CORS в backend/main.py для P1.

Добавь в main.py (P1 уже создал его или создай сам если нет):

from fastapi.middleware.cors import CORSMiddleware
import os

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Также добавь в GET /health дополнительные поля:
{
  "status": "ok",
  "db": "checking...",
  "model": "not_loaded",
  "timestamp": "ISO datetime",
  "version": "0.1.0"
}

Протестируй CORS: запусти backend на 8000, frontend dev на 5173,
убедись что fetch('http://localhost:8000/health') из браузера не даёт CORS ошибку.
```

---

### ПРОМПТ 1.3 — TypeScript типы
```
Создай frontend/src/types/api.ts — TypeScript интерфейсы на основе API.

// Производитель
export interface Producer {
  producer_id: string
  region: string
  direction: string
  total_applications: number
  completion_rate: number
  ml_score: number
  ml_rank: number
  fcfs_rank: number
  delta: number
  hidden_talent: boolean
}

// SHAP фактор
export interface ShapValue {
  feature: string
  feature_label: string
  shap_value: number
  feature_value: number
}

// Полный профиль производителя
export interface ProducerDetail extends Producer {
  shap_values: ShapValue[]
  history: MonthlyHistory[]
  stats: ProducerStats
}

export interface MonthlyHistory {
  month: string
  count: number
  amount: number
  status_breakdown: Record<string, number>
}

export interface ProducerStats {
  total_applications: number
  completed: number
  approved: number
  rejected: number
  active_months: number
}

// Шортлист
export interface ShortlistItem extends Producer {}
export interface ShortlistResponse {
  total_producers: number
  hidden_talents_count: number
  avg_ml_score: number
  items: ShortlistItem[]
}

// Fairness
export interface FairnessData {
  gini_scores: number
  gini_amounts: number
  lorenz_scores: Array<{ x: number; y: number }>
  kruskal_regions: { H: number; p_value: number; interpretation: string }
  kruskal_directions: { H: number; p_value: number; interpretation: string }
  region_z_scores: Record<string, { mean_score: number; z_score: number; outlier: boolean }>
  direction_z_scores: Record<string, { mean_score: number; z_score: number; outlier: boolean }>
  heatmap: Array<{ region: string; direction: string; avg_score: number }>
}

// Симулятор
export interface SimulationWeights {
  completion_rate: number
  approval_rate: number
  diversity: number
  activity: number
  working_hours: number
}

export interface SimulationResult {
  shortlist: ShortlistItem[]
  entered: string[]
  left: string[]
  hidden_talent_count: number
  weights_used: SimulationWeights
}

// Карта
export interface RegionMapData {
  region: string
  avg_ml_score: number
  producer_count: number
  hidden_talent_count: number
  z_score: number
  is_outlier: boolean
}

// Gemini совет
export interface GeminiAdvice {
  producer_id: string
  score_explanation: string
  baseline_injustice: string
  recommendations: Array<{ action: string; impact: string }>
}

// Метрики модели
export interface ModelMetrics {
  roc_auc: number
  avg_precision: number
  best_f1: number
  optimal_threshold: number
  cv_auc_mean: number
  cv_auc_std: number
  train_size: number
  val_size: number
  vs_baseline: { fcfs_f1: number; ml_f1: number; improvement: number }
}

Покажи что файл создан без TypeScript ошибок.
```

---

## ДЕНЬ 2 — 28 марта | Railway + Vercel аккаунты

### 🎯 Цель дня: деплой платформы настроены, P1 и P2 могут деплоить

---

### ПРОМПТ 2.1 — Railway конфигурация
```
Подготовь конфигурацию Railway для backend.

Создай backend/railway.toml (если ещё нет):
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

Создай backend/Dockerfile (если ещё нет):
FROM python:3.11-slim

WORKDIR /app

# Зависимости отдельно для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY . .

# Не копируем data/ и model.pkl (они в .dockerignore)
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

Создай backend/.dockerignore:
__pycache__
*.pyc
venv/
.env
data/
*.pkl
.git

Список env переменных для Railway (запиши — будешь добавлять в панели Railway):
- SUPABASE_URL
- SUPABASE_KEY
- GEMINI_API_KEY
- FRONTEND_URL

Проверь что Dockerfile собирается локально:
docker build -t subsidies-backend ./backend
```

---

### ПРОМПТ 2.2 — README v0
```
Напиши README.md для корня монорепо — версия v0 (базовая структура).

Включи:

# AI для справедливых субсидий
### Decentrathon 5.0 · AI for Government · inDrive × Astana Hub

## Быстрый старт

### Backend
\`\`\`bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # заполни ключи
uvicorn main:app --reload
\`\`\`

### Frontend
\`\`\`bash
cd frontend
npm install
cp .env.example .env  # заполни VITE_API_URL
npm run dev
\`\`\`

### Обучение модели
\`\`\`bash
# Поместить subsidies.xlsx в backend/data/
curl -X POST http://localhost:8000/api/pipeline/run
\`\`\`

## Архитектура
[Вставь ASCII схему из ARCHITECTURE.md]

## Команда
- P1: ML/Backend — FastAPI, scikit-learn, SHAP, Supabase
- P2: Frontend — React 18, Recharts, React-Leaflet, Framer Motion
- P3: Full-stack/DevOps — интеграция, Railway, Vercel

## Переменные окружения
[таблица всех переменных с описанием]

## Деплой
- Backend: Railway — [URL будет здесь]
- Frontend: Vercel — [URL будет здесь]

Сохрани README.md. Коммит: "docs: add README v0"
```

---

## ДЕНЬ 3 — 29 марта | Первый деплой + интеграция | ⚑ СДАЧА #1

### 🎯 Цель дня: /health работает на Railway, P2 таблица получает реальные данные

---

### ПРОМПТ 3.1 — Деплой backend на Railway
```
Задеплой backend P1 на Railway.

Инструкции (выполни по порядку):

1. Установи Railway CLI:
npm install -g @railway/cli

2. Логин:
railway login

3. Инициализация проекта:
cd backend
railway init
# Выбери: Create new project → "subsidies-backend"

4. Добавь env переменные в Railway (через CLI):
railway variables set SUPABASE_URL="значение от P1"
railway variables set SUPABASE_KEY="значение от P1"
railway variables set GEMINI_API_KEY="значение от P1"
railway variables set FRONTEND_URL="https://placeholder.vercel.app"

5. Деплой:
railway up

6. Получи URL:
railway domain

7. Проверь healthcheck:
curl https://[railway-url]/health

Ожидаемый ответ:
{ "status": "ok", "db": "connected", "model": "not_loaded" }

Если деплой упал — покажи логи:
railway logs

Обнови VITE_API_URL у P2 на полученный Railway URL.
Запиши URL в README.md.
```

---

### ПРОМПТ 3.2 — Интеграционная проверка #1
```
Проведи первую интеграционную проверку.

Чеклист (проверь каждый пункт):

1. Railway backend:
   curl https://[railway-url]/health
   → { "status": "ok", "db": "connected" }

2. P1 pipeline запущен:
   curl -X POST https://[railway-url]/api/pipeline/run
   → { "status": "success", "metrics": {...} }

3. Shortlist работает:
   curl https://[railway-url]/api/shortlist?top_n=5
   → { "total_producers": N, "items": [...] }

4. Frontend P2 (localhost:5173):
   - Открой DevTools → Network
   - Перейди на /dashboard
   - Убедись что запрос к /api/producers возвращает 200
   - Убедись что таблица рендерится с реальными данными (не mock)

5. CORS проверка:
   - В консоли браузера НЕ должно быть ошибок "CORS policy"

Если что-то не работает — исправь и перепроверь.
Запиши в docs/integration-log.md что работает, что нет.
```

---

## ДЕНЬ 4 — 30 марта | Supabase Realtime + интеграция ProducerPage

---

### ПРОМПТ 4.1 — Supabase Realtime настройка
```
Настрой Supabase Realtime для live обновлений.

В Supabase SQL Editor выполни (дай SQL команды):

-- Включи Realtime для таблицы scores
ALTER PUBLICATION supabase_realtime ADD TABLE scores;

-- Row Level Security (RLS) — разрешить чтение для анонимных пользователей
ALTER TABLE producers ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE shap_values ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read" ON producers FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON scores FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON shap_values FOR SELECT USING (true);

-- Только backend может писать (через service key)
CREATE POLICY "Allow backend write" ON producers 
  FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow backend write" ON scores 
  FOR INSERT WITH CHECK (true);

Проверь что P2 useRealtimeScores hook работает:
- Временно обнови одну запись в scores через Supabase Dashboard
- Убедись что строка на Dashboard мигает зелёным

Если Realtime не работает — проверь VITE_SUPABASE_URL и VITE_SUPABASE_ANON_KEY у P2.
```

---

### ПРОМПТ 4.2 — Интеграция ProducerPage
```
Проверь интеграцию ProducerPage P2 с API P1.

1. Возьми один из демо producer_id от P1 (например тот что дал скрытый талант).

2. Проверь API напрямую:
   curl https://[railway-url]/api/producers/[producer_id]
   → должен вернуть полный профиль с shap_values, history, stats

3. В браузере перейди на /producer/[producer_id]:
   - Заголовок рендерится с ID, регионом, направлением?
   - SHAP BarChart отображается (зелёные/красные бары)?
   - History LineChart отображается?
   - ML vs FCFS блок показывает правильные ранги?

4. Проверь Gemini совет:
   curl https://[railway-url]/api/producers/[producer_id]/advice
   → должен вернуть { score_explanation, baseline_injustice, recommendations }
   
   В браузере: текст совета отображается в синей карточке?

5. Если что-то не стыкуется между P1 API и P2 UI — зафикси проблему в GitHub Issues:
   Название: "Integration: ProducerPage - [описание проблемы]"
   Назначь на P1 или P2 в зависимости от причины.

Запиши все найденные проблемы и статус их решения.
```

---

## ДЕНЬ 5 — 31 марта | Полная интеграционная проверка

---

### ПРОМПТ 5.1 — Проверка всех эндпоинтов
```
Проведи полную проверку всех API эндпоинтов.

Для каждого эндпоинта измерь время ответа и проверь корректность данных:

1. GET /health → < 100ms
2. GET /api/metrics → < 200ms, содержит roc_auc > 0.6
3. GET /api/shortlist?top_n=20 → < 500ms, 20 элементов
4. GET /api/producers → < 500ms, пагинация работает
5. GET /api/producers?region=Алматы → < 500ms, только нужный регион
6. GET /api/producers?talent_only=true → < 500ms, только hidden_talent=true
7. GET /api/producers/{id} → < 500ms, полный профиль
8. GET /api/producers/{id}/advice → < 3000ms (Gemini может быть медленный)
9. GET /api/fairness → < 1000ms, содержит gini, kruskal, lorenz
10. GET /api/map/regions → < 500ms, 17 регионов
11. POST /api/simulate → < 500ms, entered и left не пустые

Создай простой скрипт для автопроверки:
\`\`\`bash
#!/bin/bash
BASE="https://[railway-url]"
check() { 
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -m 5 "$BASE$1")
  TIME=$(curl -s -o /dev/null -w "%{time_total}" -m 5 "$BASE$1")
  echo "$1: HTTP $STATUS в ${TIME}s"
}
check "/health"
check "/api/metrics"
check "/api/shortlist?top_n=20"
check "/api/producers"
check "/api/fairness"
check "/api/map/regions"
\`\`\`

Результаты: запиши в docs/api-performance.md.
Всё что > 500ms — создай GitHub Issue для P1.
```

---

### ПРОМПТ 5.2 — GitHub Issues + синк команды
```
Создай GitHub Issues для отслеживания прогресса.

1. Создай labels в GitHub:
   - backend (синий)
   - frontend (фиолетовый)
   - integration (оранжевый)
   - bug (красный)
   - ready-for-review (зелёный)

2. Создай milestones:
   - "Этап #1" → 29 марта
   - "Этап #2" → 2 апреля
   - "Финал" → 5 апреля

3. Создай Issues для оставшихся задач по чекпоинту #2:
   - "P2: FairnessPage реализация" → assignee P2, milestone Этап #2
   - "P2: SimulatorPage с Framer Motion" → assignee P2, milestone Этап #2
   - "P2: MapPage с React-Leaflet" → assignee P2, milestone Этап #2
   - "P1: POST /api/simulate эндпоинт" → assignee P1, milestone Этап #2
   - "P3: Vercel деплой frontend" → assignee P3, milestone Этап #2
   - "P3: demo-видео v1" → assignee P3, milestone Этап #2

4. Напиши сообщение для командного чата (сфорулируй):
   "✅ Backend на Railway: [URL]
   ✅ Shortlist API работает
   ✅ Dashboard таблица с реальными данными
   
   Статус: Этап #1 выполнен 🎯
   
   P1, нужно: POST /api/simulate к 1 апреля
   P2, нужно: SimulatorPage + FairnessPage к 2 апреля
   P3 (я): Vercel деплой + demo-видео к 2 апреля"
```

---

## ДЕНЬ 6 — 1 апреля | Vercel деплой + финальная интеграция

---

### ПРОМПТ 6.1 — Vercel деплой
```
Задеплой frontend P2 на Vercel.

1. Установи Vercel CLI:
npm install -g vercel

2. Логин:
vercel login

3. Перейди в frontend и задеплой:
cd frontend
vercel

Настройки при первом деплое:
- Framework: Vite
- Build command: npm run build
- Output dir: dist
- Root dir: ./

4. Добавь env переменные в Vercel:
vercel env add VITE_API_URL production
# Введи: https://[railway-url]

vercel env add VITE_SUPABASE_URL production
vercel env add VITE_SUPABASE_ANON_KEY production

5. Продакшн деплой:
vercel --prod

6. Получи URL и проверь:
- / → редирект на /dashboard ✓
- /dashboard → таблица с данными ✓
- /producer/[demo_id] → профиль ✓
- /simulator → слайдеры ✓
- /fairness → графики ✓
- /map → карта ✓

7. Обнови FRONTEND_URL в Railway:
railway variables set FRONTEND_URL="https://[vercel-url]"
railway up  # редеплой backend с новым CORS

Обнови README.md с живыми URL обоих деплоев.
```

---

### ПРОМПТ 6.2 — Полная интеграционная проверка #2
```
Проведи финальную интеграционную проверку на живых URL.

Тест полного flow (как будет показывать жюри):

1. Открой https://[vercel-url]/dashboard
   - Загружаются данные? (не Skeleton бесконечно)
   - KPI карточки показывают реальные числа?
   - Таблица показывает производителей с delta и badge?

2. Нажми на строку таблицы → slide-in панель
   - Открывается панель с SHAP превью?
   - Кнопка "Открыть профиль" работает?

3. Перейди на /producer/[demo_hidden_talent_id]
   - SHAP BarChart отображается?
   - Gemini совет загружается (может быть медленно)?
   - ML vs FCFS блок показывает разницу?

4. Перейди на /simulator
   - Слайдеры двигаются?
   - Шортлист обновляется?
   - Framer Motion анимация работает?

5. Перейди на /fairness
   - 4 KPI карточки с Gini и KW?
   - Lorenz кривая отображается?

6. Перейди на /map
   - Карта Казахстана загружается?
   - Регионы окрашены хороплетом?

Записывай всё что не работает → GitHub Issues → исправь сегодня же.
```

---

## ДЕНЬ 7 — 2 апреля | Demo-видео | ⚑ СДАЧА #2

---

### ПРОМПТ 7.1 — Demo сценарий
```
Создай docs/demo_script.md — сценарий для demo-видео.

Видео: 2-3 минуты. Показываем живой сайт.

\`\`\`markdown
# Demo Script — AI для справедливых субсидий

## Вступление (15 сек)
"Система ML-скоринга для замены принципа FCFS в распределении 
субсидий животноводства Казахстана. Реальные данные: 36 653 заявки."

## Dashboard (45 сек)
1. Открыть /dashboard
2. Показать KPI: "15 008 производителей, 2847 скрытых талантов"
3. Указать на колонку Delta: "FCFS несправедлив — вот наглядно"
4. Найти производителя с delta > 20: "ML считает его на 25 позиций выше FCFS"
5. Кликнуть — открыть slide-in панель с SHAP превью

## Producer Profile (45 сек)
1. Открыть профиль скрытого таланта
2. SHAP BarChart: "Вот почему такой балл — три главных фактора"
3. Gemini совет: "AI объясняет на русском языке"
4. ML vs FCFS блок: "ML ранг #12, FCFS ранг #387 — вот несправедливость"

## Simulator (30 сек)
1. Перейти на /simulator
2. Увеличить вес "Результативности" — показать как шортлист меняется
3. Framer Motion анимация: "Вошли +5, вышли -5"
4. "Доля скрытых талантов выросла с 35% до 52%"

## Fairness (20 сек)
1. Перейти на /fairness
2. Gini: "0.34 — умеренное неравенство"
3. Lorenz кривая: "Наш ML распределяет справедливее чем FCFS"

## Финал (15 сек)
"Human-in-the-loop: система помогает комиссии, не заменяет её.
Деплой: Railway + Vercel. Реальные данные."
\`\`\`

Теперь запиши видео по этому сценарию (Loom рекомендуется).
Требования:
- Разрешение: минимум 1080p
- Голосовое объяснение (можно русский)
- Показывай живой сайт, не slides
- Длина: 2-3 минуты

Ссылку на видео добавь в README.md.
```

---

### ПРОМПТ 7.2 — README v1 финал этапа #2
```
Обнови README.md до версии v1 для сдачи Этапа #2.

Структура:

# AI для справедливых субсидий 🌾
**Decentrathon 5.0 · AI for Government · inDrive × Astana Hub**

[![Demo Video](badge)](ссылка_на_видео)
[![Backend](badge)](railway_url)
[![Frontend](badge)](vercel_url)

## 🚀 Запуск за 3 команды
\`\`\`bash
git clone [repo_url] && cd subsidies-scoring
cd backend && pip install -r requirements.txt && cp .env.example .env
uvicorn main:app --reload  # затем POST /api/pipeline/run
\`\`\`

## 🎯 Что решает
FCFS (первый подал — первый получил) несправедлив.
ML модель находит производителей которые FCFS системно недооценивает.

## 📊 Метрики модели
| Метрика | FCFS Baseline | Наша ML |
|---------|---------------|---------|
| ROC-AUC | 0.50 | [реальное значение] |
| F1 Score | 0.52 | [реальное значение] |
| Валидация | — | Temporal: train 2025 → val 2026 |

## 🏗 Архитектура
[ASCII схема из ARCHITECTURE.md]

## 📋 API
| Endpoint | Описание |
|----------|----------|
| GET /health | Статус системы |
| GET /api/shortlist | Топ-N с delta и hidden talent |
| GET /api/producers/{id} | Полный профиль + SHAP |
| GET /api/fairness | Gini + Kruskal-Wallis |
| POST /api/simulate | Симулятор весов |

## 🔑 Переменные окружения
[таблица из .env.example с описаниями]

## 👥 Команда
[имена и роли]

GitHub тег v0.2 после финализации.
```

---

## ДНИ 9-10 — 4-5 апреля | Финал | ⚑ 23:59

---

### ПРОМПТ 9.1 — Финальное demo-видео
```
Запиши финальное demo-видео (2-3 мин) на живом Vercel URL.

Используй сценарий из docs/demo_script.md.
Убедись что перед записью:
- Supabase заполнен (данные свежие)
- Gemini совет кэширован для демо-производителей (не ждёт долго)
- Все 5 страниц загружаются без ошибок
- Framer Motion анимация в симуляторе работает

Инструмент: Loom (loom.com) — бесплатно, без установки.
После записи: скопируй ссылку и добавь в README.md в секцию "Demo".

Также добавь screenshot дашборда в README.md:
![Dashboard Screenshot](docs/screenshot-dashboard.png)
```

---

### ПРОМПТ 9.2 — Финальный README
```
Напиши финальный README.md версии v1.0.

Добавь к существующему:

## 📈 Детали модели (Model Card)

### Данные
- Источник: subsidy.plem.kz (официальный реестр МСХ РК)
- Размер: 36 653 заявки, 15 008 уникальных производителей
- Период: январь 2025 — март 2026

### Обучение
- Алгоритм: GradientBoostingClassifier + CalibratedClassifierCV (isotonic)
- Train: данные 2025 (32 723 заявки)
- Validation: temporal holdout 2026 (3 928 заявок)
- Признаки: 24 (временные, финансовые, категориальные, агрегаты)

### Результаты
[реальные метрики из /api/metrics]

### Ограничения
- Модель обучена только на животноводстве РК
- Distribution shift: train 82% positive → val 51% positive
- Не учитывает качество и здоровье животных
- Инструмент поддержки решений, не автоматический вердикт

## ⚖️ Fairness
- Gini коэффициент баллов: [реальное значение]
- Kruskal-Wallis по регионам: p=[значение]
- Kruskal-Wallis по направлениям: p=[значение]

## 🔒 Приватность
- producer_id = первые 11 цифр номера заявки (обезличено)
- Реальные ФИО и данные юрлиц не хранятся
- Supabase RLS настроен

Коммит: "docs: final README v1.0"
GitHub тег: v1.0
```

---

### ПРОМПТ 9.3 — Финальный чеклист перед сдачей
```
Проведи финальную проверку за 2 часа до дедлайна.

Запусти этот чеклист:

BACKEND (Railway):
□ GET https://[railway-url]/health → { status: ok, db: connected, model: loaded }
□ GET /api/shortlist?top_n=20 → 20 элементов
□ GET /api/producers?talent_only=true → только hidden_talent=true
□ GET /api/producers/[demo_id] → полный профиль с shap_values
□ GET /api/producers/[demo_id]/advice → Gemini текст
□ GET /api/fairness → gini, lorenz, kruskal данные
□ GET /api/map/regions → 17 регионов
□ POST /api/simulate → entered/left не пустые

FRONTEND (Vercel):
□ / → редирект на /dashboard
□ /dashboard → KPI + таблица с реальными данными
□ /dashboard?region=X → фильтрация работает
□ /producer/[demo_id] → SHAP chart + Gemini совет
□ /simulator → слайдеры + Framer Motion анимация
□ /fairness → Lorenz кривая + Z-score chart
□ /map → хороплет окрашен

README:
□ Ссылка на demo-видео работает
□ Ссылки на Railway и Vercel живые
□ Команда запуска работает с нуля (проверь в чистом окружении)
□ Метрики модели реальные (не placeholder)

GITHUB:
□ Тег v1.0 создан
□ Нет .env файлов в репо
□ Нет data/*.xlsx в репо
□ Нет model.pkl в репо

Всё что красное — исправь немедленно и перепроверь.
```

---

## СОВЕТЫ ПО РАБОТЕ С CLAUDE CODE (для P3)

### Запускай claude из корня монорепо:
```powershell
cd D:\Decenthrathon\subsidies-scoring
claude
```

### Твоя главная задача — разблокировать команду:
Если P1 или P2 что-то не стыкуется — это твоя задача исправить.

**Типичная ситуация — P2 получает CORS ошибку:**
```
P2 получает CORS ошибку при запросе к Railway URL.
Backend URL: https://xxx.railway.app
Frontend URL: https://yyy.vercel.app
Исправь CORS настройки в backend/main.py и задеплой.
```

**Типичная ситуация — данные не совпадают:**
```
P2 ожидает поле "ml_score" в ответе, P1 возвращает "score".
Исправь в api.js у P2 или попроси P1 поменять название поля.
Опиши оба варианта и какой быстрее.
```

**Типичная ситуация — Vercel не собирается:**
```
npm run build выдаёт ошибку: [вставь ошибку].
Исправь и задеплой снова.
```

### Коммит соглашения:
```
feat: описание новой функции
fix: исправление бага
docs: обновление документации
deploy: изменения деплоя
chore: технические задачи
```

### Порядок работы каждый день:
1. Утром: синк с P1 и P2 — что сделано, что заблокировано
2. Запусти `claude` в нужной папке
3. Разреши блокеры, задеплой если нужно
4. Вечером: обнови README, создай Issues для завтра
5. `git add . && git commit -m "chore: day X sync"`
