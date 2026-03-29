# Архитектура решения
## AI для справедливых субсидий — Subsidy Scoring System
### Decentrathon 5.0 · AI for Government · Кейс 2

---

## 1. Общее описание

Система ML-скоринга сельхозпроизводителей для замены принципа «первый подал — первый получил» (FCFS) на объективное ранжирование на основе данных. Обрабатывает реестр из 36 653 заявок на субсидии в животноводстве за 2025–2026 гг.

---

## 2. Архитектурная схема

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ПОЛЬЗОВАТЕЛЬ (браузер)                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND  (Vercel)                                │
│                                                                     │
│   React 18 + Vite                                                   │
│   ┌────────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ ┌───────┐  │
│   │ Dashboard  │ │ Producer │ │ Simulator │ │Fairness│ │  Map  │  │
│   │ Топ-N табл.│ │SHAP+AI   │ │ Слайдеры  │ │Gini,   │ │Хоро-  │  │
│   │ KPI, delta │ │ совет    │ │ live-обн. │ │Lorenz  │ │плет   │  │
│   └────────────┘ └──────────┘ └───────────┘ └────────┘ └───────┘  │
│                                                                     │
│   Библиотеки: Recharts · React-Leaflet · Framer Motion             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP/REST (JSON)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND  (Railway)                                │
│                                                                     │
│   FastAPI + uvicorn (Python 3.11)                                   │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                      REST API (7 endpoints)                 │  │
│   │  GET /health          GET /api/metrics   GET /api/stats     │  │
│   │  GET /api/shortlist   GET /api/fairness  GET /api/producers │  │
│   │  GET /docs (Swagger)                                        │  │
│   └────────────────────────────┬────────────────────────────────┘  │
│                                │                                    │
│           ┌────────────────────┼────────────────────┐              │
│           ▼                    ▼                    ▼              │
│   ┌──────────────┐   ┌──────────────────┐   ┌────────────────┐   │
│   │  ML Pipeline │   │ Fairness Module  │   │ Gemini 2.0     │   │
│   │              │   │                  │   │ Flash          │   │
│   │ GradBoost    │   │ Gini-коэффициент │   │ AI-советник    │   │
│   │ 300 деревьев │   │ Kruskal-Wallis   │   │ на русском     │   │
│   │ 24 признака  │   │ Lorenz curve     │   │                │   │
│   │ Isotonic cal.│   │ Heatmap region×  │   │                │   │
│   │ Порог=0.715  │   │ direction        │   │                │   │
│   └──────┬───────┘   └──────────────────┘   └────────────────┘   │
│          │                                                          │
│          ▼                                                          │
│   ┌──────────────┐                                                  │
│   │  model.pkl   │                                                  │
│   │  model       │                                                  │
│   │  encoders    │                                                  │
│   │  features    │                                                  │
│   │  metrics     │                                                  │
│   └──────────────┘                                                  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
              ┌─────────────────┴──────────────────┐
              ▼                                    ▼
┌─────────────────────────┐          ┌─────────────────────────┐
│   DATA  (локально)      │          │   Supabase (PostgreSQL)  │
│                         │          │                          │
│   data/subsidies.xlsx   │          │   36 653 заявки          │
│   36 653 заявки         │          │   RLS + Realtime         │
│   2025–2026 гг.         │          │                          │
└─────────────────────────┘          └─────────────────────────┘
```

---

## 3. ML Pipeline (train.py)

```
subsidies.xlsx
      │
      ▼
[1] ЗАГРУЗКА — 36 653 строки, skiprows=4
      │
      ▼
[2] PREPROCESSING
    • datetime parsing (дд.мм.гггг чч:мм:сс)
    • producer_id = первые 11 цифр номера заявки
    • pd.to_numeric для «Причитающая сумма», «Норматив»
    • log-трансформы, amount/norm ratio
      │
      ▼
[3] TARGET ENCODING
    target = 1 → Исполнена  (21 012 строк)
    target = 0 → Отклонена, Отозвано  (4 973 строки)
    EXCLUDED   → Одобрена, Получена, Сформировано поручение (10 668 строк)
      │
      ▼
[4] TEMPORAL SPLIT
    Train → 2025 год (24 653 завершённых заявки, pos=82.4%)
    Val   → 2026 год ( 1 332 завершённых заявки, pos=51.5%)
      │
      ▼
