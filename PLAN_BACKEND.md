# План разработки + промпты для Claude Code
## 🔵 Бэкендер — FastAPI + деплой + интеграция
## AI для справедливых субсидий — Decentrathon 5.0

> Твоя зона: `backend/main.py`, `backend/routers/`, Dockerfile, Railway
> Запускай `claude` из папки `D:\Decenthrathon\subsidies-scoring\backend`
> Ты начинаешь ПЕРВЫМ в День 1 — инициализируешь монорепо для всей команды.

---

## ДЕНЬ 1 — 27 марта | Монорепо + FastAPI основа | ТЫ НАЧИНАЕШЬ ПЕРВЫМ

### 🎯 Цель дня: монорепо создано, /health работает, ML-щик и фронтендер могут клонировать

---

### ПРОМПТ 1.1 — GitHub монорепо + структура
```
Инициализируй GitHub монорепо для проекта AI субсидий.

Создай структуру папок:
subsidies-scoring/
├── backend/
│   ├── ml/
│   ├── services/
│   ├── routers/
│   ├── models/
│   ├── data/          (пустая, данные не в git)
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── .dockerignore
├── frontend/          (пустая папка с README "P2 zone")
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

# Data
data/*.xlsx
data/*.csv

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

Создай .env.example:
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
GEMINI_API_KEY=AIza...
FRONTEND_URL=https://your-app.vercel.app
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...

Сделай первый git commit: "init: project structure"
Скажи ML-щику и фронтендеру что можно клонировать.
```

---

### ПРОМПТ 1.2 — FastAPI + /health
```
Создай backend/main.py — FastAPI приложение.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime

app = FastAPI(title="AI Субсидии API", version="0.1.0")

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

GET /health должен возвращать:
{
  "status": "ok",
  "db": "checking...",
  "model": "not_loaded",
  "timestamp": datetime.utcnow().isoformat(),
  "version": "0.1.0"
}

Создай backend/requirements.txt:
fastapi
uvicorn[standard]
pandas
numpy
scikit-learn
xgboost
shap
joblib
supabase
google-generativeai
scipy
openpyxl
python-dotenv
httpx

Запусти uvicorn main:app --reload и убедись что /health отвечает 200.
```

---

### ПРОМПТ 1.3 — Dockerfile + Railway конфиг
```
Создай backend/Dockerfile:
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
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

Создай backend/railway.toml:
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

Проверь что Dockerfile собирается локально:
docker build -t subsidies-backend .
```

---

## ДЕНЬ 2 — 28 марта | TypeScript типы + Pipeline endpoint

### 🎯 Цель дня: ML-щик может запустить pipeline через API

---

### ПРОМПТ 2.1 — TypeScript типы для фронтендера
```
Создай frontend/src/types/api.ts — TypeScript интерфейсы.

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

// Полный профиль
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

export interface ShortlistResponse {
  total_producers: number
  hidden_talents_count: number
  avg_ml_score: number
  items: Producer[]
}

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

export interface SimulationWeights {
  completion_rate: number
  approval_rate: number
  diversity: number
  activity: number
  working_hours: number
}

export interface SimulationResult {
  shortlist: Producer[]
  entered: string[]
  left: string[]
  hidden_talent_count: number
  weights_used: SimulationWeights
}

export interface RegionMapData {
  region: string
  avg_ml_score: number
  producer_count: number
  hidden_talent_count: number
  z_score: number
  is_outlier: boolean
}

export interface GeminiAdvice {
  producer_id: string
  score_explanation: string
  baseline_injustice: string
  recommendations: Array<{ action: string; impact: string }>
}

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
Передай файл фронтендеру.
```

---

### ПРОМПТ 2.2 — Pipeline endpoint
```
Создай backend/routers/pipeline.py и подключи к main.py.

POST /api/pipeline/run:
- Запускает run_full_pipeline() из ml/pipeline.py
- Возвращает { "status": "success", "metrics": {...}, "duration_seconds": N }
- Если модель уже загружена — перезагружает
- Обработка ошибок: HTTPException 500 с деталями

Обнови GET /health:
- Если model.pkl существует → "model": "loaded"
- Проверить соединение с Supabase (простой SELECT)

В main.py подключи роутер:
from routers.pipeline import router as pipeline_router
app.include_router(pipeline_router)

Протестируй: curl -X POST http://localhost:8000/api/pipeline/run
```

---

## ДЕНЬ 3 — 29 марта | Shortlist + Producers роутеры | ⚑ СДАЧА #1

### 🎯 Цель дня: /api/shortlist и /api/producers работают, деплой на Railway

---

### ПРОМПТ 3.1 — Shortlist роутер
```
Создай backend/routers/scoring.py.

Жди сигнала от ML-щика что baseline_service.py готов, затем:

GET /api/shortlist?top_n=20:
- Импортирует compute_baseline из ml/baseline_service.py
- Возвращает топ-N по ml_score:
  {
    "total_producers": N,
    "hidden_talents_count": N,
    "avg_ml_score": 0.73,
    "items": [{ producer_id, ml_score, fcfs_rank, ml_rank, delta, hidden_talent, region, direction }]
  }

Подключи в main.py:
from routers.scoring import router as scoring_router
app.include_router(scoring_router, prefix="/api")

Протестируй: curl http://localhost:8000/api/shortlist?top_n=5
```

