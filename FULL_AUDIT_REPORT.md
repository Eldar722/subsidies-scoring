# ПОЛНЫЙ АУДИТ ПРОЕКТА: AI для справедливых субсидий
**Дата аудита**: 2025  
**Статус**: СРЕДНИЙ (работает, но есть критические проблемы)

---

## 1. АРХИТЕКТУРНЫЙ ОБЗОР ✅

**Статус реализации**: 80% от спецификации

| Компонент | Статус | Примечание |
|-----------|--------|-----------|
| **Backend (FastAPI)** | ✅ | Все 11 роутеров загружаются |
| **ML Model (GradientBoosting)** | ✅ | AUC=0.7605, загружается корректно |
| **Данные (36K apps)** | ✅ | Parquet cache работает (1s load) |
| **Supabase интеграция** | ⚠️ | Есть проблемы с SQL запросами |
| **Fairness модуль** | ✅ | Gini, Lorenz, Kruskal-Wallis, Z-scores |
| **Hidden talent detection** | ⚠️ | Работает, но пороги критичны |
| **Fair reranking** | ❌ | Функция `compute_fair_shortlist` не реализована |
| **Counterfactuals** | ❌ | Функция `find_counterfactual` не реализована |
| **Gemini AI advisor** | ⚠️ | Зависит от API ключей (не тестировано) |
| **Drift monitor** | ✅ | Загружается (но не тестировано) |
| **Simulator** | ✅ | Загружается (но не тестировано) |

---

## 2. КРИТИЧЕСКИЕ ПРОБЛЕМЫ 🔴

### Проблема #1: РАСПРЕДЕЛЕНИЕ ДАННЫХ СМЕСТИЛОСЬ (37.5%)
**Severity**: ВЫСОКАЯ  
**Определено в**: Аудит PHASE 5

```
2025 (Train): 82.4% positive (21,012 Исполнена из 24,653)
2026 (Val):   51.5% positive (686 Исполнена из 1,332)
Shift: 37.5%
```

**Последствия**:
- Модель переобучена на 2025 года данные
- Cross-validation AUC: 0.9054 → Validation AUC: 0.7605 (16% drop)
- Threshold оптимизирован на 82% positive, но deployment 51% positive
- Может привести к смещению в предсказаниях

**Рекомендация (УРОВЕНЬ A)**:
```python
# Текущий подход неправильный - нужна распределение сбалансированная валидация
# Вариант 1: Stratified K-fold  with distribution weighting
# Вариант 2: Threshold adjustment для 51.5% positive baseline
# Вариант 3: Class weighting в модели (текущая не имеет)
```

---

### Проблема #2: DATA QUALITY - 29% UNRESOLVED APPLICATIONS
**Severity**: СРЕДНЯЯ  
**Определено в**: Аудит PHASE 6

```
Всего строк: 36,653
Resolved (target=1 или 0): 25,985 (70.9%)
Unresolved: 10,668 (29.1%)

Статусы:
  Исполнена             21,012 (1)
  Одобрена              7,615  (?) - NOT CODED AS 1
  Отклонена             2,909  (0)
  Сформировано поручение 2,854  (?) - NOT CODED
  Отозвано              2,064  (0)
  Получена              197    (?) - NOT CODED
```

**Проблема**: "Одобрена" (7,615 строк) может быть положительная, но не кодируется как 1
- Это 7.6K потерянных данных для обучения
- Может быть "предварительное одобрение"
- Или "запрос находится на рассмотрении"

**Рекомендация (УРОВЕНЬ B)**:
```
1. Уточнить у домена: что означает "Одобрена"?
2. Если positive → добавить в train
3. Если unknown → исключить без потери
4. Создать mapping: {"Одобрена": ?, "Получена": ?, ...}
```

---

### Проблема #3: HIDDEN TALENT THRESHOLD СЛИШКОМ ВЫСОКИЙ
**Severity**: СРЕДНЯЯ  
**Определено в**: Аудит PHASE 3

