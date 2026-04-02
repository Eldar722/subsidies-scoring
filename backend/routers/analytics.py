"""
analytics.py — аналитический модуль субсидий.

1. Subsidy Effectiveness: сравнение поведения производителей до/после субсидии.
   Анализ: вырос ли % исполнения, размер заявок, частота подач.

2. Red Flags / Anti-Corruption: Isolation Forest для поиска аномальных паттернов.
   Дробление, мимикрия, кластер заявок, сумма-аномалия.
"""

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
try:
    from cachetools import TTLCache
    _analytics_cache = TTLCache(maxsize=4, ttl=1800)
except ImportError:
    _analytics_cache = {}
import core.state as state
from routers.analytics_improved import compute_all_effectiveness_metrics

router = APIRouter()


# ─────────────────────────────────────────────
# SUBSIDY EFFECTIVENESS
# ─────────────────────────────────────────────

def _compute_effectiveness(df: pd.DataFrame) -> dict:
    """
    Анализ эффективности субсидий: сравниваем производителей,
    получивших субсидию в 2025 году, с их поведением в 2026 году.

    Vectorized: single groupby pass instead of 200 full-table scans.
    """
    # Производители с исполненными заявками в 2025
    subsidized_2025 = df[
        (df["year"] == 2025) & (df["Статус заявки"] == "Исполнена")
    ]["producer_id"].unique()[:200]

    if len(subsidized_2025) == 0:
        return {"total_analyzed": 0, "improved_count": 0, "needs_review_count": 0,
                "avg_effectiveness_score": 0.0, "producers": []}

    # Filter once, then group — eliminates 200 individual df[df["producer_id"]==pid] scans
    df_sub = df[df["producer_id"].isin(subsidized_2025)].copy()

    # Pandas-2.x safe: use separate aggregations instead of groupby().apply()
    grp = df_sub.groupby(["producer_id", "year"])
    apps_count     = grp["Статус заявки"].count().rename("total_apps")
    completed_s    = (
        df_sub[df_sub["Статус заявки"] == "Исполнена"]
        .groupby(["producer_id", "year"])
        .size()
        .rename("completed")
    )
    avg_amount_s   = grp["Причитающая сумма"].mean().rename("avg_amount")
    unique_months_s = grp["month"].nunique().rename("unique_months")

    yearly = pd.concat(
        [apps_count, completed_s, avg_amount_s, unique_months_s], axis=1
    ).reset_index()
    yearly["completed"]       = yearly["completed"].fillna(0)
    yearly["completion_rate"] = yearly["completed"] / yearly["total_apps"].clip(lower=1)
    yearly["apps_per_month"]  = yearly["total_apps"] / yearly["unique_months"].clip(lower=1)
    yearly["avg_amount"]      = yearly["avg_amount"].fillna(0.0)

    before = yearly[yearly["year"] == 2025].set_index("producer_id")
    after  = yearly[yearly["year"] == 2026].set_index("producer_id")

    # Only producers present in both years
    common = before.index.intersection(after.index)
    if len(common) == 0:
        return {"total_analyzed": 0, "improved_count": 0, "needs_review_count": 0,
                "avg_effectiveness_score": 0.0, "producers": []}

    before = before.loc[common]
    after  = after.loc[common]
    region_map = df_sub.groupby("producer_id")["Область"].first()

    rate_delta     = after["completion_rate"] - before["completion_rate"]
    amount_delta   = after["avg_amount"] - before["avg_amount"]
    activity_delta = after["apps_per_month"] - before["apps_per_month"]

    safe_before_amount = before["avg_amount"].replace(0, np.nan).fillna(1.0)
    safe_before_activity = before["apps_per_month"].replace(0, np.nan).fillna(1.0)

    effectiveness = (
        50
        + (rate_delta * 30)
        + (np.minimum(amount_delta / safe_before_amount, 0.5) * 20)
        + (np.minimum(activity_delta / safe_before_activity, 0.5) * 10)
    ).clip(0, 100).round(1)

    improved     = (rate_delta > 0.05) | (amount_delta > 0) | (activity_delta > 0)
    needs_review = ~improved

    results = []
    for pid in common:
        results.append({
            "producer_id": pid,
            "region": region_map.get(pid),
            "effectiveness_score": float(effectiveness[pid]),
            "improved": bool(improved[pid]),
            "needs_review": bool(needs_review[pid]),
            "before": {
                "year": 2025,
                "total_apps": int(before.loc[pid, "total_apps"]),
                "completion_rate": round(float(before.loc[pid, "completion_rate"]), 4),
                "avg_amount": round(float(before.loc[pid, "avg_amount"]), 2),
                "apps_per_month": round(float(before.loc[pid, "apps_per_month"]), 2),
            },
            "after": {
                "year": 2026,
                "total_apps": int(after.loc[pid, "total_apps"]),
                "completion_rate": round(float(after.loc[pid, "completion_rate"]), 4),
                "avg_amount": round(float(after.loc[pid, "avg_amount"]), 2),
                "apps_per_month": round(float(after.loc[pid, "apps_per_month"]), 2),
            },
            "deltas": {
                "completion_rate": round(float(rate_delta[pid]), 4),
                "avg_amount": round(float(amount_delta[pid]), 2),
                "activity": round(float(activity_delta[pid]), 2),
            },
        })

    results.sort(key=lambda x: x["effectiveness_score"], reverse=True)

    return {
        "total_analyzed": len(results),
        "improved_count": int(improved.sum()),
        "needs_review_count": int(needs_review.sum()),
        "avg_effectiveness_score": round(float(effectiveness.mean()), 1),
        "producers": results[:50],
    }


