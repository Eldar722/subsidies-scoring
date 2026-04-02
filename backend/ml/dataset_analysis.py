"""
dataset_analysis.py — детальный анализ датасета и выявление проблем для калибровки.
Проверяет:
  - Дисбаланс классов (особенно между train и val)
  - Covariate shift (различия в распределениях)
  - Calibration status (ожидаемое vs реальное распределение вероятностей)
  - Feature correlations с target
"""

import pandas as pd
import numpy as np
from scipy.stats import ks_2samp, chi2_contingency
from sklearn.metrics import brier_score_loss, log_loss
import warnings
warnings.filterwarnings("ignore")


def analyze_covariate_shift(train_df, val_df, numeric_features):
    """Проверить, есть ли covariate shift между train и val.
    
    Returns:
        dict с KS-test p-values для каждого признака.
    """
    shifts = {}
    for feat in numeric_features:
        if feat in train_df.columns and feat in val_df.columns:
            train_vals = train_df[feat].dropna()
            val_vals = val_df[feat].dropna()
            
            if len(train_vals) > 0 and len(val_vals) > 0:
                stat, pval = ks_2samp(train_vals, val_vals)
                shifts[feat] = {"ks_stat": float(stat), "p_value": float(pval)}
    
    return shifts


def compute_calibration_analysis(y_true, y_proba, n_bins=10):
    """Проанализировать calibration: ожидаемое vs реальное распределение вероятностей.
    
    Returns:
        dict с метриками calibration.
    """
    # Brier Score (средний квадрат ошибки вероятностей)
    brier = brier_score_loss(y_true, y_proba)
    
    # Log Loss (cross-entropy)
    logloss = log_loss(y_true, y_proba)
    
    # Calibration curve (ожидаемое vs реальное)
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    
    bin_sums = np.zeros(n_bins)
    bin_true = np.zeros(n_bins)
    bin_total = np.zeros(n_bins)
    
    for i in range(n_bins):
        mask = (y_proba >= bins[i]) & (y_proba < bins[i + 1])
        if i == n_bins - 1:  # Последний бин включает 1.0
            mask = (y_proba >= bins[i]) & (y_proba <= bins[i + 1])
        
        bin_sums[i] = np.sum(y_proba[mask])
        bin_true[i] = np.sum(y_true[mask])
        bin_total[i] = np.sum(mask)
    
    # Избегаем деления на 0
    bin_total = np.where(bin_total > 0, bin_total, np.nan)
    expected_prob = bin_sums / bin_total
    observed_freq = bin_true / bin_total
    
    # Expected Calibration Error (ECE)
    ece = np.nanmean(np.abs(expected_prob - observed_freq))
    
    return {
        "brier_score": float(brier),
        "log_loss": float(logloss),
        "ece": float(ece),
        "calibration_curve": {
            "bin_centers": bin_centers.tolist(),
            "expected_prob": expected_prob.tolist(),
            "observed_freq": observed_freq.tolist(),
            "bin_counts": bin_total.tolist(),
        }
    }


def full_dataset_analysis(df, train_mask, val_mask, numeric_features, cat_features):
    """Полный анализ датасета.
    
    Args:
        df: полный DataFrame
        train_mask: boolean mask для train
        val_mask: boolean mask для val
        numeric_features: список числовых признаков
        cat_features: список категориальных признаков
    
    Returns:
        dict с детальным анализом.
    """
    train_df = df[train_mask].copy()
    val_df = df[val_mask].copy()
    
    # Целеве распределение
    train_target_dist = train_df["target"].value_counts(normalize=True).to_dict()
    val_target_dist = val_df["target"].value_counts(normalize=True).to_dict()
    
    analysis = {
        "dataset_info": {
            "total_rows": len(df),
            "train_rows": len(train_df),
            "val_rows": len(val_df),
        },
        "class_distribution": {
            "train": {str(k): v for k, v in sorted(train_target_dist.items())},
            "val": {str(k): v for k, v in sorted(val_target_dist.items())},
        },
        "class_imbalance_ratio": {
            "train": float(train_target_dist.get(1, 0) / max(train_target_dist.get(0, 1), 0.001)),
            "val": float(val_target_dist.get(1, 0) / max(val_target_dist.get(0, 1), 0.001)),
        },
        "covariate_shift": analyze_covariate_shift(train_df, val_df, numeric_features),
        "numeric_stats": {},
        "categorical_stats": {},
    }
    
    # Числовые признаки
    for feat in numeric_features:
        if feat in train_df.columns:
            analysis["numeric_stats"][feat] = {
                "train_mean": float(train_df[feat].mean()) if len(train_df) > 0 else None,
                "train_std": float(train_df[feat].std()) if len(train_df) > 0 else None,
                "val_mean": float(val_df[feat].mean()) if len(val_df) > 0 else None,
                "val_std": float(val_df[feat].std()) if len(val_df) > 0 else None,
            }
    
    # Категориальные признаки (% распределение)
    for feat in cat_features:
        if feat in train_df.columns:
            train_dist = train_df[feat].value_counts(normalize=True).head(5).to_dict()
            val_dist = val_df[feat].value_counts(normalize=True).head(5).to_dict()
            analysis["categorical_stats"][feat] = {
                "train_top5": {str(k): float(v) for k, v in train_dist.items()},
                "val_top5": {str(k): float(v) for k, v in val_dist.items()},
                "train_unique": int(train_df[feat].nunique()),
                "val_unique": int(val_df[feat].nunique()),
            }
    
    return analysis


if __name__ == "__main__":
    from ml.data_loader import load_xlsx
    from ml.feature_engineering import build_features
    
    print("Загрузка данных...")
    df = load_xlsx()
    
    # Подготовить target
    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(["Исполнена"]), "target"] = 1
    df.loc[df["Статус заявки"].isin(["Отклонена", "Отозвано"]), "target"] = 0
    resolved = df.dropna(subset=["target"]).copy()
    resolved["target"] = resolved["target"].astype(int)
    
    train_mask = resolved["year"] == 2025
    val_mask = resolved["year"] == 2026
    
    numeric_features = [
        "month", "hour", "day_of_year", "day_of_week",
        "Норматив", "Причитающая сумма"
    ]
    cat_features = ["Область", "Направление водства", "Наименование субсидирования"]
    
    analysis = full_dataset_analysis(
        resolved, train_mask, val_mask, numeric_features, cat_features
    )
    
    import json
    print(json.dumps(analysis, indent=2))