```python
# Текущая логика:
delta > 10 AND ml_score > 0.7308

# Пример:
P1: ml_score=0.95, delta=15  → ✅ Скрытый талант (ОК)
P2: ml_score=0.80, delta=12  → ✅ Скрытый талант (ОК)
P3: ml_score=0.72, delta=14  → ❌ НЕ скрытый талант (ПРОБЛЕМА!)
     ^ только на 0.008 ниже, но исключён
P4: ml_score=0.65, delta=8   → ❌ Не скрытый талант (ОК, низкий delta)
```

**Проблема**:
- P3 - явно недооценён FCFS (delta=14), но исключен из-за ml_score < 0.7308
- Потеря точности в edge cases
- Нет калибровки на новых данных (2026)

**Рекомендация (УРОВЕНЬ B)**:
```python
# Вариант 1: Снизить ml_score threshold
detect_hidden_talents_by_delta(df, delta_threshold=10, score_multiplier=0.95)
# Даст threshold = 0.7308 * 0.95 = 0.6942

# Вариант 2: Использовать median-based для валидации
# hidden_talent = (delta > percentile_75) OR (ml_score > percentile_90)

# Вариант 3: A/B тестировать оба пороги и смотреть результат
```

---

### Проблема #4: FAIR RERANKING & COUNTERFACTUALS НЕ РЕАЛИЗОВАНЫ
**Severity**: КРИТИЧЕСКАЯ  
**Определено в**: Аудит PHASE 2, Проверка импортов

**Статус**:
```
❌ routers/fair_rerank.py  - вызывает import compute_fair_shortlist из ml.fair_reranker
❌ routers/counterfactual.py - вызывает import find_counterfactual из ml.counterfactual

Но эти модули НЕ СУЩЕСТВУЮТ!
```

**Ошибки при вызове API**:
```python
# GET /api/shortlist/fair → ImportError: No module named 'ml.fair_reranker'
# GET /api/counterfactual → ImportError: No module named 'ml.counterfactual'
```

**Рекомендация (УРОВЕНЬ A - БЛОКИРУЕТ ФИЧИ)**:
```
Вариант 1: Реализовать модули (2-3 часа работы)
  - ml/fair_reranker.py с compute_fair_shortlist()
  - ml/counterfactual.py с find_counterfactual()

Вариант 2: Удалить из фронтенда до реализации (1 час)
  - Remove UI для fair reranking
  - Remove UI для counterfactuals
  - Задокументировать как TODO

Вариант 3: Fallback реализация (быстро)
  - fair_reranker: return обычный shortlist
  - counterfactual: return JSON "Not available yet"
```

---

### Проблема #5: SUPABASE INTEGRATION ERROR ПОТЕНЦИАЛЕН
**Severity**: СРЕДНЯЯ (не критична на localhost)  
**Определено в**: Аудит PHASE 4

```python
# Текущий код в routers/shortlist.py:
result = (
    client.table("scores")
    .select("count=exact", count='exact')  # ❌ INVALID SQL SYNTAX
    .limit(20000)
    .execute()
)

# Ошибка: unexpected '=' expecting letter, digit
# Причина: select("count=exact") это НЕПРАВИЛЬНЫЙ синтаксис PostgREST
```

**Правильный синтаксис**:
```python
# Вариант 1: просто выбрать все
result = client.table("scores").select("*").limit(20000).execute()
data = result.data or []

# Вариант 2: если нужен count
result = client.table("scores").select("*", count='exact').execute()
count = result.count if hasattr(result, 'count') else len(result.data or [])
```

**Рекомендация (УРОВЕНЬ B)**:
```
1. Найти все использования .select("count=exact", count='exact')
2. Заменить на .select("*", count='exact') или просто .select("*")
3. Протестировать на Supabase (не меняет логику, только SQL синтаксис)
```

---

## 3. ПРОМЕЖУТОЧНЫЕ ПРОБЛЕМЫ (⚠️)

### Проблема #6: GEMINI API KEY ВОЗМОЖНО НЕ СКОНФИГУРИРОВАН
**Severity**: НИЗКАЯ (зависит от deployment)

```python
# В core/config.py:
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")

# Если не в .env → пустой ключ → Gemini API упадет
# Если GROQ key нет → оба упадут, но fallback был добавлен в session
```

