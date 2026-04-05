"""
counterfactual.py — контрфактические объяснения.
"Что изменить чтобы получить субсидию" — actionable рекомендации из модели.
"""

import numpy as np
import pandas as pd

# Управляемые признаки (производитель может повлиять)
ACTIONABLE_FEATURES = {
    "month": {"name": "Месяц подачи", "direction": "both", "step": 1, "min": 1, "max": 12},
    "hour": {"name": "Час подачи", "direction": "both", "step": 1, "min": 8, "max": 18},
    "day_of_week": {"name": "День недели", "direction": "both", "step": 1, "min": 0, "max": 4},
    "amount_to_norm": {"name": "Отношение суммы к нормативу", "direction": "down", "step": 0.1, "min": 0.5, "max": 5},
    "log_amount": {"name": "Сумма заявки", "direction": "both", "step": 0.5, "min": 5, "max": 20},
}

# Неуправляемые — регион, направление, агрегаты, v7 features (менять нельзя)
IMMUTABLE_FEATURES = {
    "region_enc", "direction_enc", "subsidy_enc",
    "reg_sr", "reg_vol", "reg_avg_amt",
    "dir_sr", "dir_vol", "dir_avg_amt",
    "sub_sr", "sub_vol", "sub_avg_amt",
    "dist_sr", "dist_vol", "dist_avg_amt",
    "Норматив", "Причитающая сумма", "log_norm",
    "day_of_year",
    # v7 features
    "month_amount_inter", "norm_per_app", "completion_trend",
    "app_frequency", "amount_consistency", "region_bias",
    "rel_amount_in_region", "rel_amount_in_direction",
}


def find_counterfactual(
    model,
    features: list,
    current_values: np.ndarray,
    threshold: float,
    max_iterations: int = 200,
) -> dict:
    """Найти минимальное изменение управляемых признаков для score > threshold.

    Args:
        model: обученная модель с predict_proba.
        features: список имён признаков.
        current_values: текущие значения признаков (1D array).
        threshold: целевой порог score.
        max_iterations: макс итераций поиска.

    Returns:
        dict: {achievable, current_score, target_score, changes, new_score}
    """
    x = current_values.copy().astype(float)
    feature_idx = {f: i for i, f in enumerate(features)}

    current_score = float(model.predict_proba(x.reshape(1, -1))[0, 1])

    if current_score >= threshold:
        return {
            "achievable": True,
            "current_score": round(current_score, 4),
            "target_score": round(threshold, 4),
            "new_score": round(current_score, 4),
            "changes": [],
            "message": "Производитель уже выше порога",
        }

    best_x = x.copy()
    best_score = current_score

    # Greedy search: на каждой итерации пробуем изменить один управляемый признак
    for _ in range(max_iterations):
        if best_score >= threshold:
            break

        best_gain = 0
        best_feature = None
        best_new_val = None

        for feat, meta in ACTIONABLE_FEATURES.items():
            if feat not in feature_idx:
                continue
            idx = feature_idx[feat]

            # Пробуем шаг вверх и вниз
            for direction in [+1, -1]:
                if meta["direction"] == "down" and direction == +1:
                    continue
                if meta["direction"] == "up" and direction == -1:
                    continue

                candidate = best_x.copy()
                new_val = candidate[idx] + direction * meta["step"]
                new_val = np.clip(new_val, meta["min"], meta["max"])

                if new_val == candidate[idx]:
                    continue

                candidate[idx] = new_val
                score = float(model.predict_proba(candidate.reshape(1, -1))[0, 1])
                gain = score - best_score

                if gain > best_gain:
                    best_gain = gain
                    best_feature = feat
                    best_new_val = new_val

        if best_feature is None:
            break

        best_x[feature_idx[best_feature]] = best_new_val
        best_score += best_gain

    # Собрать изменения
    changes = []
    for feat, meta in ACTIONABLE_FEATURES.items():
        if feat not in feature_idx:
            continue
        idx = feature_idx[feat]
        old_val = float(x[idx])
        new_val = float(best_x[idx])
        if abs(new_val - old_val) > 1e-6:
            impact = float(
                model.predict_proba(best_x.reshape(1, -1))[0, 1] -
                model.predict_proba(
                    np.where(np.arange(len(best_x)) == idx, x[idx], best_x).reshape(1, -1)
                )[0, 1]
            )
            changes.append({
                "feature": feat,
                "feature_name": meta["name"],
                "old_value": round(old_val, 2),
                "new_value": round(new_val, 2),
                "impact": round(impact, 4),
                "recommendation": _format_recommendation(feat, old_val, new_val),
            })

    changes = sorted(changes, key=lambda c: -abs(c["impact"]))

    return {
        "achievable": best_score >= threshold,
        "current_score": round(current_score, 4),
        "target_score": round(threshold, 4),
        "new_score": round(best_score, 4),
        "score_gain": round(best_score - current_score, 4),
        "changes": changes,
        "message": (
            f"Балл можно поднять с {current_score:.1%} до {best_score:.1%}"
            if best_score >= threshold
            else f"Максимально достижимый балл: {best_score:.1%} (цель: {threshold:.1%})"
        ),
    }


def _format_recommendation(feature, old_val, new_val):
    """Человекочитаемая рекомендация."""
    templates = {
        "month": "Подавайте заявку в {new} месяце вместо {old}",
        "hour": "Подавайте в {new}:00 вместо {old}:00",
        "day_of_week": "Подавайте в {day_new} вместо {day_old}",
        "amount_to_norm": "Уменьшите соотношение суммы к нормативу с {old:.1f} до {new:.1f}",
        "log_amount": "Скорректируйте сумму заявки",
    }

    days = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"]

    if feature == "day_of_week":
        return templates[feature].format(
            day_old=days[int(old_val) % 7],
            day_new=days[int(new_val) % 7],
        )
    elif feature == "month":
        months = ["", "январе", "феврале", "марте", "апреле", "мае", "июне",
                  "июле", "августе", "сентябре", "октябре", "ноябре", "декабре"]
        return f"Подавайте заявку в {months[int(new_val)]} вместо {months[int(old_val)]}"

    return templates.get(feature, "").format(old=old_val, new=new_val)
