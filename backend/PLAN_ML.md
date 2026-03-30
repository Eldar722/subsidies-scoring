# План разработки + промпты для Claude Code
## 🔴 ML-щик — ML Pipeline + данные + Supabase
## AI для справедливых субсидий — Decentrathon 5.0

> Твоя зона: `backend/ml/` + `backend/services/` + Supabase таблицы
> Запускай `claude` из папки `D:\Decenthrathon\subsidies-scoring\backend`
> Промпты закидывай последовательно — каждый следующий только после проверки предыдущего.

---

## ДЕНЬ 1 — 27 марта | Загрузка данных

### 🎯 Цель дня: датасет загружается, producer_id извлечён, структура данных понятна

---

### ПРОМПТ 1.1 — Загрузка данных
```
Создай backend/ml/data_loader.py для загрузки реального датасета субсидий.

Файл: backend/data/subsidies.xlsx
Особенности файла:
- Заголовки на строке 5 (skiprows=4 или header=4)
- Колонки: "Дата поступления", "Область", "Акимат", "Номер заявки",
  "Направление водства", "Наименование субсидирования", "Статус заявки",
  "Норматив", "Причитающая сумма", "Район хозяйства"

Функция load_xlsx(path) должна:
1. Загрузить файл с правильным header
2. Распарсить "Дата поступления" как datetime (формат: дд.мм.гггг чч:мм:сс)
3. Создать producer_id = str(Номер заявки)[:11]
4. Преобразовать "Причитающая сумма" и "Норматив" в числа (pd.to_numeric, errors='coerce')
5. Добавить колонки: year, month, hour, day_of_week, day_of_year

Добавь assert-проверки:
- assert len(df) >= 36000
- assert df["producer_id"].nunique() >= 15000

Запусти и покажи df.shape и df["producer_id"].nunique()
```

---

## ДЕНЬ 2 — 28 марта | Feature Engineering + ML Pipeline

### 🎯 Цель дня: модель обучена, метрики выведены, model.pkl сохранён

---

### ПРОМПТ 2.1 — Feature Engineering
```
Создай backend/ml/feature_engineering.py.

Функция build_features(df) принимает DataFrame из data_loader и возвращает feature_df с 24 признаками:

ВРЕМЕННЫЕ (4):
- month, hour, day_of_year, day_of_week

ФИНАНСОВЫЕ (5):
- норматив (Норматив), сумма (Причитающая сумма)
- amount_to_norm = сумма / (норматив + 1)
- log_amount = np.log1p(сумма)
- log_norm = np.log1p(норматив)

КАТЕГОРИАЛЬНЫЕ LabelEncoded (3):
- region_enc (Область)
- direction_enc (Направление водства)
- subsidy_enc (Наименование субсидирования)

АГРЕГАТЫ ПО ГРУППАМ (12) — считать ТОЛЬКО на train, val заполнять медианой:
- По региону: reg_sr (success_rate), reg_vol (volume), reg_avg_amt
- По направлению: dir_sr, dir_vol, dir_avg_amt
- По субсидии: sub_sr, sub_vol, sub_avg_amt
- По району: dist_sr, dist_vol, dist_avg_amt

ВАЖНО: функция должна принимать параметр fit=True/False:
- fit=True: обучает LabelEncoders и считает агрегаты, сохраняет их
- fit=False: применяет сохранённые энкодеры/агрегаты (для val)
- Unseen категории на val → заполнять медианой train

Покажи feature_df.columns и feature_df.describe()
```

---

### ПРОМПТ 2.2 — ML Pipeline
```
Создай backend/ml/pipeline.py.

Целевая переменная:
- target = 1 → статус "Исполнена"
- target = 0 → статус "Отклонена" или "Отозвано"
- ИСКЛЮЧИТЬ: "Одобрена", "Получена", "Сформировано поручение"

Temporal split:
- train = строки где year == 2025
- val = строки где year == 2026

Функции:
1. train_model(X_train, y_train):
   - GradientBoostingClassifier(n_estimators=300, learning_rate=0.05, max_depth=4, min_samples_leaf=20, subsample=0.8)
   - Обернуть в CalibratedClassifierCV(method='isotonic', cv=3)
   - 5-fold CV на train → вывести AUC по каждому fold и среднее
   - Вернуть обученную модель

2. evaluate(model, X_val, y_val):
   - ROC-AUC, Average Precision
   - Найти оптимальный порог по F1 на val
   - Вывести итоговые метрики

3. run_full_pipeline(data_path):
   - Загрузить данные через data_loader
   - Feature engineering
   - Train/Val split
   - Обучить модель
   - Оценить
   - Сохранить model.pkl через joblib: {model, features, encoders, optimal_threshold, metrics}
   - Вернуть metrics dict

Запусти pipeline и выведи финальные метрики на val 2026.
Целевой ROC-AUC > 0.65 на val.
```

