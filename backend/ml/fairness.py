"""
fairness.py — модуль справедливости: Gini, Lorenz, Kruskal-Wallis, Z-scores.
Анализ bias по регионам и направлениям животноводства.
"""

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
import core.state as state


def compute_gini(values) -> float:
    """Коэффициент Джини для списка значений (0 = равенство, 1 = неравенство)."""
    x = np.sort(np.array(values, dtype=float))
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0 or x.sum() == 0:
        return 0.0
    return float((2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum())) - (n + 1) / n)


def compute_lorenz(values, n_points=100) -> list:
    """Точки кривой Лоренца для Recharts. Возвращает [{x, y}, ...]."""
    x = np.sort(np.array(values, dtype=float))
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return []

    cumulative = np.cumsum(x) / x.sum()
    population = np.arange(1, len(x) + 1) / len(x)

    # Ресемплинг до n_points точек
    indices = np.linspace(0, len(x) - 1, n_points, dtype=int)
    return [
        {"x": round(float(population[i]), 4), "y": round(float(cumulative[i]), 4)}
        for i in indices
    ]


def compute_kruskal_wallis(df, group_col, value_col) -> dict:
    """Тест Краскела-Уоллиса: есть ли значимые различия между группами."""
    groups = [
        g[value_col].dropna().values
        for _, g in df.groupby(group_col)
        if len(g[value_col].dropna()) > 5
    ]
    if len(groups) < 2:
        return {"H": 0, "p_value": 1.0, "interpretation": "Недостаточно групп"}

    H, p = scipy_stats.kruskal(*groups)
    return {
        "H": round(float(H), 4),
        "p_value": round(float(p), 6),
        "interpretation": "Есть статистический bias" if p < 0.05 else "Значимых различий нет",
    }


def compute_z_scores(df, group_col, value_col) -> dict:
    """Z-score для каждой группы. |z| > 1 → outlier."""
    group_means = df.groupby(group_col)[value_col].mean()
    overall_mean = group_means.mean()
    overall_std = group_means.std()
    if overall_std == 0:
        overall_std = 1.0

    result = {}
    for group, mean_val in group_means.items():
        z = (mean_val - overall_mean) / overall_std
        result[str(group)] = {
            "mean_score": round(float(mean_val), 4),
            "z_score": round(float(z), 4),
            "outlier": bool(abs(z) > 1),
        }
    return result


def compute_fairness_report(df):
    """Полный fairness отчёт. Совместим с роутером (принимает state.DF).

    Возвращает:
        dict с gini_scores, gini_amounts, lorenz, kruskal, z_scores, heatmap.
    """
    from ml.scoring import score_dataframe

    resolved = df[df["target"].notna()].copy()
    resolved["target"] = resolved["target"].astype(int)

    # Скорим для ML-баллов
    scored = score_dataframe(df)
    producer_scores = scored.groupby("producer_id").agg(
        ml_score=("ml_score", "mean"),
        region=("Область", "first"),
        direction=("Направление водства", "first"),
        avg_amount=("Причитающая сумма", "mean"),
    ).reset_index()

    # Gini
    gini_scores = compute_gini(producer_scores["ml_score"].values)
    gini_amounts = compute_gini(
        resolved.groupby("producer_id")["Причитающая сумма"].sum().values
    )

    # Lorenz по баллам
    lorenz_scores = compute_lorenz(producer_scores["ml_score"].values)

    # Kruskal-Wallis
    kw_regions = compute_kruskal_wallis(producer_scores, "region", "ml_score")
    kw_directions = compute_kruskal_wallis(producer_scores, "direction", "ml_score")

    # Z-scores
    region_z = compute_z_scores(producer_scores, "region", "ml_score")
    direction_z = compute_z_scores(producer_scores, "direction", "ml_score")

    # Heatmap: region × direction → avg ML score
    heatmap_df = producer_scores.groupby(["region", "direction"]).agg(
        avg_score=("ml_score", "mean"),
        count=("ml_score", "count"),
    ).reset_index()
    heatmap_df = heatmap_df[heatmap_df["count"] >= 3]
    heatmap = [
        {
            "region": row["region"],
            "direction": row["direction"],
            "avg_score": round(float(row["avg_score"]), 4),
        }
        for _, row in heatmap_df.iterrows()
    ]

    # Lorenz по суммам (обратная совместимость)
    region_amounts = resolved.groupby("Область")["Причитающая сумма"].sum().sort_values()
    lorenz_amounts = compute_lorenz(region_amounts.values)

    # Region summary
    region_summary = resolved.groupby("Область").agg(
        total_apps=("target", "count"),
        success_rate=("target", "mean"),
        avg_amount=("Причитающая сумма", "mean"),
        total_amount=("Причитающая сумма", "sum"),
    ).reset_index().round(4)

    return {
        "gini_scores": round(gini_scores, 4),
        "gini_amounts": round(gini_amounts, 4),
        "gini_interpretation": (
            "Высокое неравенство" if gini_amounts > 0.4
            else "Умеренное неравенство" if gini_amounts > 0.25
            else "Низкое неравенство"
        ),
        "lorenz_scores": lorenz_scores,
        "lorenz_amounts": lorenz_amounts,
        "kruskal_regions": kw_regions,
        "kruskal_directions": kw_directions,
        "region_z_scores": region_z,
        "direction_z_scores": direction_z,
        "heatmap": heatmap,
        "regions": region_summary.to_dict(orient="records"),
    }


def cache_fairness_report(report: dict):
    """Кэшировать отчёт в Supabase fairness_cache."""
    from supabase import create_client
    from core.config import SUPABASE_URL, SUPABASE_KEY
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client.table("fairness_cache").insert({"report_json": report}).execute()
    print("  fairness_cache: 1 запись")


if __name__ == "__main__":
    import json
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    state.load_model()
    state.load_data()

    report = compute_fairness_report(state.DF)

    print("=== Fairness Report ===")
    print(f"Gini (баллы):  {report['gini_scores']}")
    print(f"Gini (суммы):  {report['gini_amounts']} — {report['gini_interpretation']}")
    print(f"Lorenz точек:  {len(report['lorenz_scores'])}")
    print(f"\nKruskal-Wallis регионы:     H={report['kruskal_regions']['H']}, p={report['kruskal_regions']['p_value']} — {report['kruskal_regions']['interpretation']}")
    print(f"Kruskal-Wallis направления: H={report['kruskal_directions']['H']}, p={report['kruskal_directions']['p_value']} — {report['kruskal_directions']['interpretation']}")

    print(f"\nZ-scores регионов:")
    for region, data in sorted(report["region_z_scores"].items()):
        flag = " [!] OUTLIER" if data["outlier"] else ""
        print(f"  {region:30s} mean={data['mean_score']:.4f} z={data['z_score']:+.4f}{flag}")

    print(f"\nZ-scores направлений:")
    for d, data in sorted(report["direction_z_scores"].items()):
        flag = " [!] OUTLIER" if data["outlier"] else ""
        print(f"  {d:45s} mean={data['mean_score']:.4f} z={data['z_score']:+.4f}{flag}")

    print(f"\nHeatmap записей: {len(report['heatmap'])}")

    # Кэш в Supabase
    try:
        cache_fairness_report(report)
        print("\nКэш в Supabase: OK")
    except Exception as e:
        print(f"\nКэш в Supabase: ошибка — {e}")
