# Архитектура SubsidyLens

## 1. Общее описание

Система ML-скоринга сельхозпроизводителей для объективного распределения государственных субсидий на животноводство в Республике Казахстан.

**Входные данные:** Реестр из 36 653 заявок на субсидии за 2025–2026 гг.

**Выходные данные:**
- Скоринг каждого производителя (0–1)
- SHAP-объяснения (топ-5 факторов)
- Контрфактуальные рекомендации
- Индикаторы риска (6 типов сигналов)
- AI-советник на русском языке

---

## 2. Архитектура системы

```
┌─────────────────────────────────────────────────────┐
│                   FRONTEND (React 18 + Vite)         │
│                                                     │
│  Dashboard → Producer → Fairness → Map → Simulator  │
│  Recharts · Tailwind · Framer Motion                │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP/REST
                        ▼
┌─────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                  │
│                                                     │
│  35+ эндпоинтов · Rate limiting · JWT Auth          │
│  Thread-safe (RLock)                                │
│                                                     │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ ML Pipeline│  │ Fairness   │  │ AI Advisor   │  │
│  │ XGBoost    │  │ Gini,      │  │ Groq/Gemini  │  │
│  │ 32 features│  │ Lorenz,    │  │ SHAP         │  │
│  │ Calibration│  │ K-Wallis   │  │ Counterfact. │  │
│  │ Risk Ind.  │  │            │  │              │  │
│  └─────┬──────┘  └────────────┘  └──────────────┘  │
│        │                                             │
│  ┌─────▼──────┐                                     │
│  │ Model      │                                     │
│  │ Registry   │ (PostgreSQL)                        │
│  │ + Storage  │ (local / S3)                        │
│  └────────────┘                                     │
└───────────┬─────────────────────────────────────────┘
            │ psycopg2 (транзакции)
            ▼
┌──────────────────────────┐     ┌────────────────────┐
│   Supabase (PostgreSQL)  │     │   Внешние API      │
│   • producers            │     │   • Groq (Llama)   │
│   • scores               │     │   • Gemini 2.0     │
│   • shap_values          │     │                    │
│   • model_registry       │     │                    │
│   • fairness_cache       │     │                    │
│   • gemini_advice        │     │                    │
└──────────────────────────┘     └────────────────────┘
```

---

## 3. ML-пайплайн

### Схема обработки данных

```
subsidies.xlsx (36 653 строки)
      │
      ▼
[1] ЗАГРУЗКА
    ├─ Парсинг дат, извлечение producer_id
    ├─ Финансовые преобразования (log, amount_to_norm)
    └─ Целевая переменная: Исполнена=1, Отклонена/Отозвана=0

      │
      ▼
[2] РАЗДЕЛЕНИЕ (temporal, без shuffle)
    ├─ Train: 2025 год — 24 653 строки (pos=82.4%)
    └─ Holdout: 2026 год — 1 332 строки (pos=51.5%)

      │
      ▼
[3] ИНЖИНИРИНГ ПРИЗНАКОВ (32 признака)
    │
    ├─ Временные (4): месяц, час, день года, день недели
    ├─ Финансовые (5): норматив, сумма, отношение, логи
    ├─ Категориальные (3): регион, направление, тип (LabelEncoder)
    ├─ Агрегаты (12): success_rate, объём, средняя × 4 группы
    └─ v7 признаки (8): trend, frequency, consistency, bias, relative
       │
       └─ Все агрегаты вычисляются ТОЛЬКО на train (без leakage)

      │
      ▼
[4] КРОСС-ВАЛИДАЦИЯ (GroupKFold по producer_id)
    ├─ Fold 1–5: AUC 0.975–0.980
    └─ Mean CV AUC: 0.9769 ± 0.0017

      │
      ▼
[5] ФИНАЛЬНАЯ МОДЕЛЬ
    ├─ XGBoost: 296 деревьев (early stopping)
    ├─ Calibration: sigmoid, 3-fold
    ├─ Time-decay weighting (поздние заявки 2025 весят больше)
    └─ Quality Gate: ROC-AUC ≥ 0.72 (иначе модель НЕ сохраняется)

      │
      ▼
[6] СОХРАНЕНИЕ (атомарное)
    ├─ Backup текущей модели → model.pkl.bak
    ├─ Запись во временный файл → model.pkl.tmp
    ├─ Атомарная замена → os.replace()
    ├─ Верификация загрузкой
    └─ Rollback при ошибке
```

---

## 4. Признаки модели

### Базовые (24 признака)

| Группа | Признаки | Источник |
|--------|----------|----------|
| Временные (4) | month, hour, day_of_year, day_of_week | Дата подачи |
| Финансовые (5) | Норматив, Прич. сумма, amount_to_norm, log_amount, log_norm | Сумма заявки |
| Категориальные (3) | region_enc, direction_enc, subsidy_enc | LabelEncoder (fit на train) |
| Агрегаты (12) | reg/dir/sub/dist: sr, vol, avg_amt | GroupBy по train 2025 |

### v7 признаки (8 признаков)

