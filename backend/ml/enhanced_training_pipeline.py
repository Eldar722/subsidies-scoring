"""
enhanced_training_pipeline.py — улучшенный pipeline с синтетическими данными + калибровкой.

Pipeline:
1. Загрузить оригинальные train/val data
2. Генерировать синтетические данные
3. Комбинировать train + synthetic
4. Обучить базовую модель (GradientBoosting)
5. Калибровка: двойной метод (Platt + Isotonic)
6. Оценка на val с calibrationная анализом
7. Сохранить модель с метриками
"""

import pandas as pd
import numpy as np
import joblib
import json
from typing import Dict, Tuple
from datetime import datetime

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score,
    precision_recall_curve, classification_report, brier_score_loss,
)

from ml.data_loader import load_xlsx
from ml.feature_engineering import build_features, FEATURES, get_state
from ml.synthetic_data_generator import generate_synthetic_training_data
from ml.dataset_analysis import compute_calibration_analysis
from ml.safe_printing import safe_print, print_section, print_success, print_error, print_warning
from core.config import MODEL_PATH, DATA_PATH


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

POSITIVE = ["Исполнена"]
NEGATIVE = ["Отклонена", "Отозвано"]

NUMERIC_FEATURES = [
    "month", "hour", "day_of_year", "day_of_week",
    "Норматив", "Причитающая сумма"
]

CAT_FEATURES = [
    "Область", "Направление водства", "Наименование субсидирования"
]


# ═══════════════════════════════════════════════════════════════════════════════
# Data Preparation
# ═══════════════════════════════════════════════════════════════════════════════

def prepare_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Подготовить данные: target + temporal split."""
    df = df.copy()
    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(POSITIVE), "target"] = 1
    df.loc[df["Статус заявки"].isin(NEGATIVE), "target"] = 0
    
    resolved = df.dropna(subset=["target"]).copy()
    resolved["target"] = resolved["target"].astype(int)
    
    train = resolved[resolved["year"] == 2025].copy()
    val = resolved[resolved["year"] == 2026].copy()
    
    return train, val


# ═══════════════════════════════════════════════════════════════════════════════
# Synthetic Data Integration
# ═══════════════════════════════════════════════════════════════════════════════

def create_augmented_training_set(train_df: pd.DataFrame, 
                                  synthetic_ratio: float = 0.3,
                                  verbose: bool = True) -> pd.DataFrame:
    """Создать augmented training set: train + synthetic.
    
    Args:
        train_df: оригинальный train (2025)
        synthetic_ratio: доля синтетических данных относительно оригинала
        verbose: выводить progress
    
    Returns:
        Объединённый DataFrame
    """
    print(f"\n📊 Original train: {len(train_df)} | pos_rate={train_df['target'].mean():.1%}")
    
    # Генерировать синтетику
    df_synthetic = generate_synthetic_training_data(
        train_df, NUMERIC_FEATURES, CAT_FEATURES,
        methods=["borderline_smote", "gaussian", "bootstrap"],
        verbose=verbose
    )
    
    if len(df_synthetic) == 0:
        print("[WARN] No synthetic data generated, using original only")
        return train_df
    
    # Объединить
    df_augmented = pd.concat([train_df, df_synthetic], ignore_index=True)
    
    print(f"\n✓ Augmented train: {len(df_augmented)} (original: {len(train_df)}, synthetic: {len(df_synthetic)})")
    print(f"  Synthetic ratio: {len(df_synthetic) / len(train_df):.1%}")
    print(f"  Augmented pos_rate: {df_augmented['target'].mean():.1%}")
    
    return df_augmented


# ═══════════════════════════════════════════════════════════════════════════════
# Model Training with Calibration
# ═══════════════════════════════════════════════════════════════════════════════

def train_base_model(X_train: np.ndarray, y_train: np.ndarray) -> GradientBoostingClassifier:
    """Обучить базовую GradientBoosting модель."""
    model = GradientBoostingClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        min_samples_leaf=20,
        subsample=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model


def cross_validate_model(X_train: np.ndarray, y_train: np.ndarray, 
                        n_splits: int = 5) -> Dict:
    """5-Fold cross-validation на train."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    cv_metrics = {
        "fold_aucs": [],
        "fold_f1s": [],
    }
    
    print("\n5-Fold Cross-Validation:")
    for fold, (tr_idx, te_idx) in enumerate(skf.split(X_train, y_train), 1):
        Xtr, Xte = X_train[tr_idx], X_train[te_idx]
        ytr, yte = y_train[tr_idx], y_train[te_idx]
        
        model = train_base_model(Xtr, ytr)
        
        # Получить вероятности
        y_proba = model.predict_proba(Xte)[:, 1]
        
        # Метрики
        auc = roc_auc_score(yte, y_proba)
        f1 = f1_score(yte, (y_proba >= 0.5).astype(int))
        
        cv_metrics["fold_aucs"].append(auc)
        cv_metrics["fold_f1s"].append(f1)
        
        print(f"  Fold {fold}: AUC={auc:.4f}, F1={f1:.4f}")
    
    cv_metrics["mean_auc"] = float(np.mean(cv_metrics["fold_aucs"]))
    cv_metrics["std_auc"] = float(np.std(cv_metrics["fold_aucs"]))
    cv_metrics["mean_f1"] = float(np.mean(cv_metrics["fold_f1s"]))
    
    print(f"  Mean AUC: {cv_metrics['mean_auc']:.4f} +/- {cv_metrics['std_auc']:.4f}")
    print(f"  Mean F1:  {cv_metrics['mean_f1']:.4f}")
    
    return cv_metrics


