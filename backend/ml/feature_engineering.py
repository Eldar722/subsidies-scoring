"""
feature_engineering.py — построение 24 признаков для модели скоринга субсидий.
Fit/transform паттерн: fit=True на train, fit=False на val.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder

# Хранилище обученных энкодеров и агрегатов
_state = {
    "encoders": {},       # {name: LabelEncoder}
    "group_stats": {},    # {(group_col, prefix): DataFrame}
    "fitted": False,
}

FEATURES = [
    # Временные (4)
    "month", "hour", "day_of_year", "day_of_week",
    # Финансовые (5)
    "Норматив", "Причитающая сумма", "amount_to_norm", "log_amount", "log_norm",
    # Категориальные (3)
    "region_enc", "direction_enc", "subsidy_enc",
    # Агрегаты: регион (3)
    "reg_sr", "reg_vol", "reg_avg_amt",
    # Агрегаты: направление (3)
    "dir_sr", "dir_vol", "dir_avg_amt",
    # Агрегаты: субсидия (3)
    "sub_sr", "sub_vol", "sub_avg_amt",
    # Агрегаты: район (3)
    "dist_sr", "dist_vol", "dist_avg_amt",
]


def _compute_group_stats(train_df, group_col, prefix):
    """Считает success_rate, volume, avg_amount по группе на train."""
    stats = train_df.groupby(group_col).agg(
        success_rate=("target", "mean"),
        volume=("target", "count"),
        avg_amount=("Причитающая сумма", "mean"),
    ).reset_index()
    stats.columns = [group_col, f"{prefix}_sr", f"{prefix}_vol", f"{prefix}_avg_amt"]
    return stats


def _merge_group_stats(df, stats, group_col, prefix, fallback_sr, fallback_vol, fallback_amt):
    """Мержит агрегаты, unseen заполняет fallback-значениями."""
    merged = df.merge(stats, on=group_col, how="left")
    merged[f"{prefix}_sr"] = merged[f"{prefix}_sr"].fillna(fallback_sr)
    merged[f"{prefix}_vol"] = merged[f"{prefix}_vol"].fillna(fallback_vol)
    merged[f"{prefix}_avg_amt"] = merged[f"{prefix}_avg_amt"].fillna(fallback_amt)
    return merged


def _safe_transform(encoder, series):
    """LabelEncoder transform с обработкой unseen категорий → -1."""
    known = set(encoder.classes_)
    return series.map(lambda x: encoder.transform([x])[0] if x in known else -1)


def build_features(df, fit=True):
    """Построить 24 признака из сырого DataFrame.

    Args:
        df: DataFrame из data_loader.load_xlsx() с колонкой target.
        fit: True — обучить энкодеры/агрегаты (train), False — применить (val).

    Returns:
        DataFrame с колонками FEATURES, готовый для модели.
    """
    result = df.copy()

    # --- Финансовые производные ---
    result["amount_to_norm"] = (
        result["Причитающая сумма"] / result["Норматив"].replace(0, np.nan)
    )
    result["log_amount"] = np.log1p(result["Причитающая сумма"].fillna(0))
    result["log_norm"] = np.log1p(result["Норматив"].fillna(0))

    # --- Категориальные LabelEncoded ---
    cat_cols = {
        "region": ("Область", "region_enc"),
        "direction": ("Направление водства", "direction_enc"),
        "subsidy": ("Наименование субсидирования", "subsidy_enc"),
    }

    if fit:
        _state["encoders"] = {}
        for name, (src_col, dst_col) in cat_cols.items():
            le = LabelEncoder()
            result[dst_col] = le.fit_transform(result[src_col].fillna("unk"))
            _state["encoders"][name] = le
    else:
        for name, (src_col, dst_col) in cat_cols.items():
            result[dst_col] = _safe_transform(
                _state["encoders"][name], result[src_col].fillna("unk")
            )

    # --- Агрегаты по группам ---
    groups = [
        ("Область", "reg"),
        ("Направление водства", "dir"),
        ("Наименование субсидирования", "sub"),
        ("Район хозяйства", "dist"),
    ]

    if fit:
        _state["group_stats"] = {}
        for group_col, prefix in groups:
            stats = _compute_group_stats(result, group_col, prefix)
            _state["group_stats"][(group_col, prefix)] = {
                "stats": stats,
                "fallback_sr": float(result["target"].mean()),
                "fallback_vol": float(stats[f"{prefix}_vol"].median()),
                "fallback_amt": float(stats[f"{prefix}_avg_amt"].median()),
            }
            result = _merge_group_stats(
                result, stats, group_col, prefix,
                _state["group_stats"][(group_col, prefix)]["fallback_sr"],
                _state["group_stats"][(group_col, prefix)]["fallback_vol"],
                _state["group_stats"][(group_col, prefix)]["fallback_amt"],
            )
    else:
        for group_col, prefix in groups:
            saved = _state["group_stats"][(group_col, prefix)]
            result = _merge_group_stats(
                result, saved["stats"], group_col, prefix,
                saved["fallback_sr"], saved["fallback_vol"], saved["fallback_amt"],
            )

    # --- Финальная очистка NaN ---
    for col in FEATURES:
        if col in result.columns:
            result[col] = result[col].fillna(0)

    _state["fitted"] = True

    return result[FEATURES]


def get_encoders():
    """Вернуть обученные LabelEncoders для scoring.py."""
    return _state["encoders"]


def get_state():
    """Вернуть полное состояние (энкодеры + агрегаты) для сохранения в model.pkl."""
    return _state


if __name__ == "__main__":
    from ml.data_loader import load_xlsx

    df = load_xlsx()

    # Целевая переменная
    POSITIVE = ["Исполнена"]
    NEGATIVE = ["Отклонена", "Отозвано"]
    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(POSITIVE), "target"] = 1
    df.loc[df["Статус заявки"].isin(NEGATIVE), "target"] = 0

    df_resolved = df.dropna(subset=["target"]).copy()
    df_resolved["target"] = df_resolved["target"].astype(int)

    train = df_resolved[df_resolved["year"] == 2025].copy()
    val = df_resolved[df_resolved["year"] == 2026].copy()

    print(f"Train: {len(train)} | Val: {len(val)}")

    # Fit на train
    X_train = build_features(train, fit=True)
    print(f"\n--- Train features ---")
    print(f"Shape: {X_train.shape}")
    print(f"Columns ({len(X_train.columns)}):\n{list(X_train.columns)}")
    print(f"\n{X_train.describe().round(2)}")

    # Transform на val
    X_val = build_features(val, fit=False)
    print(f"\n--- Val features ---")
    print(f"Shape: {X_val.shape}")
    print(f"NaN count: {X_val.isna().sum().sum()}")
