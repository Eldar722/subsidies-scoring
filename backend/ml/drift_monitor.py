"""
drift_monitor.py — мониторинг дрифта данных и confidence scoring.
PSI по признакам + Mahalanobis distance до обучающего множества.
Модель сама говорит когда ей не доверять.
"""

import numpy as np
import pandas as pd
from scipy.spatial.distance import mahalanobis

_state = {
    "train_means": None,
    "train_stds": None,
    "train_cov_inv": None,
    "train_centroid": None,
    "train_histograms": {},
    "fitted": False,
}


def fit_monitor(X_train: pd.DataFrame):
    """Запомнить распределение train для сравнения."""
    _state["train_means"] = X_train.mean().values
    _state["train_stds"] = X_train.std().values + 1e-8
    _state["train_centroid"] = X_train.mean().values

    # Ковариационная матрица для Mahalanobis
    cov = np.cov(X_train.values, rowvar=False)
    cov += np.eye(cov.shape[0]) * 1e-6  # регуляризация
    _state["train_cov_inv"] = np.linalg.inv(cov)

    # Гистограммы для PSI
    for col in X_train.columns:
        vals = X_train[col].dropna().values
        bins = np.histogram_bin_edges(vals, bins=10)
        hist, _ = np.histogram(vals, bins=bins, density=True)
        _state["train_histograms"][col] = {"bins": bins, "hist": hist + 1e-8}

    _state["fitted"] = True


def compute_psi(feature_name: str, new_values: np.ndarray) -> float:
    """Population Stability Index для одного признака."""
    if feature_name not in _state["train_histograms"]:
        return 0.0

    ref = _state["train_histograms"][feature_name]
    new_hist, _ = np.histogram(new_values, bins=ref["bins"], density=True)
    new_hist = new_hist + 1e-8

    p = ref["hist"] / ref["hist"].sum()
    q = new_hist / new_hist.sum()

    psi = np.sum((p - q) * np.log(p / q))
    return float(psi)


def compute_confidence(X_row: np.ndarray) -> dict:
    """Confidence score для одной заявки.

    Returns:
        {confidence, distance, risk_level, reasons}
    """
    if not _state["fitted"]:
        return {"confidence": 0.5, "distance": 0, "risk_level": "unknown", "reasons": []}

    # Mahalanobis distance
    try:
        dist = mahalanobis(X_row, _state["train_centroid"], _state["train_cov_inv"])
    except Exception:
        dist = np.sqrt(np.sum(((X_row - _state["train_centroid"]) / (_state["train_stds"])) ** 2))

    # Нормализуем в [0, 1] через sigmoid
    confidence = float(1.0 / (1.0 + np.exp((dist - 5) / 2)))

    # Найти аномальные признаки (z-score > 2)
    z_scores = np.abs((X_row - _state["train_means"]) / _state["train_stds"])
    reasons = []
    feature_names = list(_state["train_histograms"].keys())
    for i, z in enumerate(z_scores):
        if z > 2 and i < len(feature_names):
            reasons.append({
                "feature": feature_names[i],
                "z_score": round(float(z), 2),
                "description": f"Значение отклоняется от нормы на {z:.1f} стд.",
            })

    reasons = sorted(reasons, key=lambda x: -x["z_score"])[:3]

    if confidence >= 0.7:
        risk_level = "high_confidence"
    elif confidence >= 0.4:
        risk_level = "medium_confidence"
    else:
        risk_level = "low_confidence"

    return {
        "confidence": round(confidence, 4),
        "distance": round(float(dist), 4),
        "risk_level": risk_level,
        "reasons": reasons,
    }


def compute_drift_status(X_new: pd.DataFrame) -> dict:
    """Общий статус дрифта для набора данных."""
    if not _state["fitted"]:
        return {"status": "not_fitted"}

    # PSI по каждому признаку
    psi_scores = {}
    for col in X_new.columns:
        if col in _state["train_histograms"]:
            psi = compute_psi(col, X_new[col].dropna().values)
            psi_scores[col] = round(psi, 4)

    # Средний PSI
    avg_psi = np.mean(list(psi_scores.values())) if psi_scores else 0

    # Confidence по всем строкам
    confidences = []
    for i in range(min(len(X_new), 500)):  # sample
        c = compute_confidence(X_new.iloc[i].values)
        confidences.append(c["confidence"])

    low_confidence_pct = sum(1 for c in confidences if c < 0.4) / len(confidences)

    if avg_psi < 0.1 and low_confidence_pct < 0.1:
        status = "stable"
        message = "Данные стабильны, модель актуальна"
    elif avg_psi < 0.25 or low_confidence_pct < 0.3:
        status = "warning"
        message = "Обнаружен умеренный дрифт, рекомендуется мониторинг"
    else:
        status = "critical"
        message = "Сильный дрифт данных, рекомендуется переобучение"

    # Топ дрифтующих признаков
    top_drift = sorted(psi_scores.items(), key=lambda x: -x[1])[:5]

    return {
        "status": status,
        "message": message,
        "avg_psi": round(avg_psi, 4),
        "low_confidence_pct": round(low_confidence_pct, 4),
        "mean_confidence": round(float(np.mean(confidences)), 4),
        "psi_by_feature": psi_scores,
        "top_drift_features": [
            {"feature": f, "psi": p, "drifted": p > 0.2} for f, p in top_drift
        ],
        "sample_size": len(confidences),
    }