---

## ДЕНЬ 3 — 29 марта | SHAP + Baseline + Supabase | ⚑ СДАЧА #1

### 🎯 Цель дня: SHAP считается, данные залиты в Supabase, бэкендер подключает роутеры

---

### ПРОМПТ 3.1 — SHAP Service
```
Создай backend/ml/shap_service.py.

Функция compute_shap(model, X, producer_ids):
- Использует shap.TreeExplainer на base_model из CalibratedClassifierCV
- Для каждого producer_id вычислить shap_values
- Вернуть топ-5 признаков по |shap_value| для каждого производителя
- Формат: [{ "producer_id": "...", "feature": "...", "shap_value": 0.23, "feature_value": 150000 }]

Функция format_shap_for_ui(shap_data):
- Переименовать технические названия в русские:
  - region_enc → "Регион"
  - direction_enc → "Направление"
  - completion_rate → "Успешность заявок"
  - log_amount → "Сумма субсидии"
  - month → "Месяц подачи"
  - reg_sr → "Успешность в регионе"
  - dir_sr → "Успешность по направлению"
  - amount_to_norm → "Отношение суммы к нормативу"
  (добавь все 24 признака)

Запусти для первых 100 производителей и покажи пример вывода.
```

---

### ПРОМПТ 3.2 — Baseline + Shortlist логика
```
Создай backend/ml/baseline_service.py.

Функция compute_baseline(df, model_scores):
  Принимает: исходный DataFrame + dict {producer_id: ml_score}

  1. FCFS ранжирование:
     - Агрегировать по producer_id: первая дата подачи (min "Дата поступления")
     - fcfs_rank = ранг по submission_advance (чем раньше подал — тем выше)

  2. ML ранжирование:
     - ml_rank = ранг по ml_score (по убыванию)

  3. Delta:
     - delta = fcfs_rank - ml_rank
     - Положительная delta = ML считает производителя лучше чем FCFS

  4. Hidden talent флаг:
     - hidden_talent = True если:
       a) ml_score > медиана ml_scores
       b) количество заявок у производителя < медиана по всем производителям

  5. Вернуть DataFrame с колонками:
     producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent

Скажи бэкендеру что baseline_service.py готов — он подключает его в роутеры.
```

---

### ПРОМПТ 3.3 — Supabase таблицы + загрузка данных
```
Создай backend/services/supabase_service.py с функциями:
- upsert_producers(producers_df) → загрузить в таблицу producers
- upsert_scores(scores_df) → загрузить в таблицу scores
- upsert_shap(shap_list) → загрузить в таблицу shap_values
- upsert_metrics(metrics_dict) → загрузить в таблицу model_metrics

SQL для создания таблиц (выведи чтобы я запустил в Supabase SQL Editor):

CREATE TABLE producers (
  producer_id TEXT PRIMARY KEY,
  region TEXT,
  direction TEXT,
  total_applications INT,
  completion_rate FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE scores (
  producer_id TEXT PRIMARY KEY REFERENCES producers(producer_id),
  ml_score FLOAT,
  ml_rank INT,
  fcfs_rank INT,
  delta INT,
  hidden_talent BOOLEAN,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE shap_values (
  id SERIAL PRIMARY KEY,
  producer_id TEXT,
  feature TEXT,
  shap_value FLOAT,
  feature_value FLOAT,
  feature_label TEXT
);

CREATE TABLE model_metrics (
  id SERIAL PRIMARY KEY,
  run_id TEXT,
  roc_auc FLOAT,
  avg_precision FLOAT,
  best_f1 FLOAT,
  optimal_threshold FLOAT,
  cv_auc_mean FLOAT,
  train_size INT,
  val_size INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE gemini_advice (
  producer_id TEXT PRIMARY KEY,
  advice_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE fairness_cache (
  id SERIAL PRIMARY KEY,
  report_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

После создания таблиц — загрузи всех producers и scores батчами по 500.
Покажи count из каждой таблицы.
```