def calibrate_model(base_model: GradientBoostingClassifier,
                   X_train: np.ndarray, y_train: np.ndarray,
                   methods: list = None) -> Dict:
    """Калибровать модель несколькими методами и выбрать лучший.
    
    Args:
        base_model: обученная базовая модель
        X_train: train features
        y_train: train target
        methods: список методов ['sigmoid', 'isotonic']
    
    Returns:
        dict с плттом моделей и рекомендацией
    """
    if methods is None:
        methods = ["sigmoid", "isotonic"]
    
    print("\n🔧 Calibration:")
    calibrated_models = {}
    
    for method in methods:
        try:
            cal_model = CalibratedClassifierCV(
                base_model, 
                method=method, 
                cv=3
            )
            cal_model.fit(X_train, y_train)
            calibrated_models[method] = cal_model
            print(f"  ✓ {method} calibration fitted")
        except Exception as e:
            print(f"  [WARN] {method} failed: {e}")
    
    return calibrated_models


def evaluate_calibration(model, X_val: np.ndarray, y_val: np.ndarray,
                        model_name: str = "Model") -> Dict:
    """Оценить калибровку модели."""
    y_proba = model.predict_proba(X_val)[:, 1]
    
    # Основные метрики
    roc_auc = roc_auc_score(y_val, y_proba)
    ap = average_precision_score(y_val, y_proba)
    brier = brier_score_loss(y_val, y_proba)
    
    # Calibration analysis
    cal_analysis = compute_calibration_analysis(y_val, y_proba)
    
    # Optimal threshold по F1
    precisions, recalls, thresholds = precision_recall_curve(y_val, y_proba)
    f1_arr = 2 * precisions * recalls / (precisions + recalls + 1e-8)
    best_idx = np.argmax(f1_arr)
    best_thr = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5
    best_f1 = float(f1_arr[best_idx])
    
    # При оптимальном threshold
    y_pred = (y_proba >= best_thr).astype(int)
    
    metrics = {
        "model_name": model_name,
        "roc_auc": roc_auc,
        "average_precision": ap,
        "brier_score": brier,
        "optimal_threshold": best_thr,
        "f1_at_optimal": best_f1,
        "calibration": cal_analysis,
        "classification_report": classification_report(y_val, y_pred, output_dict=True),
    }
    
    return metrics


