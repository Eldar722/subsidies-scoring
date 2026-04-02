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


def safe_transform(encoder, series):
    known = set(encoder.classes_)
    return series.map(lambda x: encoder.transform([x])[0] if x in known else -1)


def score_dataframe(df_slice):
    """Скоринг произвольного DataFrame — возвращает df с колонкой ml_score."""
    if state.MODEL_DATA is None:
        raise HTTPException(503, "Модель не загружена")
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")

    model    = state.MODEL_DATA["model"]
    features = state.MODEL_DATA["features"]
    encoders = state.MODEL_DATA["encoders"]
    threshold = state.MODEL_DATA.get("optimal_threshold", 0.5)

    df = df_slice.copy()

    if state.GROUP_STATS:
        # Fast path: use precomputed group stats (computed once at startup).
        # Eliminates 4× groupby+merge on 32K train rows per request.
        for prefix, (group_col, stats, fill_vals) in state.GROUP_STATS.items():
            df = df.merge(stats, on=group_col, how="left")
            for col, fill_val in fill_vals.items():
                df[col] = df[col].fillna(fill_val)
    else:
        # Slow fallback: compute group stats from scratch (used before startup completes)
        train_ref = state.DF[(state.DF["year"] == 2025) & state.DF["target"].notna()].copy()
        train_ref["target"] = train_ref["target"].astype(int)
        df = _enrich_with_group_stats(df, train_ref, "Область", "reg")
        df = _enrich_with_group_stats(df, train_ref, "Направление водства", "dir")
        df = _enrich_with_group_stats(df, train_ref, "Наименование субсидирования", "sub")
        df = _enrich_with_group_stats(df, train_ref, "Район хозяйства", "dist")

    df["region_enc"]    = safe_transform(encoders["region"],    df["Область"].fillna("unk"))
    df["direction_enc"] = safe_transform(encoders["direction"], df["Направление водства"].fillna("unk"))
    df["subsidy_enc"]   = safe_transform(encoders["subsidy"],   df["Наименование субсидирования"].fillna("unk"))

    for c in features:
        if c in df.columns:
            df[c] = df[c].fillna(0)

    valid = df.dropna(subset=features)
    if len(valid) == 0:
        return pd.DataFrame()

    valid = valid.copy()
    valid["ml_score"] = model.predict_proba(valid[features])[:, 1]
    valid["ml_decision"] = (valid["ml_score"] >= threshold).astype(int)

    return valid
