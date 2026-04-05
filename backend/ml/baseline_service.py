"""
baseline_service.py — FCFS baseline, delta, hidden talent.
Сравнивает ML ранжирование с порядком подачи (FCFS).
"""

import pandas as pd
import numpy as np
from ml.hidden_talent_detector import detect_hidden_talents_by_delta


def compute_baseline(df, model_scores: dict):
    """Вычислить FCFS ранг, delta и hidden_talent для каждого производителя.

    Args:
        df: исходный DataFrame из data_loader (с date, producer_id).
        model_scores: dict {producer_id: ml_score}.

    Returns:
        DataFrame: producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent, total_apps
    """
    # FCFS: ранг по дате первой заявки (чем раньше — тем выше)
    first_submission = (
        df.groupby("producer_id")["date"]
        .min()
        .reset_index()
        .sort_values("date")
        .reset_index(drop=True)
    )
    first_submission["fcfs_rank"] = range(1, len(first_submission) + 1)

    # ML: ранг по ml_score (по убыванию)
    scores_df = pd.DataFrame(
        list(model_scores.items()), columns=["producer_id", "ml_score"]
    )
    scores_df = scores_df.sort_values("ml_score", ascending=False).reset_index(drop=True)
    scores_df["ml_rank"] = range(1, len(scores_df) + 1)

    # Подсчет количества заявок для каждого производителя
    total_apps = df.groupby("producer_id").size().reset_index(name="total_apps")

    # Объединение
    result = scores_df.merge(
        first_submission[["producer_id", "fcfs_rank"]], on="producer_id", how="inner"
    )
    result = result.merge(
        total_apps[["producer_id", "total_apps"]], on="producer_id", how="left"
    )

    # Delta = fcfs_rank - ml_rank
    # Положительная delta → ML считает лучше чем FCFS
    # Delta = ML rank - FCFS rank (положительное значение = ML считает выше FCFS)
    result["delta"] = result["fcfs_rank"] - result["ml_rank"]

    # Hidden talent: используем centralized логика (delta-based)
    # Скрытый телант = (delta > 10) AND (ml_score > threshold)
    result["hidden_talent"] = detect_hidden_talents_by_delta(result, delta_threshold=10)

    return result[[
        "producer_id", "ml_score", "ml_rank", "fcfs_rank",
        "delta", "hidden_talent", "total_apps",
    ]]


if __name__ == "__main__":
    import joblib
    from ml.data_loader import load_xlsx
    from ml.feature_engineering import build_features
    from ml.scoring import score_dataframe
    import core.state as state

    # Загрузить модель и данные через state
    state.load_model()
    state.load_data()

    df = state.DF
    scored = score_dataframe(df)

    # Средний ml_score по producer_id
    producer_scores = scored.groupby("producer_id")["ml_score"].mean().to_dict()

    result = compute_baseline(df, producer_scores)
    print(f"Всего производителей: {len(result)}")
    print(f"Hidden talents: {result['hidden_talent'].sum()}")
    print(f"\nТоп-10 по delta (недооценены FCFS):")
    top_delta = result.nlargest(10, "delta")
    for _, r in top_delta.iterrows():
        ht = " [HT]" if r["hidden_talent"] else ""
        print(f"  {r['producer_id']} | ML#{r['ml_rank']:>5} | FCFS#{r['fcfs_rank']:>5} | delta={r['delta']:>+5} | score={r['ml_score']:.3f}{ht}")

    print(f"\nТоп-10 по delta (переоценены FCFS):")
    bottom_delta = result.nsmallest(10, "delta")
    for _, r in bottom_delta.iterrows():
        print(f"  {r['producer_id']} | ML#{r['ml_rank']:>5} | FCFS#{r['fcfs_rank']:>5} | delta={r['delta']:>+5} | score={r['ml_score']:.3f}")