---

### ПРОМПТ 3.2 — Railway деплой
```
Задеплой backend на Railway.

1. Установи Railway CLI:
npm install -g @railway/cli

2. Логин:
railway login

3. Инициализация:
cd backend
railway init
# Выбери: Create new project → "subsidies-backend"

4. Добавь env переменные (возьми у ML-щика):
railway variables set SUPABASE_URL="..."
railway variables set SUPABASE_KEY="..."
railway variables set GEMINI_API_KEY="..."
railway variables set FRONTEND_URL="https://placeholder.vercel.app"

5. Деплой:
railway up

6. Проверь:
curl https://[railway-url]/health
→ { "status": "ok", "db": "connected" }

Запиши Railway URL — передай фронтендеру для VITE_API_URL.
```

---

### ПРОМПТ 3.3 — Интеграционная проверка #1
```
Проведи первую интеграционную проверку.

1. Railway backend:
   curl https://[railway-url]/health → { "status": "ok", "db": "connected" }

2. Pipeline запущен:
   curl -X POST https://[railway-url]/api/pipeline/run → { "status": "success" }

3. Shortlist работает:
   curl https://[railway-url]/api/shortlist?top_n=5 → { "total_producers": N, "items": [...] }

4. CORS проверка:
   Открой frontend localhost:5173 → DevTools → Network
   Убедись что нет ошибок "CORS policy"

Запиши в docs/integration-log.md что работает, что нет.
```

---

## ДЕНЬ 4 — 30 марта | Producers + Fairness роутеры

### 🎯 Цель дня: полный CRUD по производителям, fairness эндпоинт

---

### ПРОМПТ 4.1 — Producers роутер
```
Создай backend/routers/producers.py.

GET /api/producers:
  Query params: region, direction, talent_only, min_score, page=1, limit=50
  Возвращает:
  {
    "total": N,
    "page": 1,
    "items": [{ producer_id, region, direction, ml_score, ml_rank, fcfs_rank, delta, hidden_talent, total_applications, completion_rate }]
  }

GET /api/producers/{id}:
  Полный профиль:
  {
    producer_id, region, direction, ml_score, ml_rank, fcfs_rank, delta, hidden_talent,
    "shap_values": [топ-5 SHAP факторов],
    "history": [{ month, count, amount, status_breakdown }],
    "stats": { total_applications, completed, approved, rejected, active_months }
  }
  404 если не найден.

GET /api/map/regions:
  [{ region, avg_ml_score, producer_count, hidden_talent_count, z_score, is_outlier }]

GET /api/metrics:
  { roc_auc, avg_precision, best_f1, optimal_threshold, cv_auc_mean, cv_auc_std, train_size, val_size,
    vs_baseline: { fcfs_f1, ml_f1, improvement } }

Подключи в main.py. Проверь что все эндпоинты < 500ms.
```

---

### ПРОМПТ 4.2 — Fairness роутер
```
Создай backend/routers/fairness.py.

Жди сигнала от ML-щика что fairness.py готов, затем:

GET /api/fairness:
- Импортирует compute_fairness_report из ml/fairness.py
- Сначала проверяет кэш в fairness_cache (если свежий < 1ч — отдаёт)
- Иначе считает заново и кэширует
- Возвращает полный fairness отчёт

Подключи в main.py.
Протестируй: curl http://localhost:8000/api/fairness
```

---

### ПРОМПТ 4.3 — Supabase RLS
```
Настрой Supabase RLS для безопасности.

Выполни в Supabase SQL Editor:

-- Включи Realtime для таблицы scores
ALTER PUBLICATION supabase_realtime ADD TABLE scores;

-- Row Level Security
ALTER TABLE producers ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE shap_values ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read" ON producers FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON scores FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON shap_values FOR SELECT USING (true);
CREATE POLICY "Allow backend write" ON producers FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow backend write" ON scores FOR INSERT WITH CHECK (true);

Проверь что фронтенд читает данные через anon key без ошибок.
```

---

## ДЕНЬ 5 — 31 марта | Advisor + Simulator роутеры

### 🎯 Цель дня: все эндпоинты готовы, фронтендер может подключаться

---

### ПРОМПТ 5.1 — Advisor роутер
```
Создай backend/routers/advisor.py.

Жди сигнала от ML-щика что gemini_advisor.py готов, затем:

GET /api/producers/{id}/advice:
- Сначала проверить кэш в gemini_advice (если есть и не старше 24ч — вернуть)
- Если нет — вызвать get_advice() из services/gemini_advisor.py и сохранить
- Если Gemini недоступен → вернуть fallback:
  { "score_explanation": "Совет временно недоступен", "recommendations": [] }

Подключи в main.py. Проверь для демо producer_id от ML-щика.
```

---

