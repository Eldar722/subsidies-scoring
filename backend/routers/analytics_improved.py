"""
analytics_improved.py — Расширенный анализ эффективности субсидий.

3 метрики в разных табах:
1. 2025 Completed: % успешных субсидий в 2025
2. Survival Rate: сколько производителей вернулись в 2026
3. Year-over-Year: сравнение для тех, кто был в обоих годах
"""

import numpy as np
import pandas as pd


def compute_2025_completion_rate(df: pd.DataFrame) -> dict:
    """
    Метрика #1: Эффективность программы субсидий в 2025.
    Показывает: сколько заявок было исполнено из всех поданных.
    """
    df_2025 = df[df["year"] == 2025].copy()
    
    if len(df_2025) == 0:
        return {
            "metric": "2025_completion",
            "total_applications": 0,
            "completed": 0,
            "rejected": 0,
            "pending": 0,
            "completion_rate": 0.0,
            "rejected_rate": 0.0,
            "pending_rate": 0.0,
            "by_region": []
        }
    
    total = len(df_2025)
    completed = len(df_2025[df_2025["Статус заявки"] == "Исполнена"])
    rejected = len(df_2025[df_2025["Статус заявки"].isin(["Отклонена", "Отозвано"])])
    pending = len(df_2025[~df_2025["Статус заявки"].isin(["Исполнена", "Отклонена", "Отозвано"])])
    
    # По регионам
    by_region = df_2025.groupby("Область").agg({
        "producer_id": "count",
        "Статус заявки": lambda s: len(s[s == "Исполнена"])
    }).rename(columns={"producer_id": "total", "Статус заявки": "completed"})
    
    by_region["completion_rate"] = (by_region["completed"] / by_region["total"]).round(3)
    by_region = by_region.sort_values("completion_rate", ascending=False)
    
    by_region_list = [
        {
            "region": region,
            "total_applications": int(row["total"]),
            "completed": int(row["completed"]),
            "completion_rate": float(row["completion_rate"])
        }
        for region, row in by_region.iterrows()
    ]
    
    return {
        "metric": "2025_completion",
        "total_applications": int(total),
        "completed": int(completed),
        "rejected": int(rejected),
        "pending": int(pending),
        "completion_rate": round(completed / total, 3) if total > 0 else 0.0,
        "rejected_rate": round(rejected / total, 3) if total > 0 else 0.0,
        "pending_rate": round(pending / total, 3) if total > 0 else 0.0,
        "by_region": by_region_list,
        "summary": f"✅ {completed} из {total} субсидий исполнено ({round(completed/total*100, 1)}%)"
    }


def compute_survival_rate(df: pd.DataFrame) -> dict:
    """
    Метрика #2: Выживаемость производителей.
    Показывает: какой % производителей, получивших субсидию в 2025, остались активны в 2026.
    """
    # Производители, получившие субсидию в 2025
    subsidized_2025_producers = df[
        (df["year"] == 2025) & (df["Статус заявки"] == "Исполнена")
    ]["producer_id"].unique()
    
    if len(subsidized_2025_producers) == 0:
        return {
            "metric": "survival_rate",
            "initial_count": 0,
            "survived_count": 0,
            "survival_rate": 0.0,
            "summary": "Нет данных о субсидиях 2025"
        }
    
    # Производители в 2026
    producers_2026 = set(df[df["year"] == 2026]["producer_id"].unique())
    
    # Пересечение
    survived = [p for p in subsidized_2025_producers if p in producers_2026]
    
    survival_rate = len(survived) / len(subsidized_2025_producers) if len(subsidized_2025_producers) > 0 else 0.0
    
    # Анализ ситуации выживших
    if len(survived) > 0:
        df_survived = df[df["producer_id"].isin(survived)]
        
        # 2026 метрики
        survived_2026 = df_survived[df_survived["year"] == 2026]
        completed_2026 = len(survived_2026[survived_2026["Статус заявки"] == "Исполнена"])
        total_2026 = len(survived_2026)
        
        survival_details = {
            "completed_2026": int(completed_2026),
            "total_2026": int(total_2026),
            "completion_rate_2026": round(completed_2026 / total_2026, 3) if total_2026 > 0 else 0.0,
        }
    else:
        survival_details = {}
    
    return {
        "metric": "survival_rate",
        "initial_count": int(len(subsidized_2025_producers)),
        "survived_count": int(len(survived)),
        "survival_rate": round(survival_rate, 3),
        "survival_percentage": round(survival_rate * 100, 1),
        "details": survival_details,
        "summary": f"Вернулось {len(survived)} производителей из {len(subsidized_2025_producers)} ({round(survival_rate*100, 1)}%)"
    }


