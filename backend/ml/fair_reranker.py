"""
fair_reranker.py — post-processing fairness reranking.
Гарантирует пропорциональное представительство регионов/направлений в шортлисте.
"""

import pandas as pd
import numpy as np


def compute_fair_shortlist(
    producers_df: pd.DataFrame,
    score_col: str = "ml_score",
    group_col: str = "region",
    top_n: int = 20,
    tolerance: float = 0.5,
) -> dict:
    """Справедливый шортлист с constraint на представительство групп.

    Args:
        producers_df: DataFrame с producer_id, ml_score, region, direction.
        score_col: колонка с баллом.
        group_col: по какой группе балансировать (region или direction).
        top_n: размер шортлиста.
        tolerance: макс допустимое отклонение от пропорциональной доли (0.5 = 50%).

    Returns:
        dict: fair_shortlist, original_shortlist, swaps, fairness_improvement
    """
    df = producers_df.copy()

    # Исходный шортлист (чисто по score)
    original = df.nlargest(top_n, score_col)
    original_ids = set(original["producer_id"])

    # Пропорциональная доля каждой группы в популяции
    group_proportions = df[group_col].value_counts(normalize=True)

    # Фактическая доля в шортлисте
    shortlist = original.copy()
    shortlist_proportions = shortlist[group_col].value_counts(normalize=True)

    swaps = []

    # Итеративная корректировка
    for _ in range(top_n):
        # Пересчитать текущие доли
        current_props = shortlist[group_col].value_counts(normalize=True)

        # Найти наиболее переrrepresented группу
        max_excess = 0
        over_group = None
        for group in current_props.index:
            expected = group_proportions.get(group, 0)
            actual = current_props.get(group, 0)
            excess = actual - expected
            if excess > max_excess and excess > expected * tolerance:
                max_excess = excess
                over_group = group

        if over_group is None:
            break  # всё сбалансировано

        # Найти наиболее underrepresented группу
        min_deficit = 0
        under_group = None
        for group in group_proportions.index:
            expected = group_proportions.get(group, 0)
            actual = current_props.get(group, 0)
            deficit = expected - actual
            if deficit > min_deficit:
                min_deficit = deficit
                under_group = group

        if under_group is None:
            break

        # Заменить: слабейший из over_group → сильнейший не-в-шортлисте из under_group
        over_candidates = shortlist[shortlist[group_col] == over_group].nsmallest(1, score_col)
        if len(over_candidates) == 0:
            break

        remove_id = over_candidates.iloc[0]["producer_id"]
        remove_score = over_candidates.iloc[0][score_col]

        not_in_shortlist = df[
            (df[group_col] == under_group) &
            (~df["producer_id"].isin(shortlist["producer_id"]))
        ]
        if len(not_in_shortlist) == 0:
            break

        add_candidate = not_in_shortlist.nlargest(1, score_col).iloc[0]
        add_id = add_candidate["producer_id"]
        add_score = add_candidate[score_col]

        # Выполнить замену
        shortlist = shortlist[shortlist["producer_id"] != remove_id]
        shortlist = pd.concat([shortlist, not_in_shortlist.nlargest(1, score_col)], ignore_index=True)

        swaps.append({
            "removed": {"producer_id": str(remove_id), "score": round(float(remove_score), 4), "group": str(over_group)},
            "added": {"producer_id": str(add_id), "score": round(float(add_score), 4), "group": str(under_group)},
            "reason": f"{under_group} недопредставлен (доля {current_props.get(under_group, 0):.0%} vs ожидаемая {group_proportions.get(under_group, 0):.0%})",
        })

    # Метрики улучшения
    final_props = shortlist[group_col].value_counts(normalize=True)

    def representation_gap(props):
        gaps = []
        for group in group_proportions.index:
            expected = group_proportions.get(group, 0)
            actual = props.get(group, 0)
            if expected > 0:
                gaps.append(abs(actual - expected) / expected)
        return float(np.mean(gaps)) if gaps else 0

    gap_before = representation_gap(shortlist_proportions)
    gap_after = representation_gap(final_props)

    # Score drop
    original_avg = original[score_col].mean()
    fair_avg = shortlist[score_col].mean()

    fair_list = shortlist.sort_values(score_col, ascending=False)

    return {
        "fair_shortlist": fair_list[[
            "producer_id", score_col, group_col
        ]].round(4).to_dict(orient="records"),
        "original_shortlist": original[[
            "producer_id", score_col, group_col
        ]].sort_values(score_col, ascending=False).round(4).to_dict(orient="records"),
        "swaps": swaps,
        "total_swaps": len(swaps),
        "fairness_improvement": {
            "representation_gap_before": round(gap_before, 4),
            "representation_gap_after": round(gap_after, 4),
            "improvement_pct": round((1 - gap_after / (gap_before + 1e-8)) * 100, 1),
        },
        "score_impact": {
            "original_avg_score": round(float(original_avg), 4),
            "fair_avg_score": round(float(fair_avg), 4),
            "score_drop_pct": round((1 - fair_avg / (original_avg + 1e-8)) * 100, 2),
        },
        "group_distribution": {
            "population": {str(k): round(float(v), 4) for k, v in group_proportions.items()},
            "original_shortlist": {str(k): round(float(v), 4) for k, v in shortlist_proportions.items()},
            "fair_shortlist": {str(k): round(float(v), 4) for k, v in final_props.items()},
        },
    }