# ═══════════════════════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def run_enhanced_pipeline(use_synthetic: bool = True,
                         synthetic_ratio: float = 0.3,
                         calibration_methods: list = None,
                         verbose: bool = True) -> Dict:
    """Запустить full pipeline: данные → синтетика → обучение → калибровка → оценка.
    
    Returns:
        dict с результатами и метриками
    """
    
    if calibration_methods is None:
        calibration_methods = ["sigmoid", "isotonic"]
    
    print_section("ENHANCED ML PIPELINE (v2 with Synthetic Data + Calibration)")
    
    # ════ 1. LOAD DATA ════
    safe_print("\n[1/6] Loading data...")
    df = load_xlsx()
    train_raw, val_raw = prepare_data(df)
    
    safe_print(f"  Train (2025): {len(train_raw)} samples | pos_rate={train_raw['target'].mean():.1%}")
    safe_print(f"  Val   (2026): {len(val_raw)} samples | pos_rate={val_raw['target'].mean():.1%}")
    
    # ════ 2. CREATE AUGMENTED DATASET ════
    if use_synthetic:
        print("\n[2/6] Creating augmented training set...")
        train_data = create_augmented_training_set(train_raw, synthetic_ratio, verbose)
    else:
        print("\n[2/6] Using original training data only...")
        train_data = train_raw.copy()
    
    # ════ 3. BUILD FEATURES ════
    print("\n[3/6] Building features...")
    X_train = build_features(train_data, fit=True)
    X_val = build_features(val_raw, fit=False)
    y_train = train_data["target"].values
    y_val = val_raw["target"].values
    
    print(f"  X_train shape: {X_train.shape}")
    print(f"  X_val shape: {X_val.shape}")
    
    # ════ 4. CROSS-VALIDATION ════
    print("\n[4/6] Cross-validation...")
    cv_results = cross_validate_model(X_train.values, y_train)
    
    # ════ 5. TRAIN & CALIBRATE ════
    print("\n[5/6] Training base model & calibration...")
    base_model = train_base_model(X_train.values, y_train)
    
    # Calibrate
    calibrated_models = calibrate_model(base_model, X_train.values, y_train, 
                                       calibration_methods)
    
    # ════ 6. EVALUATE ════
    print("\n[6/6] Evaluating on hold-out (2026)...")
    
    eval_results = {}
    
    # Base model
    eval_results["base_model"] = evaluate_calibration(base_model, X_val.values, y_val,
                                                      model_name="Base (uncalibrated)")
    
    # Calibrated models
    for method, cal_model in calibrated_models.items():
        eval_results[f"calibrated_{method}"] = evaluate_calibration(
            cal_model, X_val.values, y_val,
            model_name=f"Calibrated ({method})"
        )
    
    # ════ SUMMARY ════
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    
    for model_name, metrics in eval_results.items():
        print(f"\n{model_name.upper()}:")
        print(f"  ROC-AUC:              {metrics['roc_auc']:.4f}")
        print(f"  Average Precision:    {metrics['average_precision']:.4f}")
        print(f"  Brier Score:          {metrics['brier_score']:.4f}")
        print(f"  Optimal Threshold:    {metrics['optimal_threshold']:.3f}")
        print(f"  F1 @ Optimal:         {metrics['f1_at_optimal']:.4f}")
        print(f"  ECE:                  {metrics['calibration']['ece']:.4f}")
    
    # ════ SAVE MODEL ════
    print("\n[SAVE] Saving best model...")
    
    # Выбрать лучшую модель по ROC-AUC
    best_model_key = max(eval_results.keys(), 
                        key=lambda k: eval_results[k]["roc_auc"])
    best_eval = eval_results[best_model_key]
    
    if "calibrated" in best_model_key:
        method = best_model_key.split("_")[1]
        best_model = calibrated_models[method]
    else:
        best_model = base_model
    
    # Сохранить модель
    model_data = {
        "model": best_model,
        "base_model": base_model,
        "features": FEATURES,
        "feature_state": get_state(),
        "metrics": {
            "roc_auc": best_eval["roc_auc"],
            "average_precision": best_eval["average_precision"],
            "brier_score": best_eval["brier_score"],
            "optimal_threshold": best_eval["optimal_threshold"],
            "f1_at_optimal": best_eval["f1_at_optimal"],
            "calibration_ece": best_eval["calibration"]["ece"],
            "cv_results": cv_results,
            "trained_with_synthetic": use_synthetic,
        },
        "evaluation": eval_results,
        "training_timestamp": datetime.now().isoformat(),
    }
    
    joblib.dump(model_data, MODEL_PATH)
    print(f"  ✓ Model saved: {MODEL_PATH}")
    print(f"  ✓ Best model: {best_model_key} (ROC-AUC={best_eval['roc_auc']:.4f})")
    
    return {
        "cv_results": cv_results,
        "eval_results": eval_results,
        "best_model_key": best_model_key,
        "model_data": model_data,
    }


if __name__ == "__main__":
    results = run_enhanced_pipeline(
        use_synthetic=True,
        synthetic_ratio=0.3,
        calibration_methods=["platt", "isotonic"],
        verbose=True
    )
    
    # Сохранить результаты в JSON для reports
    report = {
        "cv_results": results["cv_results"],
        "best_model": results["best_model_key"],
    }
    
    # Упростить eval_results для JSON
    simplified_eval = {}
    for key, metrics in results["eval_results"].items():
        simplified_eval[key] = {
            "roc_auc": metrics["roc_auc"],
            "average_precision": metrics["average_precision"],
            "brier_score": metrics["brier_score"],
            "optimal_threshold": metrics["optimal_threshold"],
            "f1_at_optimal": metrics["f1_at_optimal"],
            "ece": metrics["calibration"]["ece"],
        }
    
    report["evaluation"] = simplified_eval
    
    with open("data_analysis_enhanced.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Report saved: data_analysis_enhanced.json")