# ─────────────────────────────────────────────
# RED FLAGS / ANTI-CORRUPTION
# ─────────────────────────────────────────────

def _compute_red_flags(df: pd.DataFrame) -> dict:
    """
    Поиск подозрительных паттернов с помощью правил и Isolation Forest.
    """
    flags = []

    # Преобразуем данные для анализа
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["Причитающая сумма"] = pd.to_numeric(df["Причитающая сумма"], errors="coerce")

    # ── Флаг 1: Дробление ──
    # Несколько разных producer_id подают одинаковые суммы в одном районе за один день
    if "Район хозяйства" in df.columns:
        df["date_day"] = df["date"].dt.date
        group_cols = ["Район хозяйства", "date_day"]
        grouped = df.groupby(group_cols + ["Причитающая сумма"]).agg(
            pid_count=("producer_id", "nunique"),
            total_apps=("producer_id", "count"),
        ).reset_index()
        suspicious_sums = grouped[(grouped["pid_count"] > 2) & (grouped["total_apps"] > 3)]

        for _, row in suspicious_sums.iterrows():
            pids = df[
                (df["Район хозяйства"] == row["Район хозяйства"])
                & (df["date_day"] == row["date_day"])
                & (df["Причитающая сумма"] == row["Причитающая сумма"])
            ]["producer_id"].unique()
            flags.append({
                "flag_type": "fragmentation",
                "risk_level": "high",
                "title": "Дробление заявок",
                "description": (
                    f"{int(row['pid_count'])} разных производителей подали одинаковую сумму "
                    f"({row['Причитающая сумма']:,.0f} ₸) в районе «{row['Район хозяйства']}» "
                    f"в один день ({row['date_day']})"
                ),
                "producer_ids": [str(p) for p in pids[:10]],
                "district": row["Район хозяйства"],
                "date": str(row["date_day"]),
                "amount": float(row["Причитающая сумма"]),
                "affected_count": int(row["pid_count"]),
            })

    # ── Флаг 2: Мимикрия — резкая смена суммы после отказа (vectorized) ──
    yearly_by_pid = df.groupby(["producer_id", "year"])["Причитающая сумма"].mean().unstack(fill_value=np.nan)
    if 2025 in yearly_by_pid.columns and 2026 in yearly_by_pid.columns:
        rejected_2025 = set(df[
            (df["year"] == 2025) & (df["Статус заявки"].isin(["Отклонена", "Отозвано"]))
        ]["producer_id"].unique())

        # Vectorized: filter + compute change_ratio without per-producer loops
        candidates = yearly_by_pid[yearly_by_pid.index.isin(rejected_2025)].copy()
        candidates = candidates.dropna(subset=[2025, 2026])
        candidates = candidates[candidates[2025] != 0]
        candidates["change_ratio"] = (candidates[2026] - candidates[2025]).abs() / candidates[2025]
        mimicry_pids = candidates[candidates["change_ratio"] > 0.5]

        if len(mimicry_pids) > 0:
            region_map = df.groupby("producer_id")["Область"].first()
            for pid, row in mimicry_pids.iterrows():
                flags.append({
                    "flag_type": "mimicry",
                    "risk_level": "medium",
                    "title": "Мимикрия после отказа",
                    "description": (
                        f"Производитель получил отказ в 2025 и резко изменил "
                        f"суммы заявок в 2026 ({row['change_ratio']*100:.0f}% изменение)"
                    ),
                    "producer_ids": [str(pid)],
                    "region": region_map.get(pid),
                    "amount_change_pct": round(float(row["change_ratio"]) * 100, 1),
                    "amount_2025": round(float(row.loc[2025]), 2),
                    "amount_2026": round(float(row.loc[2026]), 2),
                    "affected_count": 1,
                })

    # ── Флаг 3: Кластер заявок — аномально много из одного района ──
    if "Район хозяйства" in df.columns:
        district_counts = df.groupby("Район хозяйства")["producer_id"].count()
        mean_count = district_counts.mean()
        std_count = district_counts.std()
        outlier_districts = district_counts[district_counts > mean_count + 3 * std_count]

        for district, count in outlier_districts.items():
            flags.append({
                "flag_type": "cluster",
                "risk_level": "medium",
                "title": "Аномальный кластер заявок",
                "description": (
                    f"Район «{district}» содержит {int(count)} заявок — "
                    f"значительно выше среднего ({mean_count:.0f} ± {std_count:.0f})"
                ),
                "producer_ids": [],
                "district": district,
                "count": int(count),
                "mean_count": round(float(mean_count), 1),
                "affected_count": int(count),
            })

    # ── Флаг 4: Isolation Forest — общая аномальность ──
    try:
        from sklearn.ensemble import IsolationForest

        numeric_cols = ["Причитающая сумма", "Норматив", "month", "hour"]
        feat_df = df[numeric_cols].copy()
        for c in numeric_cols:
            feat_df[c] = pd.to_numeric(feat_df[c], errors="coerce").fillna(0)

        # Агрегируем по производителю
        pid_feats = df.groupby("producer_id").agg(
            avg_amount=("Причитающая сумма", "mean"),
            total_apps=("producer_id", "count"),
            avg_month=("month", "mean"),
            avg_hour=("hour", "mean"),
        ).fillna(0)

        if len(pid_feats) > 20:
            iso = IsolationForest(contamination=0.05, random_state=42)
            iso.fit(pid_feats)
            scores = iso.decision_function(pid_feats)
            anomaly_mask = iso.predict(pid_feats) == -1
            anomalous_pids = pid_feats[anomaly_mask].index.tolist()

            if anomalous_pids:
                flags.append({
                    "flag_type": "isolation_forest",
                    "risk_level": "low",
                    "title": f"ML-аномалия: {len(anomalous_pids)} производителей",
                    "description": (
                        f"Isolation Forest выявил {len(anomalous_pids)} производителей "
                        f"с аномальным поведенческим профилем (нетипичные суммы, время, активность)"
                    ),
                    "producer_ids": [str(p) for p in anomalous_pids[:20]],
                    "affected_count": len(anomalous_pids),
                })
    except Exception as e:
        print(f"[WARN] Isolation Forest failed: {e}")

    # Сортируем по уровню риска
    risk_order = {"high": 0, "medium": 1, "low": 2}
    flags.sort(key=lambda f: risk_order.get(f["risk_level"], 3))

    high = sum(1 for f in flags if f["risk_level"] == "high")
    medium = sum(1 for f in flags if f["risk_level"] == "medium")
    low = sum(1 for f in flags if f["risk_level"] == "low")

    return {
        "total_flags": len(flags),
        "high_risk": high,
        "medium_risk": medium,
        "low_risk": low,
        "flags": flags[:100],
    }


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@router.get("/analytics/subsidy-effectiveness")
def subsidy_effectiveness():
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")

    cache_key = "subsidy_effectiveness"
    if cache_key in _analytics_cache:
        return _analytics_cache[cache_key]

    result = compute_all_effectiveness_metrics(state.DF)
    _analytics_cache[cache_key] = result
    return result


@router.get("/analytics/red-flags")
def red_flags():
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")

    cache_key = "red_flags"
    if cache_key in _analytics_cache:
        return _analytics_cache[cache_key]

    result = _compute_red_flags(state.DF)
    _analytics_cache[cache_key] = result
    return result
