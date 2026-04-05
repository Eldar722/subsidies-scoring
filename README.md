# SubsidyLens — Система ML-скоринга субсидий для сельского хозяйства

> **Decentrathon 5.0 · Кейс №2: Система скоринга для сельского хозяйства**

## Обзор

SubsidyLens — система машинного обучения для объективного ранжирования сельхозпроизводителей при распределении государственных субсидий на животноводство в Республике Казахстан. Система заменяет принцип «первый подал — первый получил» (FCFS) на прозрачный, объяснимый и воспроизводимый скоринг, основанный на анализе исторических данных.

## Текущие метрики

| Метрика | Значение | Порог |
|---------|----------|-------|
| **Hold-out ROC-AUC (2026)** | 0.7439 | ≥ 0.72 ✅ |
| **GroupKFold CV AUC (2025)** | 0.9769 ± 0.0017 | — |
| **F1-Score** | 0.7460 | — |
| **Precision** | 0.6828 | — |
| **Recall** | 0.8222 | — |
| **Точность (Accuracy)** | 0.7117 | — |

**Сравнение с baseline FCFS:**

| Метрика | FCFS | SubsidyLens | Улучшение |
|---------|------|-------------|-----------|
| ROC-AUC | 0.61 | 0.74 | +21% |
| F1-Score | ~0.52 | 0.75 | +44% |
| Ложные одобрения (FP) | ~422 | 262 | −38% |

## Ключевые компоненты

### ML-модель

| Параметр | Значение |
|----------|----------|
| Алгоритм | XGBoost + Isotonic Calibration |
| Количество признаков | 32 (24 базовых + 8 v7) |
| Валидация | GroupKFold (по producer_id) + temporal holdout 2026 |
| Seed | 42 (полная воспроизводимость) |
| Качество | ROC-AUC ≥ 0.72 (quality gate) |

### Объяснимость

- **SHAP:** Топ-5 факторов влияния для каждого производителя
- **Контрфактуальный анализ:** «Что изменить для одобрения»
- **Риск-индикаторы:** 6 типов сигналов (поведенческие, финансовые, региональные)
- **AI-советник:** Рекомендации на русском языке (Groq / Gemini)

### Production-готовность

- Атомарное обновление модели (backup → tmp → replace → verify)
- Автоматический rollback при деградации метрик
- Rate limiting на всех 35+ эндпоинтах
- Thread-safe обработка запросов (RLock)
- Реестр версий моделей в PostgreSQL
- Batch-синхронизация с Supabase (500× ускорение)

## Быстрый старт

### Предварительные требования

- Python 3.12+
- Node.js 20+
- Заполненный `backend/.env` (см. `backend/.env.example`)

### Запуск backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Проверка: `curl http://127.0.0.1:8000/health`

### Запуск frontend

```bash
cd frontend
npm install
npm run dev
```

Откройте: `http://localhost:5173`

### Переобучение модели

```bash
cd backend
python train.py
```

Модель сохраняется автоматически при прохождении quality gate (ROC-AUC ≥ 0.72). Синхронизация с Supabase происходит автоматически после обучения.

## Структура проекта