| Признак | Описание | Зачем |
|---------|----------|-------|
| `completion_trend` | Отклонение от регионального успеха | Главный предиктор (важность 0.22) |
| `app_frequency` | log(app_count + 1) | Активность производителя |
| `amount_consistency` | 1 / (CV + 1) | Стабильность сумм заявок |
| `region_bias` | reg_sr − global_mean | Смещение региона |
| `rel_amount_in_region` | Сумма / reg_avg_amt | Относительная сумма в регионе |
| `rel_amount_in_direction` | Сумма / dir_avg_amt | Относительная сумма в направлении |
| `month_amount_inter` | month × log_amount | Взаимодействие сезонности и суммы |
| `norm_per_app` | Норматив / app_count | Норматив на заявку |

---

## 5. Объяснимость

### SHAP (TreeExplainer)

Для каждого производителя вычисляются значения Шепли — вклад каждого признака в итоговый скор.

```
Производитель #12345678 | ML Score: 0.78
  1. completion_trend    +0.12 ████████
  2. sub_sr              +0.08 █████
  3. reg_sr              +0.05 ███
  4. month               -0.03 ██
  5. log_amount          -0.02 █
```

Оптимизации:
- Precomputed TreeExplainer при запуске сервера
- Фильтрация слабых признаков (bottom 25% по median |SHAP|)
- Стабильный вывод ровно 5 критериев

### Контрфактуальный анализ

Greedy-поиск минимальных изменений управляемых признаков для прохода порога:

```
Текущий скор: 65.4% → Цель: 87.1%
  1. Месяц подачи: Август → Июль (+12.3%)
  2. Отношение суммы к нормативу: 1.8 → 1.2 (+9.7%)
```

Управляемые признаки: месяц, час, день недели, amount_to_norm, log_amount.

### Риск-индикаторы

6 типов сигналов, каждый с severity 0–100:

| Тип | Что обнаруживает |
|-----|------------------|
| Behavioral | Нерегулярная подача заявок (CV интервалов > 1.5) |
| Financial | Аномальная вариация сумм vs peers (CV > 2×) |
| Status | Высокий процент отклонений (> 50%) |
| Temporal | Снижение активности в последнее время |
| Peer group | Z-score > 2 от группы (регион + направление) |
| New entrant | Мало заявок, но суммы > 3× медианы региона |

---

## 6. Инфраструктура

### База данных (Supabase / PostgreSQL)

| Таблица | Назначение | Метод записи |
|---------|------------|--------------|
| `producers` | Профили производителей | psycopg2, batch upsert |
| `scores` | ML-скоры и ранги | psycopg2, batch (staging → upsert) |
| `shap_values` | SHAP-значения | psycopg2, staging→verify→swap |
| `model_registry` | Реестр версий моделей | psycopg2, ON CONFLICT |
| `fairness_cache` | Кеш метрик справедливости | psycopg2 |
| `gemini_advice` | Кеш AI-советов | psycopg2 |

Все записи — через psycopg2 транзакции (не REST API).
SHAP: TRUNCATE staging → INSERT → verify → DELETE production → INSERT → COMMIT.

### Модель и реестр

Каждая обученная модель регистрируется в `model_registry`:

```sql
model_registry (
    version TEXT PRIMARY KEY,    -- v73.1.24
    roc_auc FLOAT,
    status TEXT,                  -- registered / active / rolled_back
    created_at TIMESTAMPTZ,
    metadata JSONB
)
```

Атомарная замена активной модели через `activate_model()`:
1. Загрузка кандидата из хранилища
2. Валидация (наличие roc_auc)
3. Swap в памяти (под RLock)
4. Rebuild кешей
5. Commit в БД

---

## 7. Безопасность

| Мера | Реализация |
|------|------------|
| Аутентификация | Supabase JWT (HS256) |
| Обязательность секрета | Crash при отсутствии SUPABASE_JWT_SECRET |
| Rate limiting | 5–120 запросов/мин на эндпоинт |
| CORS | Whitelist из env (не `*`) |
| Секреты | Только в `.env`, не в git |
| Записи в БД | Только psycopg2 транзакции |
| Модель | Atomic save с backup и rollback |

---

## 8. Производительность

| Операция | До оптимизации | После | Ускорение |
|----------|----------------|-------|-----------|
| Upsert scores (15K) | ~20 мин | ~3 сек | 400× |
| Upsert producers (15K) | ~5 мин | ~2 сек | 150× |
| Upsert SHAP (55K) | ~15 мин | ~5 сек | 180× |

Метод: `psycopg2.extras.execute_values` с батчами по 1000–2000 записей через временную staging-таблицу.

---

## 9. Развёртывание

```
Backend: Railway / Render
  ├── Python 3.12
  ├── FastAPI + uvicorn
  ├── Env vars: DATABASE_URL, SUPABASE_*, GROQ_*, GEMINI_*
  └── Health check: /health

Frontend: Vercel
  ├── React 18 + Vite
  ├── Tailwind CSS
  └── Env vars: VITE_API_URL
```

---

**Версия документа:** 2.0 · Апрель 2026