**Рекомендация (УРОВЕНЬ C)**:
```
Проверить .env файл на сервере:
- GEMINI_API_KEY=sk-...
- GROQ_API_KEY=gsk_...
- AI_PROVIDER=groq или gemini
```

---

### Проблема #7: MODEL PERSISTENCE & CONCURRENCY
**Severity**: НИЗКАЯ (зависит от traffic)

```python
# Глобальные переменные:
MODEL_DATA = None
DF = None
GROUP_STATS = None
SHAP_EXPLAINER = None

# Проблема: если конкурентные запросы вызывают reload_model
# может быть race condition при multiprocessing
```

**Рекомендация (УРОВЕНЬ C)**:
```
Использовать lock если есть konkurentnost:
from threading import Lock
model_lock = Lock()

def safe_reload_model():
    with model_lock:
        load_model()
```

---

## 4. КАЧЕСТВО ML МОДЕЛИ 📊

### Обзор
```
┌─────────────────────────────────────────────────────────┐
│ Model Metrics                                           │
├─────────────────────────────────────────────────────────┤
│ ROC-AUC (Val 2026):    0.7605  ✅ (target > 0.75)       │
│ F1 Score (Val 2026):   0.7394  ✅ (target > 0.7)        │
│ Optimal Threshold:     0.7308  ⚠️  (very high!)        │
├─────────────────────────────────────────────────────────┤
│ Cross-Validation AUC:  0.9054  ⚠️  (perfect on 2025)   │
│ Validation AUC:        0.7605  ⚠️  (gap = 16%)          │
│ Gap Reason:            Distribution shift 37.5%         │
├─────────────────────────────────────────────────────────┤
│ Train size (2025):     24,653  apps (82.4% positive)    │
│ Val size (2026):       1,332   apps (51.5% positive)    │
│ Unseen producers est: ~99%     (producer-level split)   │
└─────────────────────────────────────────────────────────┘
```

### Оценка полезности
**🟢 AUC=0.7605 полезен для ранжирования**
- Лучше чем FCFS baseline (AUC=0.61)
- 23% улучшение над FCFS
- Но НЕ идеален (0.76 < 0.80)

**🟡 Distribution shift критичен**
- 37.5% shift между годами слишком большой
- Может быть:
  - Временной эффект (2026 более конкурентна)
  - Изменение процесса подачи (новые требования)
  - Реакция производителей на 2025 результаты

**🟢 Features адекватны**
- 24 features (4 temporal + 3 financial + 3 categorical + 12 aggregates)
- Aggregates только из train (unseen categories → median fill)
- Temporal split правильный (train 2025 → val 2026)

---

## 5. BACKEND INTEGRATION 🔗

### Supabase Schema (ОК)
```sql
✅ producers (producer_id, region, direction, total_applications, completion_rate)
✅ scores (producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent)
✅ shap_values (id, producer_id, feature, shap_value, feature_value)
✅ model_metrics (run_id, roc_auc, cv_auc_mean, ..., created_at)
✅ fairness_cache (id, data, created_at)
✅ gemini_advice (producer_id, advice, created_at)
✅ training_samples (для синтетических данных)
```

### Fallback Logic (ОК)
```python
✅ shortlist.py: Supabase fallback → in-memory compute_shortlist()
✅ producers.py: Supabase fallback → in-memory state.DF
✅ fairness.py: Supabase fallback → in-memory compute_fairness_report()
⚠️  scoring.py: NO fallback - если GROUP_STATS пустой, медленный path
```

### Caching (ОК)
```python
✅ shortlist: TTLCache(ttl=300 sec = 5 min)
✅ metrics: 10 min cache для talent aggregates
✅ fairness: 1 hour cache
✅ producers: cache per region (не очень оптимально)
```

---

## 6. ИНТЕГРАЦИЯ FRONTEND-BACKEND ⚠️

