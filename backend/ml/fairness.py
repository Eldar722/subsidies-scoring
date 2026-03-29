import numpy as np
import pandas as pd
from fastapi import HTTPException
from scipy import stats as scipy_stats
import core.state as state


def gini(x):
    x = np.sort(x)
    n = len(x)
    if n == 0 or x.sum() == 0:
        return 0.0
    cumx = np.cumsum(x)
    return float((2 * np.sum((np.arange(1, n + 1) * x)) / (n * x.sum())) - (n + 1) / n)


def compute_fairness_report(df):
    resolved = df[df["target"].notna()].copy()

    region_amounts = resolved.groupby("Область")["Причитающая сумма"].sum().sort_values()
    amounts = region_amounts.values.astype(float)

    gini_value = gini(amounts)

    sorted_amounts = np.sort(amounts)
    cumulative = np.cumsum(sorted_amounts) / sorted_amounts.sum()
    population = np.arange(1, len(sorted_amounts) + 1) / len(sorted_amounts)
    lorenz = [
        {"population": round(float(p), 4), "cumulative_share": round(float(c), 4)}
        for p, c in zip(population, cumulative)
    ]

    region_groups = [
        g["Причитающая сумма"].dropna().values
        for _, g in resolved.groupby("Область")
        if len(g) > 5
    ]
    if len(region_groups) >= 2:
        kw_stat, kw_p = scipy_stats.kruskal(*region_groups)
    else:
        kw_stat, kw_p = 0, 1

    dir_groups = [
        g["Причитающая сумма"].dropna().values
        for _, g in resolved.groupby("Направление водства")
        if len(g) > 5
    ]
    if len(dir_groups) >= 2:
        kw_dir_stat, kw_dir_p = scipy_stats.kruskal(*dir_groups)
    else:
        kw_dir_stat, kw_dir_p = 0, 1

    region_summary = resolved.groupby("Область").agg(
        total_apps=("target", "count"),
        success_rate=("target", "mean"),
        avg_amount=("Причитающая сумма", "mean"),
        total_amount=("Причитающая сумма", "sum"),
    ).reset_index().round(4)

    heatmap = resolved.groupby(["Область", "Направление водства"]).agg(
        success_rate=("target", "mean"),
        count=("target", "count"),
    ).reset_index()
    heatmap = heatmap[heatmap["count"] >= 5].round(4)

    return {
        "gini_coefficient": round(gini_value, 4),
        "gini_interpretation": (
            "Высокое неравенство" if gini_value > 0.4
            else "Умеренное неравенство" if gini_value > 0.25
            else "Низкое неравенство"
        ),
        "lorenz_curve": lorenz,
        "kruskal_wallis": {
            "by_region": {
                "statistic": round(float(kw_stat), 4),
                "p_value": round(float(kw_p), 6),
                "significant": bool(kw_p < 0.05),
                "interpretation": "Суммы значимо различаются между регионами" if kw_p < 0.05
                                  else "Значимых различий не обнаружено",
            },
            "by_direction": {
                "statistic": round(float(kw_dir_stat), 4),
                "p_value": round(float(kw_dir_p), 6),
                "significant": bool(kw_dir_p < 0.05),
                "interpretation": "Суммы значимо различаются между направлениями" if kw_dir_p < 0.05
                                  else "Значимых различий не обнаружено",
            },
        },
        "regions": region_summary.to_dict(orient="records"),
        "heatmap": heatmap.to_dict(orient="records"),
    }
