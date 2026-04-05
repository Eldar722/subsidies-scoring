"""
risk_indicators.py — Advanced risk scoring for producers.

Combines multiple signal types:
  1. Behavioral anomalies (irregular submission patterns)
  2. Financial inconsistency (amount volatility vs peer group)
  3. Geographic outliers (region/direction deviation)
  4. Temporal patterns (seasonal shifts, recent changes)
  5. Peer group comparison (similar producers)

Each risk is scored 0-100 with explanation.
"""

import numpy as np
import pandas as pd
from typing import Any


def compute_risk_profile(producer_id: str, df: pd.DataFrame, scores_df: pd.DataFrame = None) -> dict:
    """Compute comprehensive risk profile for a producer.

    Returns:
        {
            "overall_risk": 0-100,
            "risk_level": "low" | "medium" | "high" | "critical",
            "signals": [
                {
                    "type": str,
                    "severity": 0-100,
                    "title": str,
                    "description": str,
                    "action": str,
                }
            ]
        }
    """
    producer_rows = df[df["producer_id"] == producer_id]
    if len(producer_rows) == 0:
        return {"overall_risk": 0, "risk_level": "unknown", "signals": []}

    signals = []

    # ── 1. BEHAVIORAL: Submission pattern irregularity ──
    if len(producer_rows) >= 3:
        dates = pd.to_datetime(producer_rows["date"].dropna()).sort_values()
        if len(dates) >= 3:
            intervals = dates.diff().dt.days.dropna()
            if len(intervals) > 1:
                cv_intervals = intervals.std() / (intervals.mean() + 1)
                if cv_intervals > 1.5:
                    signals.append({
                        "type": "behavioral",
                        "severity": min(90, int(cv_intervals * 30)),
                        "title": "Нерегулярная подача заявок",
                        "description": f"Интервалы между заявками сильно варьируются (CV={cv_intervals:.1f}). "
                                       f"Это может указывать на непредсказуемость деятельности.",
                        "action": "Проверить стабильность хозяйственной деятельности",
                    })

    # ── 2. FINANCIAL: Amount volatility vs peer group ──
    producer_avg = producer_rows["Причитающая сумма"].mean()
    producer_std = producer_rows["Причитающая сумма"].std()
    if pd.notna(producer_std) and producer_avg > 0:
        producer_cv = producer_std / producer_avg
        # Compare with peers in same region
        region = producer_rows["Область"].iloc[0]
        region_rows = df[df["Область"] == region]
        region_cv = region_rows["Причитающая сумма"].std() / (region_rows["Причитающая сумма"].mean() + 1)
        if producer_cv > region_cv * 2 and len(producer_rows) >= 3:
            signals.append({
                "type": "financial",
                "severity": min(85, int((producer_cv / region_cv - 1) * 40)),
                "title": "Аномальная вариация сумм",
                "description": f"Суммы заявок варьируются значительно сильнее, чем у коллег по региону "
                               f"(CV {producer_cv:.2f} vs {region_cv:.2f}).",
                "action": "Проверить обоснованность сумм в заявках",
            })

    # ── 3. STATUS: High rejection rate ──
    if len(producer_rows) >= 2:
        statuses = producer_rows["Статус заявки"].fillna("")
        rejected = (statuses == "Отклонена").sum() + (statuses == "Отозвано").sum()
        rejection_rate = rejected / len(producer_rows)
        if rejection_rate > 0.5:
            signals.append({
                "type": "status",
                "severity": min(95, int(rejection_rate * 100)),
                "title": "Высокий процент отклонений",
                "description": f"{rejection_rate:.0%} заявок отклонено или отозвано "
                               f"({rejected} из {len(producer_rows)}).",
                "action": "Проверить причины отклонений предыдущих заявок",
            })

    # ── 4. TEMPORAL: Recent decline in activity ──
    if len(producer_rows) >= 4:
        dates_sorted = pd.to_datetime(producer_rows["date"].dropna()).sort_values()
        if len(dates_sorted) >= 4:
            midpoint = len(dates_sorted) // 2
            first_half_span = (dates_sorted.iloc[midpoint] - dates_sorted.iloc[0]).days + 1
            second_half_span = (dates_sorted.iloc[-1] - dates_sorted.iloc[midpoint]).days + 1
            if second_half_span > first_half_span * 2 and first_half_span > 0:
                signals.append({
                    "type": "temporal",
                    "severity": min(75, int((second_half_span / (first_half_span + 1) - 1) * 20)),
                    "title": "Снижение активности",
                    "description": "В последнее время производитель подаёт заявки значительно реже.",
                    "action": "Узнать причины снижения активности",
                })

    # ── 5. PEER GROUP: Score deviation from similar producers ──
    if scores_df is not None and len(producer_rows) > 0:
        producer_score = producer_rows["ml_score"].mean() if "ml_score" in producer_rows.columns else None
        if producer_score is not None and len(scores_df) > 10:
            region = producer_rows["Область"].iloc[0]
            direction = producer_rows["Направление водства"].iloc[0]
            peers = scores_df[
                (scores_df["Область"] == region) &
                (scores_df["Направление водства"] == direction)
            ]
            if len(peers) >= 5:
                peer_mean = peers["ml_score"].mean()
                peer_std = peers["ml_score"].std() + 0.01
                z_score = abs(producer_score - peer_mean) / peer_std
                if z_score > 2:
                    signals.append({
                        "type": "peer_group",
                        "severity": min(80, int(z_score * 25)),
                        "title": "Отклонение от группы",
                        "description": f"Балл производителя значительно отличается от средних по группе "
                                       f"({producer_score:.2f} vs {peer_mean:.2f} ± {peer_std:.2f}).",
                        "action": "Проверить особенности данного производителя",
                    })

    # ── 6. NEW ENTRANT: Few applications, high amounts ──
    if len(producer_rows) <= 2:
        total_amount = producer_rows["Причитающая сумма"].sum()
        if pd.notna(total_amount) and total_amount > 0:
            region = producer_rows["Область"].iloc[0]
            region_median = df[df["Область"] == region]["Причитающая сумма"].median()
            if total_amount > region_median * 3:
                signals.append({
                    "type": "new_entrant",
                    "severity": 60,
                    "title": "Новый участник с крупными заявками",
                    "description": f"Мало заявок ({len(producer_rows)}), но общая сумма "
                                   f"значительно превышает медиану по региону ({total_amount:.0f} vs {region_median:.0f}).",
                    "action": "Проверить историю и обоснованность",
                })

    # ── Overall risk calculation ──
    if not signals:
        overall_risk = 0
    else:
        # Weighted combination: max severity (60%) + mean severity (40%)
        max_sev = max(s["severity"] for s in signals)
        mean_sev = np.mean([s["severity"] for s in signals])
        overall_risk = int(0.6 * max_sev + 0.4 * mean_sev)

    # Risk level
    if overall_risk < 20:
        risk_level = "low"
    elif overall_risk < 45:
        risk_level = "medium"
    elif overall_risk < 70:
        risk_level = "high"
    else:
        risk_level = "critical"

    return {
        "overall_risk": overall_risk,
        "risk_level": risk_level,
        "signal_count": len(signals),
        "signals": sorted(signals, key=lambda s: -s["severity"]),
    }
