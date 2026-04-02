# 🔍 ПОЛНЫЙ АУДИТ СИСТЕМЫ - ROOT CAUSE ANALYSIS

**Date**: 2026-04-02  
**Status**: 3/3 проблем идентифицировано

---

## ПРОБЛЕМА #1: BACKEND ИСПОЛЬЗУЕТ СТАРУЮ МОДЕЛЬ

### ROOT CAUSE - Точная Диагностика

**Файл**: `core/state.py` (строка 18-33)  
**Тип**: Singleton pattern + отсутствие cache invalidation

```python
# ПРОБЛЕМА: Глобальная переменная загружается ОДИН РАЗ при startup
MODEL_DATA = None  # <- Строка 7

def load_model():
    global MODEL_DATA
    if os.path.exists(MODEL_PATH):
        MODEL_DATA = joblib.load(MODEL_PATH)  # <- Загружается один раз
        # ... metrics processing
        print(f"[OK] Model loaded | AUC={MODEL_DATA['metrics']['roc_auc']:.4f}")
        return True
```

**Механизм Запуска**:
1. `main.py` → `@app.on_event("startup")` (строка 67)
2. Вызывает `load_model()` один раз
3. MODEL_DATA сохраняется в памяти FastAPI процесса
4. После обучения новой модели файл `model.pkl` обновляется ✓
5. **НО** MODEL_DATA в памяти остаётся старым ✗
6. Нужен перезапуск FastAPI чтобы загрузить новую модель

**Доказательство**:

```python
# pipeline.py строка 70-71: После обучения пытается перезагрузить
state.load_model()      # <- Это работает!
state.load_data()

# Но MODEL_DATA is global singleton в памяти
# Если train.py вызовет state.load_model() тоже в том же процессе - OK
# Если train.py отдельный процесс - MODEL_DATA не обновится в FastAPI
```

**Проверка на месте**:
- 🟢 ИСПРАВЛЕНО в предыдущих сессиях (`pipeline.py` вызывает `state.load_model()` после train)
- ✅ Подтверждение: `test_optimization.py` показал корректную загрузку

---

## ПРОБЛЕМА #2: "СКРЫТЫЕ ТАЛАНТЫ" НЕ РАБОТАЮТ

### ROOT CAUSE #2A - Undefined Variable Bug

**Файл**: `ml/baseline.py` (строка 51)  
**Тип**: Runtime error - переменная не определена

```python
def compute_shortlist(df, top_n: int = 20):
    # ... вычисления ...
    
    return {
        "total_producers": int(len(producer_scores)),
        "hidden_talent_count": hidden_talent_total,
        "optimal_threshold": threshold,  # <- 🔴 ОШИБКА: threshold не определена!
        "shortlist": top[...].to_dict(orient="records"),
    }
```

**Что случается**:
1. Функция вызвана → пытается вернуть `threshold`
2. `NameError: name 'threshold' is not defined`
3. Endpoint `/api/shortlist` падает
4. Frontend не получает shortlist с hidden_talent

**Где используется baseline.py**:
- `producers.py` → `_fallback_all_items()` (строка 107)
- `shortlist.py` → `GET /api/shortlist` (строка 89)

---

### ROOT CAUSE #2B - Несовместимые Источники Данных

**Файл**: `producers.py` (строка 29, 64)  
**Тип**: Data architecture mismatch

**Логика**:
```python
# producers.py линия 29-30: Запрашивает из Supabase
scores_resp = (
    client.table("scores")
    .select("producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent")  # <- Поле из БД
    .execute()
)

# Потом строка 64:
"hidden_talent": bool(s.get("hidden_talent", False)),  # <- Берётся из БД
```

**Проблема**:
- `hidden_talent` ожидается в таблице `scores` в Supabase
- Но `train.py` НЕ обновляет Supabase после обучения
- `train.py` только сохраняет `model.pkl` локально (строка 292)
- Supabase таблица `scores` остаётся со старыми значениями

**Fallback логика**:
```python
# producers.py строка 107-108:
def _fallback_all_items() -> list:
    if state.DF is None:
        return []
    from ml.baseline import compute_shortlist  # <- Вызывает buggy функцию!
    result = compute_shortlist(state.DF, ...)
```

Когда Supabase недоступен → fallback → ошибка в baseline.py!

---

## ПРОБЛЕМА #3: "ЭФФЕКТИВНОСТЬ СУБСИДИЙ" ВОЗВРАЩАЕТ ПУСТО

