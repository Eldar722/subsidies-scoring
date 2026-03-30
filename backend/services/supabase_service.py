"""
supabase_service.py — загрузка данных в Supabase (producers, scores, shap_values, model_metrics).
"""

import math
from supabase import create_client
from core.config import SUPABASE_URL, SUPABASE_KEY

BATCH_SIZE = 500


def _get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _clean_row(row: dict) -> dict:
    """Заменить NaN/inf на None для JSON-сериализации."""
    cleaned = {}
    for k, v in row.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def _upsert_batch(table: str, records: list, batch_size: int = BATCH_SIZE):
    """Upsert записей батчами."""
    client = _get_client()
    total = 0
    for i in range(0, len(records), batch_size):
        batch = [_clean_row(r) for r in records[i:i + batch_size]]
        client.table(table).upsert(batch).execute()
        total += len(batch)
        if total % 1000 == 0 or total == len(records):
            print(f"  {table}: {total}/{len(records)}")
    return total


def upsert_producers(producers_df):
    """Загрузить producers в Supabase."""
    records = producers_df.to_dict(orient="records")
    return _upsert_batch("producers", records)


def upsert_scores(scores_df):
    """Загрузить scores в Supabase."""
    records = scores_df.to_dict(orient="records")
    return _upsert_batch("scores", records)


def upsert_shap(shap_list):
    """Загрузить SHAP values в Supabase."""
    return _upsert_batch("shap_values", shap_list)


def upsert_metrics(metrics_dict):
    """Загрузить model_metrics в Supabase."""
    client = _get_client()
    client.table("model_metrics").insert(metrics_dict).execute()
    print(f"  model_metrics: 1 запись")
    return 1


def count_table(table: str) -> int:
    """Подсчитать количество записей в таблице."""
    client = _get_client()
    result = client.table(table).select("*", count="exact").limit(0).execute()
    return result.count


if __name__ == "__main__":
    import numpy as np
    import joblib
    from ml.data_loader import load_xlsx
    from ml.feature_engineering import build_features, FEATURES
    from ml.scoring import score_dataframe
    from ml.baseline_service import compute_baseline
    from ml.shap_service import compute_shap
    import core.state as state

    # --- 1. Загрузка модели и данных ---
    state.load_model()
    state.load_data()
    artifact = joblib.load("model.pkl")
    df = state.DF

    # --- 2. Скоринг всех заявок ---
    print("Скоринг заявок...")
    scored = score_dataframe(df)

    # --- 3. Producers ---
    print("\nПодготовка producers...")
    producers = scored.groupby("producer_id").agg(
        region=("Область", "first"),
        direction=("Направление водства", "first"),
        total_applications=("ml_score", "count"),
        completion_rate=("ml_score", "mean"),
    ).reset_index()
    print(f"  {len(producers)} производителей")
    upsert_producers(producers)

    # --- 4. Scores (с baseline) ---
    print("\nПодготовка scores...")
    producer_scores = scored.groupby("producer_id")["ml_score"].mean().to_dict()
    baseline = compute_baseline(df, producer_scores)
    scores_upload = baseline[["producer_id", "ml_score", "ml_rank", "fcfs_rank", "delta", "hidden_talent"]].copy()
    scores_upload["hidden_talent"] = scores_upload["hidden_talent"].astype(bool)
    upsert_scores(scores_upload)

    # --- 5. SHAP values (топ-5 для каждого producer) ---
    print("\nВычисление SHAP...")
    base_model = artifact["base_model"]

    # Готовим features через train fit
    resolved = df.dropna(subset=["target"]).copy()
    resolved["target"] = resolved["target"].astype(int)
    train = resolved[resolved["year"] == 2025].reset_index(drop=True)
    X_train = build_features(train, fit=True)

    # Берём уникальных производителей — одну строку на каждого
    first_idx = train.groupby("producer_id").first().reset_index()
    first_mask = train.index.isin(
        train.groupby("producer_id").apply(lambda g: g.index[0]).values
    )
    X_first = X_train[first_mask].reset_index(drop=True)
    pids_first = train[first_mask]["producer_id"].reset_index(drop=True)

    print(f"  SHAP для {len(X_first)} производителей...")
    shap_data = compute_shap(base_model, X_first, pids_first, top_n=5)
    print(f"  {len(shap_data)} записей SHAP")
    upsert_shap(shap_data)

    # --- 6. Model metrics ---
    print("\nЗагрузка метрик модели...")
    m = artifact["metrics"]
    metrics_upload = {
        "run_id": "v1_pipeline",
        "roc_auc": m["roc_auc"],
        "avg_precision": m["avg_precision"],
        "best_f1": m["best_f1"],
        "optimal_threshold": m["optimal_threshold"],
        "cv_auc_mean": m["cv_auc_mean"],
        "train_size": int(m.get("train_size", len(train))),
        "val_size": int(m.get("val_size", 0)),
    }
    upsert_metrics(metrics_upload)

    # --- 7. Проверка ---
    print("\n=== Итого в Supabase ===")
    for table in ["producers", "scores", "shap_values", "model_metrics"]:
        try:
            c = count_table(table)
            print(f"  {table}: {c}")
        except Exception as e:
            print(f"  {table}: ошибка — {e}")