def compute_year_over_year_comparison(df: pd.DataFrame) -> dict:
    """
    Метрика #3: Сравнение год-в-год.
    Показывает: как изменились показатели у производителей, которые были в 2025 и 2026.
    """
    # Получившие субсидию в 2025
    subsidized_2025 = df[
        (df["year"] == 2025) & (df["Статус заявки"] == "Исполнена")
    ]["producer_id"].unique()
    
    if len(subsidized_2025) == 0:
        return {
            "metric": "year_over_year",
            "total_analyzed": 0,
            "improved_count": 0,
            "producers": []
        }
    
    df_filtered = df[df["producer_id"].isin(subsidized_2025)].copy()
    
    # Группируем по году и производителю
    grp = df_filtered.groupby(["producer_id", "year"])
    
    yearly_stats = grp.agg({
        "Статус заявки": "count",
        "Причитающая сумма": ["mean", "sum"],
        "month": "nunique"
    }).reset_index()
    
    yearly_stats.columns = ["producer_id", "year", "total_apps", "avg_amount", "total_amount", "unique_months"]
    
    # Заполняем нулями
    yearly_stats["total_apps"] = yearly_stats["total_apps"].fillna(0)
    yearly_stats["avg_amount"] = yearly_stats["avg_amount"].fillna(0)
    yearly_stats["total_amount"] = yearly_stats["total_amount"].fillna(0)
    yearly_stats["unique_months"] = yearly_stats["unique_months"].fillna(1)
    
    # Метрики на месяц
    yearly_stats["apps_per_month"] = yearly_stats["total_apps"] / yearly_stats["unique_months"].clip(lower=1)
    
    before = yearly_stats[yearly_stats["year"] == 2025].set_index("producer_id")
    after = yearly_stats[yearly_stats["year"] == 2026].set_index("producer_id")
    
    # Только те, кто в 2025 и 2026
    common = before.index.intersection(after.index)
    
    if len(common) == 0:
        return {
            "metric": "year_over_year",
            "total_analyzed": 0,
            "improved_count": 0,
            "producers": [],
            "summary": "Недостаточно данных: только 1 производитель повторил заявку в 2026"
        }
    
    before = before.loc[common]
    after = after.loc[common]
    
    region_map = df_filtered.groupby("producer_id")["Область"].first()
    
    # Вычисляем дельты
    apps_delta = after["total_apps"] - before["total_apps"]
    amount_delta = after["avg_amount"] - before["avg_amount"]
    activity_delta = after["apps_per_month"] - before["apps_per_month"]
    
    # Эффективность (0-100)
    effectiveness = (
        50
        + (np.minimum(apps_delta / before["total_apps"].clip(lower=1), 0.5) * 15)
        + (np.minimum(amount_delta / before["avg_amount"].replace(0, 1), 0.5) * 20)
        + (np.minimum(activity_delta / before["apps_per_month"].replace(0, 1), 0.5) * 15)
    ).clip(0, 100).round(1)
    
    improved = (apps_delta > 0) | (amount_delta > 0) | (activity_delta > 0)
    
    results = []
    for pid in common:
        results.append({
            "producer_id": str(pid),
            "region": region_map.get(pid),
            "effectiveness_score": float(effectiveness[pid]),
            "improved": bool(improved[pid]),
            "2025": {
                "total_apps": int(before.loc[pid, "total_apps"]),
                "avg_amount": round(float(before.loc[pid, "avg_amount"]), 2),
                "total_amount": round(float(before.loc[pid, "total_amount"]), 2),
                "apps_per_month": round(float(before.loc[pid, "apps_per_month"]), 2),
            },
            "2026": {
                "total_apps": int(after.loc[pid, "total_apps"]),
                "avg_amount": round(float(after.loc[pid, "avg_amount"]), 2),
                "total_amount": round(float(after.loc[pid, "total_amount"]), 2),
                "apps_per_month": round(float(after.loc[pid, "apps_per_month"]), 2),
            },
            "deltas": {
                "apps": int(apps_delta[pid]),
                "avg_amount": round(float(amount_delta[pid]), 2),
                "activity": round(float(activity_delta[pid]), 2),
            }
        })
    
    results.sort(key=lambda x: x["effectiveness_score"], reverse=True)
    
    return {
        "metric": "year_over_year",
        "total_analyzed": len(results),
        "improved_count": int(improved.sum()),
        "avg_effectiveness_score": round(float(effectiveness.mean()), 1),
        "producers": results,
        "summary": f"{int(improved.sum())} из {len(results)} производителей показали улучшения"
    }


def compute_all_effectiveness_metrics(df: pd.DataFrame) -> dict:
    """
    Комбинированный результат: все 3 метрики эффективности.
    """
    return {
        "metrics": {
            "completion_2025": compute_2025_completion_rate(df),
            "survival": compute_survival_rate(df),
            "year_over_year": compute_year_over_year_comparison(df),
        },
        "tabs": [
            {
                "id": "completion_2025",
                "label": "2025 Завершенные",
                "description": "Эффективность программы субсидий в 2025"
            },
            {
                "id": "survival",
                "label": "Выживаемость",
                "description": "Какой % производителей остался активен в 2026"
            },
            {
                "id": "year_over_year",
                "label": "Год-в-год сравнение",
                "description": "Развитие у производителей, которые повторили заявку"
            }
        ]
    }