---

## ДЕНЬ 4 — 30 марта | Fairness + Gemini Advisor

### 🎯 Цель дня: fairness модуль готов, Gemini кэширован для топ-100

---

### ПРОМПТ 4.1 — Fairness Module
```
Создай backend/ml/fairness.py.

Функции:

1. compute_gini(values: list) → float:
   - Коэффициент Джини для списка значений
   - Формула: G = (2 * sum(i * x_i) / (n * sum(x_i))) - (n+1)/n
   - Вернуть значение 0-1

2. compute_lorenz(values: list) → list[{x, y}]:
   - Точки для кривой Лоренца
   - x = кумулятивная доля производителей (0-1)
   - y = кумулятивная доля баллов (0-1)
   - Вернуть список из 100 точек для Recharts

3. compute_kruskal_wallis(df, group_col, value_col) → {H, p_value, interpretation}:
   - Тест Краскела-Уоллиса через scipy.stats.kruskal
   - interpretation: "Значимых различий нет" если p > 0.05, иначе "Есть статистический bias"

4. compute_z_scores(df, group_col, value_col) → dict:
   - Z-score для каждой группы (регион или направление)
   - Флаг: |z| > 1 → "outlier": True

5. compute_fairness_report(scores_df, producers_df) → dict:
   Возвращает:
   {
     "gini_scores": float,
     "gini_amounts": float,
     "lorenz_scores": [{x, y}, ...],
     "kruskal_regions": {H, p_value, interpretation},
     "kruskal_directions": {H, p_value, interpretation},
     "region_z_scores": {region: {mean_score, z_score, outlier}},
     "direction_z_scores": {direction: {mean_score, z_score, outlier}},
     "heatmap": [{region, direction, avg_score}]
   }

Кэшировать результат в Supabase таблице fairness_cache.
Скажи бэкендеру что fairness.py готов — он подключает в роутер.
Покажи итоговый JSON с реальными данными.
```

---

### ПРОМПТ 4.2 — Gemini Advisor
```
Создай backend/services/gemini_advisor.py.

Используй google-generativeai, модель: gemini-2.0-flash.
API ключ из GEMINI_API_KEY в .env.

Функция get_advice(producer_data: dict) → dict:
  producer_data содержит: producer_id, ml_score, shap_top5, fcfs_rank, delta, region, direction

  Системный промпт:
  """
  Ты — AI-советник для комиссии МСХ Казахстана по субсидиям в животноводстве.
  Отвечай только на русском языке. Будь конкретным и практичным.
  Возвращай ТОЛЬКО валидный JSON без markdown блоков.
  """

  Пользовательский промпт:
  """
  Производитель {producer_id} из региона {region}, направление: {direction}.
  ML балл: {ml_score:.1%}. FCFS ранг: #{fcfs_rank}. ML ранг: #{ml_rank}. Delta: {delta}.

  Топ факторы влияющие на балл (SHAP):
  {shap_factors_formatted}

  Верни JSON:
  {{
    "score_explanation": "2-3 предложения почему такой балл",
    "baseline_injustice": "1 предложение — справедлив ли FCFS для этого производителя",
    "recommendations": [
      {{"action": "конкретное действие", "impact": "+X% к вероятности одобрения"}},
      {{"action": "второе действие", "impact": "+Y%"}}
    ]
  }}
  """

  - Retry 2 раза при ошибке (sleep 2s)
  - Парсить JSON из ответа
  - Fallback если ошибка парсинга: вернуть дефолтный dict с сообщением

Функция batch_advise(producer_ids: list, limit=100):
  - Для каждого producer_id получить данные из Supabase
  - Вызвать get_advice()
  - Сохранить в gemini_advice: producer_id, advice_json, created_at
  - Sleep 0.5s между запросами (rate limit 1500 req/day)
  - Показывать прогресс каждые 10 записей

Запусти batch_advise для топ-20 производителей и покажи пример ответа.
Скажи бэкендеру что gemini_advisor.py готов — он подключает роутер /api/producers/{id}/advice.
```

---

## ДЕНЬ 5 — 31 марта | Simulator Service

### 🎯 Цель дня: симулятор весов готов, бэкендер подключает эндпоинт

---