### ПРОМПТ 5.2 — Simulator роутер
```
Создай backend/routers/simulator.py.

Жди сигнала от ML-щика что simulator_service.py готов, затем:

POST /api/simulate:
  Body:
  {
    "weights": {
      "completion_rate": 0.35,
      "approval_rate": 0.25,
      "diversity": 0.20,
      "activity": 0.10,
      "working_hours": 0.10
    },
    "top_n": 20
  }
  - Вызывает simulate() из ml/simulator_service.py
  - Автоматически нормирует weights если сумма != 1
  - Возвращает ShortlistResult

Подключи в main.py.
Протестируй с разными весами — убедись что entered/left не пустые.
```

---

### ПРОМПТ 5.3 — Финальная проверка всех эндпоинтов
```
Проведи полную проверку всех API эндпоинтов.

Скрипт для автопроверки:
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

Всё что > 500ms — оптимизируй (добавь кэширование или индексы в Supabase).
Запиши результаты в docs/api-performance.md.
```

---

## ДЕНЬ 6 — 1 апреля | Vercel деплой фронтенда

### 🎯 Цель дня: фронтенд на Vercel, CORS настроен для прода

---

### ПРОМПТ 6.1 — Vercel деплой
```
Задеплой frontend фронтендера на Vercel.

1. npm install -g vercel
2. cd frontend && vercel
   - Framework: Vite
   - Build: npm run build
   - Output: dist

3. Добавь env переменные в Vercel:
vercel env add VITE_API_URL production
# Введи: https://[railway-url]
vercel env add VITE_SUPABASE_URL production
vercel env add VITE_SUPABASE_ANON_KEY production

4. Продакшн деплой:
vercel --prod

5. Получи Vercel URL → обнови FRONTEND_URL в Railway:
railway variables set FRONTEND_URL="https://[vercel-url]"
railway up  # редеплой с новым CORS

6. Проверь что нет CORS ошибок на живом сайте.
```

---

### ПРОМПТ 6.2 — Интеграционная проверка #2
```
Проведи финальную интеграционную проверку на живых URL.

1. /dashboard → KPI карточки с реальными числами
2. Клик на строку таблицы → slide-in панель с SHAP
3. /producer/[demo_id] → SHAP chart + Gemini совет
4. /simulator → слайдеры работают, шортлист меняется
5. /fairness → Lorenz кривая + Z-score chart
6. /map → карта Казахстана с хороплетом

Все проблемы → исправь немедленно.
Обнови README.md с живыми URL Railway и Vercel.
```

---

## ДЕНЬ 7 — 2 апреля | Demo сценарий + Edge cases | ⚑ СДАЧА #2

---

### ПРОМПТ 7.1 — Edge cases
```
Проверь все edge cases перед сдачей #2.

1. GET /api/producers/{несуществующий_id} → 404 с понятным сообщением
2. Gemini недоступен → fallback JSON (не 500 ошибка)
3. POST /api/simulate с weights != 1 → автоматически нормирует
4. POST /api/pipeline/run когда модель уже загружена → перезагружает без ошибки

Пройдись по Swagger /docs — все эндпоинты задокументированы.
```

---

## ДНИ 9-10 — 4-5 апреля | Финал | ⚑ 23:59

---

### ПРОМПТ 9.1 — Финальный чеклист
```
Проведи финальную проверку за 2 часа до дедлайна.

BACKEND (Railway):
□ GET /health → { status: ok, db: connected, model: loaded }
□ GET /api/shortlist?top_n=20 → 20 элементов
□ GET /api/producers?talent_only=true → только hidden_talent=true
□ GET /api/producers/[demo_id] → полный профиль с shap_values
□ GET /api/producers/[demo_id]/advice → Gemini текст
□ GET /api/fairness → gini, lorenz, kruskal данные
□ GET /api/map/regions → 17 регионов
□ POST /api/simulate → entered/left не пустые

GITHUB:
□ Нет .env файлов в репо
□ Нет data/*.xlsx в репо
□ Нет model.pkl в репо
□ Тег v1.0 создан

Финальный коммит: "feat: final backend v1.0"
```

---

## СОВЕТЫ ПО РАБОТЕ С CLAUDE CODE

### Запускай claude из папки backend:
```powershell
cd D:\Decenthrathon\subsidies-scoring\backend
claude
```

### Синк с ML-щиком:
Ты подключаешь то что он пишет. Чеклист зависимостей:
- `baseline_service.py` готов → подключаешь `/api/shortlist`
- `fairness.py` готов → подключаешь `/api/fairness`
- `gemini_advisor.py` готов → подключаешь `/api/producers/{id}/advice`
- `simulator_service.py` готов → подключаешь `/api/simulate`

### Если ML-щик ещё не закончил модуль:
```
Создай заглушку для /api/fairness — возвращает мок данные.
Когда ML-щик закончит fairness.py — заменю заглушку на реальный вызов.
```

### Порядок работы каждый день:
1. `cd backend && claude`
2. Закинь промпт
3. Проверь: `curl http://localhost:8000/health`
4. `git add . && git commit -m "feat: day X - описание"`
