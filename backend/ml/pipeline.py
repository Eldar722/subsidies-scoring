"""
pipeline.py — обучение, оценка и сохранение ML модели скоринга субсидий.
Temporal split: train 2025 → val 2026.
"""

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score,
    precision_recall_curve, classification_report,
)

from ml.data_loader import load_xlsx
from ml.feature_engineering import build_features, get_encoders, FEATURES


POSITIVE = ["Исполнена"]
NEGATIVE = ["Отклонена", "Отозвано"]


def _prepare_data(df):
    """Добавить target и разбить на train/val по году."""
    df = df.copy()
    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(POSITIVE), "target"] = 1
    df.loc[df["Статус заявки"].isin(NEGATIVE), "target"] = 0

    resolved = df.dropna(subset=["target"]).copy()
    resolved["target"] = resolved["target"].astype(int)

    train = resolved[resolved["year"] == 2025].copy()
    val = resolved[resolved["year"] == 2026].copy()
    return train, val


def train_model(X_train, y_train):
    """Обучить GradientBoosting + калибровка + 5-fold CV."""
    # 5-Fold Cross-Validation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_aucs = []

    print("\n5-Fold CV на train 2025:")
    for fold, (tr_idx, te_idx) in enumerate(skf.split(X_train, y_train), 1):
        Xtr, Xte = X_train.iloc[tr_idx], X_train.iloc[te_idx]
        ytr, yte = y_train.iloc[tr_idx], y_train.iloc[te_idx]

        m = GradientBoostingClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=4,
            min_samples_leaf=20, subsample=0.8, random_state=42,
        )
        m.fit(Xtr, ytr)
        auc = roc_auc_score(yte, m.predict_proba(Xte)[:, 1])
        cv_aucs.append(auc)
        print(f"  Fold {fold}: AUC={auc:.4f}")

    print(f"  Mean CV AUC: {np.mean(cv_aucs):.4f} +/- {np.std(cv_aucs):.4f}")

    # Финальная модель
    print("\nОбучение финальной модели...")
    base_model = GradientBoostingClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=4,
        min_samples_leaf=20, subsample=0.8, random_state=42,
    )
    base_model.fit(X_train, y_train)

    # Калибровка
    print("Калибровка (isotonic, 3-fold)...")
    model = CalibratedClassifierCV(base_model, method="isotonic", cv=3)
    model.fit(X_train, y_train)

    return model, base_model, cv_aucs


def evaluate(model, X_val, y_val):
    """Оценить модель на hold-out 2026."""
    proba = model.predict_proba(X_val)[:, 1]

    auc = roc_auc_score(y_val, proba)
    ap = average_precision_score(y_val, proba)

    # Оптимальный порог по F1
    precisions, recalls, thresholds = precision_recall_curve(y_val, proba)
    f1_arr = 2 * precisions * recalls / (precisions + recalls + 1e-8)
    best_idx = np.argmax(f1_arr)
    best_thr = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5
    best_f1 = float(f1_arr[best_idx])

    pred = (proba >= best_thr).astype(int)

    print(f"\n{'=' * 50}")
    print(f"  HOLD-OUT 2026")
    print(f"{'=' * 50}")
    print(f"  ROC-AUC          : {auc:.4f}")
    print(f"  Average Precision : {ap:.4f}")
    print(f"  Best threshold    : {best_thr:.3f} -> F1 = {best_f1:.4f}")
    print(f"{'=' * 50}")
    print(classification_report(y_val, pred, target_names=["Отклон./Отозв.", "Исполнена"]))

    return {
        "roc_auc": float(auc),
        "avg_precision": float(ap),
        "best_f1": float(best_f1),
        "optimal_threshold": float(best_thr),
    }


def run_full_pipeline(data_path="data/subsidies.xlsx"):
    """Полный пайплайн: загрузка → features → train → eval → save."""
    print("Загрузка данных...")
    df = load_xlsx(data_path)

    print("Подготовка train/val...")
    train, val = _prepare_data(df)
    print(f"  Train (2025): {len(train)} | pos={train['target'].mean():.1%}")
    print(f"  Val   (2026): {len(val)} | pos={val['target'].mean():.1%}")

    print("\nFeature engineering...")
    X_train = build_features(train, fit=True)
    y_train = train["target"]
    X_val = build_features(val, fit=False)
    y_val = val["target"]

    print(f"  Features: {len(FEATURES)} | Train: {len(X_train)} | Val: {len(X_val)}")

    model, base_model, cv_aucs = train_model(X_train, y_train)
    metrics = evaluate(model, X_val, y_val)
    metrics["cv_auc_mean"] = float(np.mean(cv_aucs))
    metrics["cv_auc_std"] = float(np.std(cv_aucs))
    metrics["train_size"] = len(X_train)
    metrics["val_size"] = len(X_val)

    # Сохранение
    artifact = {
        "model": model,
        "base_model": base_model,
        "features": FEATURES,
        "encoders": get_encoders(),
        "optimal_threshold": metrics["optimal_threshold"],
        "metrics": metrics,
    }
    joblib.dump(artifact, "model.pkl")
    print(f"\nmodel.pkl сохранён")
    print(f"  AUC: {metrics['roc_auc']:.4f} | F1: {metrics['best_f1']:.4f} | Threshold: {metrics['optimal_threshold']:.3f}")

    return metrics


if __name__ == "__main__":
    metrics = run_full_pipeline()
    print(f"\nИтоговые метрики: {metrics}")
