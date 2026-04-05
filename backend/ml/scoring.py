"""
scoring.py — score a DataFrame using the trained model.
Uses the SAME feature engineering as training (no leakage).
"""

import pandas as pd
import numpy as np
from fastapi import HTTPException
import core.state as state


def _enrich_with_group_stats(df_to_enrich, train_df, group_col, prefix):
    """Добавить агрегаты из train по group_col."""
    stats = train_df.groupby(group_col).agg(
        success_rate=("target", "mean"),
        volume=("target", "count"),
        avg_amount=("Причитающая сумма", "mean"),
    ).reset_index()
    stats.columns = [group_col, f"{prefix}_sr", f"{prefix}_vol", f"{prefix}_avg_amt"]
    enriched = df_to_enrich.merge(stats, on=group_col, how="left")
    for c in [f"{prefix}_sr", f"{prefix}_vol", f"{prefix}_avg_amt"]:
        fill_val = train_df["target"].mean() if "_sr" in c else stats[c].median()
        enriched[c] = enriched[c].fillna(fill_val)
    return enriched


def _compute_producer_features(df, train_ref):
    """Compute per-producer aggregates from train_ref and merge into df.

    Uses cached producer_stats from MODEL_DATA if available (faster).
    """
    # Check for cached producer stats (from model artifact)
    cached = state.MODEL_DATA.get("producer_stats")
    if cached is not None:
        stats_df = pd.DataFrame(cached["df"])
        fallbacks = cached.get("fallbacks", {})
        df = df.merge(stats_df, on="producer_id", how="left")
        for col, fallback in fallbacks.items():
            df[col] = df[col].fillna(fallback)
        return df

    # Compute from scratch
    producer_stats = train_ref.groupby("producer_id").agg(
        app_count=("target", "count"),
        app_completion=("target", "mean"),
        avg_amount_producer=("Причитающая сумма", "mean"),
        std_amount_producer=("Причитающая сумма", "std"),
    ).reset_index()
    producer_stats["std_amount_producer"] = producer_stats["std_amount_producer"].fillna(0)
    producer_stats["amount_cv"] = producer_stats["std_amount_producer"] / (
        producer_stats["avg_amount_producer"].replace(0, np.nan)
    )
    producer_stats["amount_cv"] = producer_stats["amount_cv"].fillna(0).clip(upper=5)

    global_app_count = float(train_ref["producer_id"].value_counts().median())
    global_completion = float(train_ref["target"].mean())
    global_avg_amount = float(train_ref["Причитающая сумма"].median())
    global_amount_cv = float(producer_stats["amount_cv"].median())

    fallbacks = {
        "app_count": global_app_count,
        "app_completion": global_completion,
        "avg_amount_producer": global_avg_amount,
        "amount_cv": global_amount_cv,
    }

    df = df.merge(producer_stats, on="producer_id", how="left")
    for col, fallback in fallbacks.items():
        df[col] = df[col].fillna(fallback)

    return df


def _compute_v7_features(df, train_ref):
    """Compute v7 interaction & trend features on df."""
    # Ensure producer stats are present
    if "app_count" not in df.columns:
        df = _compute_producer_features(df, train_ref)

    # month × amount interaction
    df["month_amount_inter"] = df["month"] * df["log_amount"]

    # Norm per application
    df["norm_per_app"] = df["Норматив"] / df["app_count"].replace(0, np.nan)
    df["norm_per_app"] = df["norm_per_app"].fillna(df["norm_per_app"].median()).clip(upper=1e6)

    # Completion trend
    if "reg_sr" in df.columns:
        df["completion_trend"] = df["app_completion"] - df["reg_sr"]
    else:
        df["completion_trend"] = df["app_completion"] - train_ref["target"].mean()

    # Application frequency
    df["app_frequency"] = np.log1p(df["app_count"])

    # Amount consistency
    df["amount_consistency"] = 1.0 / (df["amount_cv"] + 1.0)

    # Region bias
    if "reg_sr" in df.columns:
        df["region_bias"] = df["reg_sr"] - train_ref["target"].mean()
    else:
        df["region_bias"] = 0.0

    # Relative amount in region
    if "reg_avg_amt" in df.columns:
        df["rel_amount_in_region"] = df["Причитающая сумма"] / df["reg_avg_amt"].replace(0, np.nan)
        df["rel_amount_in_region"] = df["rel_amount_in_region"].fillna(
            df["rel_amount_in_region"].median()
        ).clip(upper=10)
    else:
        df["rel_amount_in_region"] = 1.0

    # Relative amount in direction
    if "dir_avg_amt" in df.columns:
        df["rel_amount_in_direction"] = df["Причитающая сумма"] / df["dir_avg_amt"].replace(0, np.nan)
        df["rel_amount_in_direction"] = df["rel_amount_in_direction"].fillna(
            df["rel_amount_in_direction"].median()
        ).clip(upper=10)
    else:
        df["rel_amount_in_direction"] = 1.0

    return df


