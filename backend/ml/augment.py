"""
augment.py — синтетическое дополнение обучающих данных.

Метод: Gaussian noise на числовых признаках minority class (bootstrap + jitter).
Почему не SMOTE: данные mixed (categorical + numerical), деревья плохо
используют интерполяцию в feature space — Bootstrap+Noise предпочтительнее.
Почему не синтез через GAN/VAE: избыточная сложность для 5k негативных сэмплов.

Negative class (target=0) = Отклонена + Отозвано — это ~5k из ~23k resolved строк.
Цель: довести соотношение до ~1:2 (с 1:4), что снизит порог решения и улучшит recall neg.
"""

import numpy as np
import pandas as pd


# Числовые колонки, к которым применяем noise
_NUMERIC_COLS = ["Причитающая сумма", "Норматив"]
# Временные, к которым применяем целочисленный jitter
_HOUR_COL = "hour"


def augment_minority(
    df: pd.DataFrame,
    target_col: str = "target",
    target_ratio: float = 0.35,
    noise_std: float = 0.04,
    random_state: int = 42,
) -> pd.DataFrame:
    """Дополнить minority class (target=0) синтетическими сэмплами.

    Args:
        df: train DataFrame с колонкой target (0/1), уже отфильтрованный (только resolved).
        target_col: имя колонки с целевой переменной.
        target_ratio: желаемая доля minority (target=0) после augmentation.
            По умолчанию 0.35 → соотношение ~1:1.86 вместо исходного ~1:4.
        noise_std: доля от std числовой колонки для Gaussian шума.
        random_state: seed для воспроизводимости.

    Returns:
        DataFrame только с синтетическими строками (без оригиналов).
        Содержит колонку is_synthetic=True.
        Гарантирует year == train year (2025) — не попадёт в val split.
    """
    rng = np.random.default_rng(random_state)

    minority = df[df[target_col] == 0].copy()
    majority = df[df[target_col] == 1].copy()

    n_min = len(minority)
    n_maj = len(majority)
    n_total = n_min + n_maj

    if n_min == 0:
        return pd.DataFrame(columns=df.columns)

    # Сколько синтетических строк нужно:
    # target_ratio = (n_min + n_synth) / (n_total + n_synth)
    # => n_synth = (target_ratio * n_total - n_min) / (1 - target_ratio)
    n_synth = int((target_ratio * n_total - n_min) / (1 - target_ratio))
    n_synth = max(0, n_synth)

    if n_synth == 0:
        print(f"[augment] Minority уже >= {target_ratio:.0%} — augmentation не нужна.")
        return pd.DataFrame(columns=df.columns)

    print(f"[augment] Minority: {n_min} ({n_min/n_total:.1%}) → +{n_synth} синтетических → "
          f"{n_min+n_synth}/{n_total+n_synth} ({(n_min+n_synth)/(n_total+n_synth):.1%})")

    # Bootstrap из minority
    idx = rng.integers(0, n_min, size=n_synth)
    synthetic = minority.iloc[idx].reset_index(drop=True).copy()

    # Gaussian noise на числовых колонках
    for col in _NUMERIC_COLS:
        if col not in synthetic.columns:
            continue
        col_std = minority[col].dropna().std()
        if col_std > 0 and col_std == col_std:  # not NaN
            noise = rng.normal(0, noise_std * col_std, size=n_synth)
            synthetic[col] = (synthetic[col].fillna(0).values + noise).clip(min=0)

    # Целочисленный jitter на hour (-1, 0, +1)
    if _HOUR_COL in synthetic.columns:
        jitter = rng.integers(-1, 2, size=n_synth)
        synthetic[_HOUR_COL] = (synthetic[_HOUR_COL].fillna(0).astype(int).values + jitter).clip(0, 23)

    synthetic["is_synthetic"] = True
    # Гарантируем year=2025 чтобы не сломать temporal split
    if "year" in synthetic.columns:
        synthetic["year"] = 2025

    return synthetic


def get_augmentation_stats(original_df: pd.DataFrame, synthetic_df: pd.DataFrame, target_col: str = "target") -> dict:
    """Статистика augmentation для логирования."""
    n_orig = len(original_df)
    n_synth = len(synthetic_df)
    n_total = n_orig + n_synth

    orig_pos = int((original_df[target_col] == 1).sum())
    orig_neg = int((original_df[target_col] == 0).sum())
    synth_neg = int((synthetic_df[target_col] == 0).sum()) if n_synth > 0 else 0

    return {
        "n_original": n_orig,
        "n_synthetic": n_synth,
        "n_total": n_total,
        "orig_positive": orig_pos,
        "orig_negative": orig_neg,
        "synth_negative": synth_neg,
        "ratio_before": round(orig_neg / max(orig_pos, 1), 3),
        "ratio_after": round((orig_neg + synth_neg) / max(orig_pos, 1), 3),
    }