### ПРОМПТ 5.1 — Simulator Service
```
Создай backend/ml/simulator_service.py.

Функция simulate(weights: dict, top_n: int) → dict:

  1. Проверить что сумма weights == 1.0 (нормировать если нет)
  2. Для каждого производителя пересчитать взвешенный score:
     weighted_score = (completion_rate * w1) + (approval_rate * w2) + ...
  3. Отсортировать по weighted_score → новый шортлист топ-N
  4. Сравнить с базовым ml шортлистом:
     - entered: кто вошёл в новый но не был в базовом
     - left: кто был в базовом но вышел из нового
  5. Вернуть:
  {
    "shortlist": [{ producer_id, weighted_score, hidden_talent, ... }],
    "entered": [producer_ids],
    "left": [producer_ids],
    "hidden_talent_count": N,
    "weights_used": { ... }
  }

Протестируй с разными весами и убедись что entered/left логика работает.
Скажи бэкендеру что simulator_service.py готов — он подключает POST /api/simulate.
```

---

## ДЕНЬ 6 — 1 апреля | Демо данные

### 🎯 Цель дня: 5 интересных производителей для демо жюри

---

### ПРОМПТ 6.1 — Демо данные
```
Подготовь 5 демо-производителей для презентации жюри.

Нужно найти в реальных данных:
3 "скрытых таланта" — производители где:
- hidden_talent = True
- delta > 10 (ML считает их намного лучше чем FCFS)
- Интересная история в SHAP

2 "переоценённых FCFS" — производители где:
- delta < -10
- completion_rate ниже медианы

Для каждого из 5:
1. Убедись что есть Gemini совет в кэше gemini_advice
2. Убедись что есть SHAP данные в shap_values
3. Запиши producer_id

Выведи таблицу:
producer_id | region | direction | ml_score | fcfs_rank | delta | hidden_talent | ключевой SHAP фактор

Передай эти 5 producer_id фронтендеру для демо-тестирования.
```

---

## ДЕНЬ 7 — 2 апреля | Финальная проверка ML | ⚑ СДАЧА #2

---

### ПРОМПТ 7.1 — Model Card (Model Card секция README)
```
Напиши backend/README.md — model card секцию.

Включи:
1. Как запустить за 3 команды
2. Model Card:
   - Алгоритм: GradientBoostingClassifier + CalibratedClassifierCV
   - Целевая: completion_rate ("Исполнена")
   - Train: 2025 данные (N строк)
   - Validation: temporal holdout 2026 (N строк)
   - Метрики: ROC-AUC=X.XX, F1=X.XX, Precision=X.XX, Recall=X.XX
   - CV AUC: X.XX ± X.XX
3. 24 признака с описанием на русском
4. Ограничения модели:
   - Обучена только на животноводстве РК
   - Distribution shift: train 82% positive → val 51% positive
   - Не учитывает качество животных и внешние факторы
   - Инструмент поддержки, не автоматическое решение
5. Fairness метрики (реальные из Supabase):
   - Gini score
   - Kruskal-Wallis по регионам: p=X.XX
   - Kruskal-Wallis по направлениям: p=X.XX

Возьми реальные метрики из Supabase model_metrics.
```

---

## ДНИ 9-10 — 4-5 апреля | Финал | ⚑ 23:59

---

### ПРОМПТ 9.1 — Clean code финал
```
Проведи финальный аудит ML кода перед сдачей.

1. Все функции имеют docstrings
2. Нет хардкодированных путей — только из .env или аргументов
3. Нет закомментированного кода
4. requirements.txt с точными версиями: pip freeze > requirements.txt
5. model.pkl в .gitignore
6. data/*.xlsx в .gitignore

Сделай финальный git commit: "feat: final ML v1.0"
```

---

## СОВЕТЫ ПО РАБОТЕ С CLAUDE CODE

### Запускай claude из папки backend:
```powershell
cd D:\Decenthrathon\subsidies-scoring\backend
claude
```

### Синк с бэкендером:
Каждый раз когда заканчиваешь модуль — сообщи бэкендеру:
```
Готово: backend/ml/fairness.py
Экспортирует: compute_fairness_report(scores_df, producers_df) → dict
Данные берёт: из Supabase (scores + producers таблицы)
```

### Порядок работы каждый день:
1. `cd backend && claude`
2. Закинь промпт
3. После выполнения — проверь что модуль импортируется без ошибок
4. Сообщи бэкендеру что готово
5. `git add . && git commit -m "feat: day X - описание"`