### ROOT CAUSE - Data Logic Error

**Файл**: `routers/analytics.py` (строка 38-68)  
**Тип**: Логика не учитывает реальную структуру данных

```python
def _compute_effectiveness(df: pd.DataFrame) -> dict:
    # 2025 год - много данных
    subsidized_2025 = df[
        (df["year"] == 2025) & (df["Статус заявки"] == "Исполнена")
    ]["producer_id"].unique()[:200]
    # -> 9255 уникальных производителей ✓
    
    # Фильтруем по ним
    df_sub = df[df["producer_id"].isin(subsidized_2025)].copy()
    
    # Группируем по годам для до/после сравнения
    before = yearly[yearly["year"] == 2025].set_index("producer_id")
    after  = yearly[yearly["year"] == 2026].set_index("producer_id")
    
    # Ищем производителей в ОБОИХ годах
    common = before.index.intersection(after.index)
    # -> Только 1 производитель! 🔴
    
    if len(common) == 0:
        return {"total_analyzed": 0, "improved_count": 0, ...}  # Пустой ответ
```

**Реальные Данные**:
```
Producers with Исполнена in 2025: 9,255
Producers appearing in BOTH 2025 and 2026: 1
Result: "Effectively analyzed: 0"
```

**Почему так**:
- Данные из 2025 это исторические записи о производителях которые больше не подавали заявки
- Данные из 2026 (april 2) это новые заявки от других производителей
- Мало повторений → intersect почти пуст → функция возвращает []

---

## РЕЗЮМЕ ROOT CAUSES

| # | Проблема | Компонент | Root Cause | Статус |
|---|----------|-----------|-----------|--------|
| 1 | Старая модель | `core/state.py` | Singleton без cache invalidation | ✅ FIXED |
| 2A | Hidden talents ошибка | `ml/baseline.py:51` | Undefined variable `threshold` | 🔴 TODO |
| 2B | Hidden talents источник | `producers.py` | TB не обновляется из train.py | 🔴 TODO |
| 3 | Subsidy effectiveness | `analytics.py` | Нет пересечения 2025→2026 producers | 🔴 LOGIC |

---

## ТОЧНЫЕ ФИКСЫ

### FIX #2A - mlBaseline.py Undefined Variable

**Текущий код (НЕПРАВИЛЬНО)**:
```python
def compute_shortlist(df, top_n: int = 20):
    # ... вычисления ...
    return {
        "optimal_threshold": threshold,  # ❌ Не определена
```

**ФИКС - Опция 1 (QUICK)**:
```python
def compute_shortlist(df, top_n: int = 20):
    # ...
    threshold = state.MODEL_DATA.get("optimal_threshold", 0.5) if state.MODEL_DATA else 0.5
    
    return {
        "optimal_threshold": threshold,  # ✅ Теперь определена
```

**ФИКС - Опция 2 (PROPER)**:
```python
def compute_shortlist(df, top_n: int = 20):
    from ml.hidden_talent_detector import get_optimal_threshold
    
    threshold = get_optimal_threshold()  # ✅ Централизованно
    
    return {
        "optimal_threshold": threshold,
```

**Рекомендация**: Использовать опцию 2 (уже используется get_optimal_threshold для hidden_talent)

---

### FIX #2B - Обновление Supabase после Train

**Текущий статус**: `train.py` не обновляет Supabase

**QUICK PATCH** - Добавить в конец `train.py` (после сохранения model.pkl):

```python
# === NEW - After model saved ===
if __name__ == "__main__" or True:  # If running as script
    print("\n📊 Updating Supabase scores table...")
    
    # Score all data
    from ml.scoring import score_dataframe
    scored = score_dataframe(df)  # -> ml_score для каждой заявки
    
    # Aggregate by producer
    producer_scores = scored.groupby("producer_id").agg({
        "ml_score": "mean",
        "date": ["min", "count"],
    }).reset_index()
    
    # Add hidden_talent from baseline logic
    from ml.hidden_talent_detector import detect_hidden_talents_by_delta
    producer_scores["hidden_talent"] = detect_hidden_talents_by_delta(...)
    
    # Upsert to Supabase
    try:
        from services.supabase_service import _get_client
        client = _get_client()
        for _, row in producer_scores.iterrows():
            client.table("scores").upsert({
                "producer_id": row["producer_id"],
                "ml_score": float(row["ml_score"]),
                "ml_rank": ...,  # Вычислить rank
                "hidden_talent": bool(row["hidden_talent"]),
                # ... другие поля
            }).execute()
```