def safe_transform(encoder, series):
    known = set(encoder.classes_)
    return series.map(lambda x: encoder.transform([x])[0] if x in known else -1)


def score_dataframe(df_slice):
    """Скоринг произвольного DataFrame — возвращает df с колонкой ml_score.

    Uses the SAME preprocessing as training:
    - Group stats from precomputed cache (or recomputed from train data)
    - Producer-level aggregates (app_count, completion, amount_cv)
    - v7 interaction & trend features
    - LabelEncoder transform with known classes
    - NaN fill with TRAIN medians (stored in artifact), NOT 0
    """
    if state.MODEL_DATA is None:
        raise HTTPException(503, "Модель не загружена")
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")

    model    = state.MODEL_DATA["model"]
    features = state.MODEL_DATA["features"]
    encoders = state.MODEL_DATA["encoders"]
    threshold = state.MODEL_DATA.get("optimal_threshold", 0.5)
    train_medians = state.MODEL_DATA.get("train_medians", {})

    df = df_slice.copy()

    # ── Group stats ──
    if state.GROUP_STATS:
        for prefix, (group_col, stats, fill_vals) in state.GROUP_STATS.items():
            df = df.merge(stats, on=group_col, how="left")
            for col, fill_val in fill_vals.items():
                df[col] = df[col].fillna(fill_val)
    else:
        train_ref = state.DF[(state.DF["year"] == 2025) & state.DF["target"].notna()].copy()
        train_ref["target"] = train_ref["target"].astype(int)
        df = _enrich_with_group_stats(df, train_ref, "Область", "reg")
        df = _enrich_with_group_stats(df, train_ref, "Направление водства", "dir")
        df = _enrich_with_group_stats(df, train_ref, "Наименование субсидирования", "sub")
        df = _enrich_with_group_stats(df, train_ref, "Район хозяйства", "dist")

    # ── Producer-level features ──
    train_ref = state.DF[(state.DF["year"] == 2025) & state.DF["target"].notna()].copy()
    train_ref["target"] = train_ref["target"].astype(int)
    df = _compute_producer_features(df, train_ref)

    # ── v7 features ──
    df = _compute_v7_features(df, train_ref)

    # ── Encode categoricals ──
    df["region_enc"]    = safe_transform(encoders["region"],    df["Область"].fillna("unk"))
    df["direction_enc"] = safe_transform(encoders["direction"], df["Направление водства"].fillna("unk"))
    df["subsidy_enc"]   = safe_transform(encoders["subsidy"],   df["Наименование субсидирования"].fillna("unk"))

    # ── Fill NaN with train medians ──
    for c in features:
        if c in df.columns:
            fill_val = train_medians.get(c, 0.0)
            df[c] = df[c].fillna(fill_val)

    valid = df.dropna(subset=features)
    if len(valid) == 0:
        return pd.DataFrame()

    valid = valid.copy()

    X_to_predict = valid[features].values if hasattr(valid[features], 'values') else valid[features]
    valid["ml_score"] = model.predict_proba(X_to_predict)[:, 1]
    valid["ml_decision"] = (valid["ml_score"] >= threshold).astype(int)

    return valid