```
subsidies-scoring/
├── backend/
│   ├── main.py                    # FastAPI приложение (35+ эндпоинтов)
│   ├── train.py                   # ML-пайплайн: загрузка → обучение → сохранение
│   │
│   ├── core/
│   │   ├── config.py              # Конфигурация, валидация env
│   │   ├── state.py               # Глобальное состояние модели (thread-safe)
│   │   └── rate_limits.py         # Лимиты запросов
│   │
│   ├── ml/
│   │   ├── scoring.py             # Скоринг DataFrame
│   │   ├── shap_service.py        # SHAP-объяснения
│   │   ├── counterfactual.py      # Контрфактуальный анализ
│   │   ├── risk_indicators.py     # Индикаторы риска (6 типов)
│   │   ├── fairness.py            # Gini, Lorenz, Kruskal-Wallis
│   │   ├── drift_monitor.py       # Мониторинг дрейфа (PSI, Mahalanobis)
│   │   └── sync_to_supabase.py    # Синхронизация с БД
│   │
│   ├── services/
│   │   ├── supabase_service.py    # Атомарные записи в PostgreSQL
│   │   ├── gemini.py              # AI-советник (Groq + Gemini)
│   │   ├── model_registry.py      # Реестр версий моделей
│   │   └── model_storage.py       # Хранилище артефактов
│   │
│   └── routers/                   # API-маршруты
│       ├── producers.py           # Профили производителей
│       ├── shortlist.py           # Шортлист
│       ├── fairness.py            # Анализ справедливости
│       ├── simulate.py            # Симулятор весов
│       ├── drift.py               # Мониторинг дрейфа
│       ├── counterfactual.py      # Контрфактуалы
│       ├── model_management.py    # Управление моделями
│       └── ...
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── DashboardPage.jsx  # Главная: метрики, KPI, шортлист
│       │   ├── ProducerPage.jsx   # Профиль: SHAP, AI, риск, история
│       │   ├── FairnessPage.jsx   # Gini, Lorenz, Z-score, Heatmap
│       │   ├── SimulatorPage.jsx  # Симулятор весов
│       │   ├── MapPage.jsx        # Карта регионов
│       │   └── AnalyticsPage.jsx  # Аналитика
│       └── ...
│
├── docs/supabase_migrations/      # Миграции БД
├── ARCHITECTURE.md                # Архитектура системы
└── README.md                      # Этот файл
```

## API Endpoints

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/health` | Проверка работоспособности |
| GET | `/api/metrics` | Метрики модели (AUC, F1, Precision, Recall) |
| GET | `/api/stats` | Статистика датасета |
| GET | `/api/shortlist?top_n=20` | Топ-N производителей |
| GET | `/api/shortlist/fair` | Справедливое ранжирование |
| GET | `/api/producers/{id}` | Профиль + SHAP + история |
| GET | `/api/producers/{id}/risk` | Индикаторы риска |
| GET | `/api/producers/{id}/advice` | AI-советник |
| GET | `/api/producers/{id}/counterfactual` | Контрфактуальные рекомендации |
| POST | `/api/simulate` | Симуляция с весами |
| GET | `/api/fairness` | Gini, Lorenz, Kruskal-Wallis |
| GET | `/api/drift/status` | Статус дрейфа модели |
| POST | `/api/pipeline/run` | Переобучение модели |
| GET | `/api/models` | Реестр моделей |
| POST | `/api/models/rollback` | Откат модели |

## Датасет

| Параметр | Значение |
|----------|----------|
| Заявок всего | 36 653 |
| Завершённых | 25 985 |
| Уникальных производителей | 15 009 |
| Регионов | 18 |
| Направлений животноводства | 9 |
| Период | Январь 2025 — Март 2026 |
| Доля исполненных (2025) | 82.4% |
| Доля исполненных (2026) | 51.5% |

## Безопасность

- Переменные окружения хранятся только локально (`.env` не в git)
- Ключи API не передаются на frontend
- SUPABASE_JWT_SECRET обязателен для production
- Rate limiting: 5–120 запросов/мин в зависимости от эндпоинта
- Все записи в БД через psycopg2 транзакции (не REST API)

## Развёртывание

### Backend → Railway / Render

```bash
# Переменные окружения (через UI платформы):
DATABASE_URL
SUPABASE_URL
SUPABASE_KEY
SUPABASE_JWT_SECRET (или DEV_JWT_SECRET для разработки)
GROQ_API_KEY
GEMINI_API_KEY

git push origin main
```

### Frontend → Vercel

```bash
# Переменные окружения:
VITE_API_URL=https://ваш-backend-url

git push origin main
```

## Лицензия

Проект создан для хакатона Decentrathon 5.0 (2026).