[5] FEATURE ENGINEERING (24 признака, только на train)

    Временные (4):
      month, hour, day_of_year, day_of_week

    Финансовые (5):
      Норматив, Причитающая сумма,
      amount_to_norm, log_amount, log_norm

    Категориальные LabelEncoded (3):
      region_enc, direction_enc, subsidy_enc

    Агрегаты по группам (12):
      Регион   → reg_sr,  reg_vol,  reg_avg_amt
      Направл. → dir_sr,  dir_vol,  dir_avg_amt
      Субсидия → sub_sr,  sub_vol,  sub_avg_amt
      Район    → dist_sr, dist_vol, dist_avg_amt

    ⚠ Все агрегаты считаются строго по train.
      Val unseen-категории → заполняются медианами train.
      │
      ▼
[6] 5-FOLD CROSS-VALIDATION на train (2025)
    Fold 1: AUC=0.8507  F1=0.9373
    Fold 2: AUC=0.8527  F1=0.9354
    Fold 3: AUC=0.8505  F1=0.9391
    Fold 4: AUC=0.8502  F1=0.9381
    Fold 5: AUC=0.8454  F1=0.9353
    ── Mean CV AUC: 0.8499 ± 0.0024
    ── Mean CV F1 : 0.9370 ± 0.0015
      │
      ▼
[7] ОБУЧЕНИЕ ФИНАЛЬНОЙ МОДЕЛИ
    GradientBoostingClassifier:
      n_estimators=300, learning_rate=0.05
      max_depth=4, min_samples_leaf=20, subsample=0.8
    + CalibratedClassifierCV (isotonic, cv=3)
      │
      ▼
[8] HOLD-OUT ОЦЕНКА (2026)
    ROC-AUC          = 0.6904
    Average Precision = 0.6645
    Оптимальный порог = 0.715  →  F1 = 0.7310
    (разрыв с CV — distribution shift: 82% → 51% positive)
      │
      ▼
[9] СОХРАНЕНИЕ → model.pkl
    {model, base_model, features, encoders, optimal_threshold, metrics}
```

---

## 4. API Endpoints (main.py)

| Endpoint | Что возвращает |
|----------|---------------|
| `GET /health` | status, model, data, rows, timestamp |
| `GET /api/metrics` | roc_auc, avg_precision, best_f1, threshold, cv_auc_mean, features |
| `GET /api/stats` | total_rows, producers, status_distribution, year_distribution, regions, directions, avg_amount |
| `GET /api/shortlist?top_n=N` | total_producers, список с ml_score, delta, hidden_talent, fcfs_rank |
| `GET /api/fairness` | gini_coefficient, lorenz_curve, kruskal_wallis (по регионам и направлениям), heatmap регион×направление |
| `GET /api/producers/{id}` | профиль, заявки, ml_score, status_breakdown |
| `GET /docs` | Swagger UI (интерактивная документация) |

---

## 5. Ключевые бизнес-концепции

**delta** — разница между ML-позицией производителя и его FCFS-позицией.
Положительная delta = ML считает его более достойным, чем показывает очередь.

**hidden_talent** — производители с высоким ML-score, но малым числом заявок.
FCFS их системно недооценивает: они подают редко, но эффективно.

**Temporal validation** — модель обучена на 2025, валидируется на 2026.
Имитирует реальное использование: модель не видит будущее.

**Human-in-the-loop** — система формирует рекомендации, финальное решение
за комиссией МСХ. Инструмент поддержки, не автоматический вердикт.

---

## 6. Технологический стек

| Слой | Технология | Версия |
|------|-----------|--------|
| Backend | FastAPI | 0.111.0 |
| ASGI | uvicorn | 0.29.0 |
| ML | scikit-learn | 1.4.2 |
| ML (доп.) | XGBoost | 2.0.3 |
| Объяснимость | SHAP | 0.45.0 |
| Статистика | SciPy | 1.13.0 |
| Данные | pandas 2.2.2, numpy 1.26.4 |
| Excel | openpyxl | 3.1.2 |
| Сериализация | joblib | 1.4.0 |
| AI-советник | Gemini 2.0 Flash | — |
| Frontend | React 18 + Vite | — |
| Стили | Tailwind CSS + Inter | — |
| Графики | Recharts | — |
| Карта | React-Leaflet | — |
| Анимации | Framer Motion | — |
| БД | Supabase (PostgreSQL) | — |
| Деплой backend | Railway | — |
| Деплой frontend | Vercel | — |

---

## 7. Структура репозитория

```
subsidies-scoring/
├── backend/
│   ├── train.py          # ML pipeline: preprocessing → train → eval → model.pkl
│   ├── main.py           # FastAPI: 7 endpoints + startup data loading
│   ├── requirements.txt  # Python зависимости
│   ├── model.pkl         # Обученная модель (генерируется train.py)
│   └── data/
│       └── subsidies.xlsx
├── frontend/
│   ├── src/
│   │   ├── pages/        # Dashboard, Producer, Simulator, Fairness, Map
│   │   └── components/
│   └── package.json
├── railway.toml
└── README.md
```
