"""
simulator_service.py — симулятор весов для шортлиста.
Пересчитывает взвешенный score при изменении слайдеров.
"""

import numpy as np
import pandas as pd
from ml.scoring import score_dataframe
import core.state as state

DEFAULT_WEIGHTS = {
    "completion_rate": 0.35,
    "approval_rate": 0.25,
    "direction_diversity": 0.20,
    "apps_per_month": 0.10,
    "working_hours": 0.10,
}


def _build_producer_features(df):
    """Агрегировать признаки по producer_id для взвешенного скоринга."""
    resolved = df[df["target"].notna()].copy()

    producers = resolved.groupby("producer_id").agg(
        completion_rate=("target", "mean"),
        total_apps=("target", "count"),
        region=("Область", "first"),
        direction=("Направление водства", "first"),
    ).reset_index()

    # approval_rate: доля не-отклонённых среди всех заявок producer
    all_apps = df.groupby("producer_id").size().reset_index(name="all_apps")
    rejected = df[df["Статус заявки"].isin(["Отклонена", "Отозвано"])].groupby("producer_id").size().reset_index(name="rejected")
    producers = producers.merge(all_apps, on="producer_id", how="left")
    producers = producers.merge(rejected, on="producer_id", how="left")
    producers["rejected"] = producers["rejected"].fillna(0)
    producers["approval_rate"] = 1 - (producers["rejected"] / producers["all_apps"].replace(0, 1))

    # direction_diversity: сколько уникальных направлений у producer / макс
    dir_count = df.groupby("producer_id")["Направление водства"].nunique().reset_index(name="n_directions")
    producers = producers.merge(dir_count, on="producer_id", how="left")
    max_dirs = producers["n_directions"].max() or 1
    producers["direction_diversity"] = producers["n_directions"] / max_dirs

    # apps_per_month: заявок в месяц
    date_range = df.groupby("producer_id")["date"].agg(["min", "max"]).reset_index()
    date_range["months"] = ((date_range["max"] - date_range["min"]).dt.days / 30.0).clip(lower=1)
    producers = producers.merge(date_range[["producer_id", "months"]], on="producer_id", how="left")
    producers["apps_per_month"] = producers["total_apps"] / producers["months"].replace(0, 1)

    # working_hours: доля заявок поданных в рабочее время (9-18)
    df_with_hour = df.copy()
    df_with_hour["is_working"] = df_with_hour["hour"].between(9, 18).astype(int)
    wh = df_with_hour.groupby("producer_id")["is_working"].mean().reset_index(name="working_hours")
    producers = producers.merge(wh, on="producer_id", how="left")

    # Нормализация 0-1
    for col in ["completion_rate", "approval_rate", "direction_diversity", "apps_per_month", "working_hours"]:
        producers[col] = producers[col].fillna(0)
        col_max = producers[col].max()
        if col_max > 0:
            producers[col] = producers[col] / col_max

    return producers


def simulate(weights: dict, top_n: int = 20, baseline_top_n: int = 20) -> dict:
    """Пересчитать шортлист с новыми весами.

    Args:
        weights: dict {completion_rate, approval_rate, direction_diversity,
                       apps_per_month, working_hours} — суммой ~1.0
        top_n: размер нового шортлиста
        baseline_top_n: размер базового шортлиста для сравнения

    Returns:
        dict: shortlist, entered, left, hidden_talent_count, weights_used
    """
    if state.DF is None or state.MODEL_DATA is None:
        raise RuntimeError("Data or model not loaded")

    # Нормализация весов
    total = sum(weights.values()) or 1.0
    weights = {k: v / total for k, v in weights.items()}

    producers = _build_producer_features(state.DF)

    # Взвешенный score
    producers["weighted_score"] = sum(
        producers[col] * weights.get(col, 0)
        for col in DEFAULT_WEIGHTS.keys()
        if col in producers.columns
    )

    # ML baseline для сравнения
    scored = score_dataframe(state.DF)
    ml_scores = scored.groupby("producer_id")["ml_score"].mean().reset_index()
    producers = producers.merge(ml_scores, on="producer_id", how="left")
    producers["ml_score"] = producers["ml_score"].fillna(0)

    # Hidden talent
    score_med = producers["ml_score"].median()
    apps_med = producers["total_apps"].median()
    producers["hidden_talent"] = (
        (producers["ml_score"] > score_med) &
        (producers["total_apps"] < apps_med)
    )

    # Базовый шортлист (по ml_score)
    baseline_ids = set(
        producers.nlargest(baseline_top_n, "ml_score")["producer_id"]
    )

    # Новый шортлист (по weighted_score)
    new_top = producers.nlargest(top_n, "weighted_score")
    new_ids = set(new_top["producer_id"])

    entered = sorted(new_ids - baseline_ids)
    left = sorted(baseline_ids - new_ids)

    shortlist = new_top[[
        "producer_id", "weighted_score", "ml_score",
        "region", "direction", "hidden_talent",
        "completion_rate", "approval_rate",
    ]].round(4).to_dict(orient="records")

    return {
        "shortlist": shortlist,
        "entered": entered,
        "left": left,
        "hidden_talent_count": int(new_top["hidden_talent"].sum()),
        "weights_used": {k: round(v, 4) for k, v in weights.items()},
    }


if __name__ == "__main__":
    import sys
    import json
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    state.load_model()
    state.load_data()

    # Тест 1: дефолтные веса
    print("=== Дефолтные веса ===")
    result = simulate(DEFAULT_WEIGHTS)
    print(f"Entered: {len(result['entered'])} | Left: {len(result['left'])} | HT: {result['hidden_talent_count']}")

    # Тест 2: перекос на completion_rate
    print("\n=== Перекос на completion_rate (80%) ===")
    result2 = simulate({"completion_rate": 0.8, "approval_rate": 0.05, "direction_diversity": 0.05, "apps_per_month": 0.05, "working_hours": 0.05})
    print(f"Entered: {len(result2['entered'])} | Left: {len(result2['left'])} | HT: {result2['hidden_talent_count']}")

    # Тест 3: равные веса
    print("\n=== Равные веса ===")
    result3 = simulate({"completion_rate": 0.2, "approval_rate": 0.2, "direction_diversity": 0.2, "apps_per_month": 0.2, "working_hours": 0.2})
    print(f"Entered: {len(result3['entered'])} | Left: {len(result3['left'])} | HT: {result3['hidden_talent_count']}")

    print(f"\nТоп-5 (дефолт):")
    for p in result["shortlist"][:5]:
        ht = " [HT]" if p["hidden_talent"] else ""
        print(f"  {p['producer_id']} | w={p['weighted_score']:.4f} | ml={p['ml_score']:.4f} | {p['region']}{ht}")