**PROPER FIX** - Создать новый модуль для sync:

```python
# ml/sync_to_supabase.py - NEW FILE
def sync_scores_to_supabase(df, model_data):
    """After training, update Supabase with new scores."""
    from services.supabase_service import _get_client
    from ml.baseline import compute_shortlist
    
    result = compute_shortlist(df)  # Get shortlist with hidden_talent
    client = _get_client()
    
    # Batch upsert (Supabase rates limit ~1000/sec)
    for item in result["shortlist"]:
        client.table("scores").upsert({
            "producer_id": item["producer_id"],
            "ml_score": item["ml_score"],
            "ml_rank": item["ml_rank"],
            "hidden_talent": item["hidden_talent"],
            # ...
        }, ignore_duplicates=False).execute()
    
    print(f"✅ {len(result['shortlist'])} scores synced to Supabase")
```

Затем вызвать в `train.py`:
```python
from ml.sync_to_supabase import sync_scores_to_supabase
sync_scores_to_supabase(df_test, artifact)
```

---

### FIX #3 - Subsidy Effectiveness (LOGIC FIX)

**Проблема**: Нет производителей в обоих периодах

**Опции решения**:

**Опция A - Изменить на "per-year analysis"**:
```python
def _compute_effectiveness(df: pd.DataFrame) -> dict:
    # Вместо до/после - просто анализируем 2026
    df_2026 = df[df["year"] == 2026]
    
    # Считаем effectiveness как completion_rate по region/direction
    ...
    
    return {
        "analysis_period": "2026-Q1",
        "by_region": {...},
        "by_direction": {...},
    }
```

**Опция B - Отказаться от 2025**:
```python
# Вместо поиска producers в ОБОИХ 2025 и 2026
# Просто смотрим успешные производители в 2026

subsidized = df[
    (df["year"] == 2026) & 
    (df["Статус заявки"] == "Исполнена")
]["producer_id"].unique()

# Анализируем их статистику
...
```

**Опция C - Наисправнее (RECOMMENDED)**:
```python
def _compute_effectiveness(df: pd.DataFrame) -> dict:
    """Вернуть к базовому анализу вместо do/after сравнения."""
    
    # Какие регионы/направления наиболее успешны в 2026
    success = df[
        (df["year"] == 2026) & 
        (df["Статус заявки"] == "Исполнена")
    ]
    
    if len(success) == 0:
        return {
            "message": "Insufficient 2026 data",
            "total_analyzed": 0,
            "producers": []
        }
    
    # Group by region/direction/producer
    effectiveness = (
        success.groupby(["region", "direction", "producer_id"])
        .size()
        .to_frame("success_count")
        .sort_values("success_count", ascending=False)
    )
    
    return effectiveness.to_dict()
```

---

## ПОЛНЫЙ СПИСОК ИЗМЕНЕНИЙ

### Файлы которые РАБОТАЮТ ✅
- ✅ `pipeline.py` - уже вызывает reload после train
- ✅ `core/state.py` - уже возвращает True/False

### Файлы которые НУЖНО ФИКСИТЬ 🔴

1. **ml/baseline.py**
   - Строка 51: Добавить `threshold = ...`
   - Рекомендация: Использовать `get_optimal_threshold()`

2. **train.py**
   - Конец файла: Добавить sync to Supabase
   - Или создать `ml/sync_to_supabase.py` и вызвать из train

3. **routers/analytics.py**
   - Строка 38-68: Переписать logic для 2026 только
   - Или оставить как есть (вернёт 0, что честно)

---

## QUICK PATCH (5 минут)

```python
# 1. ml/baseline.py строка 50 - ADD BEFORE RETURN
threshold = state.MODEL_DATA.get("optimal_threshold", 0.5) if state.MODEL_DATA else 0.5

# 2. train.py строка 292 - ADD AFTER joblib.dump
from ml.scoring import score_dataframe
scored = score_dataframe(df_test)  # ml_score
# TODO: Sync to Supabase

# 3. analytics.py строка 42 - CHANGE RETURN (когда common пуст)
# Это уже правильно возвращает пусто - честное поведение
```

---

## PROPER FIX (30 минут)

1. ✅ Использовать `get_optimal_threshold()` в baseline.py
2. 📝 Создать `ml/sync_to_supabase.py`
3. 🔄 Вызвать sync в конце train.py
4. 📊 Либо переписать analytics.py для 2026-only analysis