### Соответствие контрактов
```
Frontend запрашивает:  ✅ Backend отвечает:
─────────────────────────────────────────
GET /api/metrics      ✅ model metrics vs FCFS
GET /api/shortlist    ✅ top producers (с delta, hidden_talent)
GET /api/fairness     ✅ Gini, Lorenz, KW, Z-scores, heatmap
GET /api/producers    ✅ producer list с aggregates
GET /api/simulate     ✅ simulator

API несовместимость:
GET /api/shortlist/fair        ❌ fair_reranker не реализован
GET /api/counterfactual        ❌ counterfactual не реализован
GET /api/drift                 ⚠️  не тестирован
GET /api/audit                 ⚠️  не тестирован
```

---

## 7. ОТВЕТСТВЕННОСТИ ПО ПРОБЛЕМАМ 🎯

### CRITICAL (Должны быть исправлены ДО production)
✅ **Fair Reranking & Counterfactuals** → либо реализовать, либо скрыть  
✅ **Hidden Talent логика** → пересобрать пороги на 2026 данных  
✅ **Supabase SQL fix** → проверить select синтаксис во всех файлах  

### HIGH (Должны быть в дорожной карте)
⚠️ **Distribution shift mitigation** → retrain с weighting или recalibration  
⚠️ **Data mapping** → кодировать "Одобрена" статус корректно  

### MEDIUM
🟡 **Model persistence** → добавить thread locks если concurrent requests  
🟡 **Gemini API keys** → verify .env configuration  
🟡 **Error handling** — добавить более детальные error messages  

---

## 8. РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ

### УРОВЕНЬ A - Критические (1-2 дня)
```
1. ✅ Реализовать fair_reranker и counterfactual модули
   OR скрыть эти API if not ready
   
2. ✅ Пересчитать hidden_talent threshold на 2026 данных
   Текущий: delta > 10 AND ml_score > 0.7308
   Рекомендуемый: delta > 8 AND ml_score > 0.65
   
3. ✅ Исправить Supabase select синтаксис везде
   select("count=exact", count='exact') → select("*", count='exact')
```

### УРОВЕНЬ B - Важные (3-5 дней)
```
4. Добавить weighted accuracy penalty для distribution shift
   class_weight = 'balanced' in GradientBoosting
   
5. Уточнить домен: что такое "Одобрена" статус?
   Закодировать корректно
   
6. Добавить более детальные error messages
   + logging of Supabase query failures
   
7. Валидировать model performance каждый month
```

### УРОВЕНЬ C - Желательные (1-2 недели)
```
8. Добавить thread locks для MODEL_DATA если concurrent
   
9. Расширить unit tests для ml modules
   
10. Dashboard для мониторинга distribution shift
    (показать 2025 vs 2026 статистику в real-time)
```

---

## 9. ЗАКЛЮЧЕНИЕ

### Общее состояние: ⚠️ СРЕДНИЙ (7/10)

**Работает хорошо**:
- ✅ Core ML pipeline функционален
- ✅ Backend интеграция продумана
- ✅ Fallback logic предусмотрен
- ✅ Fairness metrics реализованы
- ✅ SHAP explanations работают
- ✅ Данные 36K приложений загружаются быстро

**Требует внимания**:
- ❌ Fair Reranking и Counterfactuals не реализованы
- ⚠️ Distribution shift 37.5% требует mitigation
- ⚠️ Hidden talent пороги требуют перестройки
- ⚠️ 29% приложений без разрешения статуса
- ⚠️ Supabase SQL синтаксис требует проверки

### Рекомендация по развертыванию
```
PHASE 1 (URGENT - 2 дня):
  [ ] Реализовать fair_reranker или скрыть API
  [ ] Реализовать counterfactual или скрыть API
  [ ] Пересчитать hidden_talent threshold
  
PHASE 2 (SHORT TERM - неделя):
  [ ] Fix Supabase SQL queries
  [ ] Добавить distribution shift mitigation
  [ ] Verify Gemini API config
  
PHASE 3 (LONG TERM - месяц):
  [ ] Retrain model с better handling shift
  [ ] A/B тестировать hidden talent logic
  [ ] Добавить production monitoring
```

---

**Аудит завершён**: Все основные компоненты работают, но требуется исправление 3-5 критических проблем перед production.

