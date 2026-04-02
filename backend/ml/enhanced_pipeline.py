"""
enhanced_pipeline.py — улучшенный пайплайн обучения с синтетическими данными и улучшенной калибровкой.
"""

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score,
    precision_recall_curve, classification_report, brier_score_loss
)
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from ml.data_loader import load_xlsx
from ml.feature_engineering import build_features, get_encoders, FEATURES
from ml.synthetic_data import create_synthetic_data, save_synthetic_to_supabase

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


def train_model_with_synthetic(X_train, y_train, use_synthetic=True, synthetic_method='combined'):
    """
    Обучить модель с опциональным использованием синтетических данных и улучшенной калибровкой.
    
    Args:
        X_train: обучающие признаки
        y_train: обучающие метки
        use_synthetic: использовать ли синтетические данные
        synthetic_method: метод генерации синтетических данных
    
    Returns:
        model: калиброванная модель
        base_model: базовая модель
        cv_aucs: результаты кросс-валидации
        X_train_used: использованные обучающие данные (оригинал + синтетика)
        y_train_used: использованные метки
    """
    # Анализ исходного дисбаланса
    print(f"\nИсходное распределение классов:")
    unique, counts = np.unique(y_train, return_counts=True)
    for cls, count in zip(unique, counts):
        print(f"  Класс {cls}: {count} ({count/len(y_train)*100:.1f}%)")
    
    X_train_used = X_train.copy()
    y_train_used = y_train.copy()
    
    # Генерация синтетических данных если требуется
    if use_synthetic:
        print(f"\nГенерация синтетических данных методом: {synthetic_method}")
        X_synthetic, y_synthetic = create_synthetic_data(
            X_train.values, y_train.values,
            method=synthetic_method,
            sampling_strategy=0.5,  # Увеличиваем minority класс до 50% от majority
            random_state=42
        )
        
        # Объединяем оригинальные и синтетические данные
        X_train_used = np.vstack([X_train, X_synthetic])
        y_train_used = np.hstack([y_train, y_synthetic])
        
        print(f"\nПосле добавления синтетических данных:")
        unique, counts = np.unique(y_train_used, return_counts=True)
        for cls, count in zip(unique, counts):
            print(f"  Класс {cls}: {count} ({count/len(y_train_used)*100:.1f}%)")
    
    # 5-Fold Cross-Validation
    print(f"\n5-Fold CV на обработанных данных...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_aucs = []

    for fold, (tr_idx, te_idx) in enumerate(skf.split(X_train_used, y_train_used), 1):
        Xtr, Xte = X_train_used[tr_idx], X_train_used[te_idx]
        ytr, yte = y_train_used[tr_idx], y_train_used[te_idx]

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
    base_model.fit(X_train_used, y_train_used)

    # Улучшенная калибровка: пробуем оба метода и выбираем лучший
    print("\nСравнение методов калибровки...")
    
    # Метод 1: Isotonic regression
    model_isotonic = CalibratedClassifierCV(base_model, method="isotonic", cv=3)
    model_isotonic.fit(X_train_used, y_train_used)
    
    # Метод 2: Platt scaling (sigmoid)
    model_sigmoid = CalibratedClassifierCV(base_model, method="sigmoid", cv=3)
    model_sigmoid.fit(X_train_used, y_train_used)
    
    # Выбираем лучший метод на основе Brier score (меньше - лучше)
    # Используем оставшиеся данные для валидации калибровки
    from sklearn.model_selection import train_test_split
    X_cal_train, X_cal_val, y_cal_train, y_cal_val = train_test_split(
        X_train_used, y_train_used, test_size=0.3, random_state=42, stratify=y_train_used
    )
    
    # Переобучаем на калибровочной выборке
    base_model_cal = GradientBoostingClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=4,
        min_samples_leaf=20, subsample=0.8, random_state=42,
    )
    base_model_cal.fit(X_cal_train, y_cal_train)
    
    model_iso_cal = CalibratedClassifierCV(base_model_cal, method="isotonic", cv=2)
    model_sig_cal = CalibratedClassifierCV(base_model_cal, method="sigmoid", cv=2)
    
    model_iso_cal.fit(X_cal_train, y_cal_train)
    model_sig_cal.fit(X_cal_train, y_cal_train)
    
    # Оценка калибровки
    prob_iso = model_iso_cal.predict_proba(X_cal_val)[:, 1]
    prob_sig = model_sig_cal.predict_proba(X_cal_val)[:, 1]
    
    brier_iso = brier_score_loss(y_cal_val, prob_iso)
    brier_sig = brier_score_loss(y_cal_val, prob_sig)
    
    print(f"  Brier score (isotonic): {brier_iso:.4f}")
    print(f"  Brier score (sigmoid):  {brier_sig:.4f}")
    
    if brier_iso <= brier_sig:
        print("  Выбран метод: Isotonic regression")
        model = model_isotonic
    else:
        print("  Выбран метод: Platt scaling (sigmoid)")
        model = model_sigmoid
    
    # Переобучаем выбранную модель на всех данных
    model.fit(X_train_used, y_train_used)

    return model, base_model, cv_aucs, X_train_used, y_train_used


def evaluate_model(model, X_val, y_val, model_name="Model"):
    """Оценить модель на hold-out с расширенными метриками."""
    proba = model.predict_proba(X_val)[:, 1]

    auc = roc_auc_score(y_val, proba)
    ap = average_precision_score(y_val, proba)
    
    # Brier score для оценки калибровки
    brier = brier_score_loss(y_val, proba)
    
    # Оптимальный порог по F1
    precisions, recalls, thresholds = precision_recall_curve(y_val, proba)
    f1_arr = 2 * precisions * recalls / (precisions + recalls + 1e-8)
    best_idx = np.argmax(f1_arr)
    best_thr = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5
    best_f1 = float(f1_arr[best_idx])

    pred = (proba >= best_thr).astype(int)

    print(f"\n{'=' * 60}")
    print(f"  {model_name.upper()} - HOLD-OUT 2026")
    print(f"{'=' * 60}")
    print(f"  ROC-AUC          : {auc:.4f}")
    print(f"  Average Precision: {ap:.4f}")
    print(f"  Brier Score      : {brier:.4f} (меньше - лучше калибровка)")
    print(f"  Best threshold   : {best_thr:.3f} -> F1 = {best_f1:.4f}")
    print(f"{'=' * 60}")
    print(classification_report(y_val, pred, target_names=["Отклон./Отозв.", "Исполнена"]))

    return {
        "roc_auc": float(auc),
        "avg_precision": float(ap),
        "brier_score": float(brier),
        "best_f1": float(best_f1),
        "optimal_threshold": float(best_thr),
        "predictions_proba": proba
    }


def run_enhanced_pipeline(data_path="data/subsidies.xlsx", use_synthetic=True, synthetic_method='combined'):
    """
    Улучшенный полный пайплайн: загрузка → features → синтетика → train → calibrate → eval → save.
    """
    print("ЗАПУСК УЛУЧШЕННОГО ПАЙПЛАЙНА ОБУЧЕНИЯ")
    print("=" * 60)
    
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

    # Обучение с синтетическими данными и улучшенной калибровкой
    model, base_model, cv_aucs, X_train_used, y_train_used = train_model_with_synthetic(
        X_train, y_train, 
        use_synthetic=use_synthetic, 
        synthetic_method=synthetic_method
    )
    
    # Оценка модели
    metrics = evaluate_model(model, X_val, y_val, "Улучшенная модель")
    metrics["cv_auc_mean"] = float(np.mean(cv_aucs))
    metrics["cv_auc_std"] = float(np.std(cv_aucs))
    metrics["train_size_original"] = len(X_train)
    metrics["train_size_used"] = len(X_train_used)
    metrics["val_size"] = len(X_val)
    metrics["synthetic_used"] = use_synthetic
    metrics["synthetic_method"] = synthetic_method if use_synthetic else None

    # Сохранение улучшенной модели
    artifact = {
        "model": model,
        "base_model": base_model,
        "features": FEATURES,
        "encoders": get_encoders(),
        "optimal_threshold": metrics["optimal_threshold"],
        "metrics": metrics,
        "synthetic_info": {
            "used": use_synthetic,
            "method": synthetic_method if use_synthetic else None,
            "original_size": len(X_train),
            "synthetic_size": len(X_train_used) - len(X_train) if use_synthetic else 0
        }
    }
    
    model_filename = f"model_enhanced_{synthetic_method if use_synthetic else 'baseline'}.pkl"
    joblib.dump(artifact, model_filename)
    print(f"\n{model_filename} сохранён")
    print(f"  AUC: {metrics['roc_auc']:.4f} | F1: {metrics['best_f1']:.4f} | Brier: {metrics['brier_score']:.4f}")
    
    # Также сохраняем как основную модель для обратной совместимости
    joblib.dump(artifact, "model.pkl")
    print(f"model.pkl обновлен (обратная совместимость)")
    
    return metrics


def compare_models(baseline_metrics, enhanced_metrics):
    """Сравнение метрик baseline и enhanced моделей."""
    print(f"\n{'=' * 80}")
    print("СРАВНЕНИЕ МОДЕЛЕЙ: BASELINE vs ENHANCED")
    print(f"{'=' * 80}")
    print(f"{'Метрика':<25} {'Baseline':<15} {'Enhanced':<15} {'Изменение':<15}")
    print(f"{'-' * 80}")
    
    metrics_to_compare = [
        ('ROC-AUC', 'roc_auc', '.4f'),
        ('Average Precision', 'avg_precision', '.4f'),
        ('Brier Score', 'brier_score', '.4f'),
        ('Best F1', 'best_f1', '.4f'),
        ('CV AUC Mean', 'cv_auc_mean', '.4f'),
        ('Train Size', 'train_size_original', 'd')
    ]
    
    for name, key, fmt in metrics_to_compare:
        base_val = baseline_metrics.get(key, 0)
        enh_val = enhanced_metrics.get(key, 0)
        
        if fmt == '.4f':
            change = f"{enh_val - base_val:+.4f}"
        else:
            change = f"{enh_val - base_val:+d}"
            
        print(f"{name:<25} {base_val:<15.{fmt.split('.')[1] if '.' in fmt else '0'}} {enh_val:<15.{fmt.split('.')[1] if '.' in fmt else '0'}} {change:<15}")
    
    print(f"{'=' * 80}")
    
    # Оценка улучшений
    auc_improvement = enhanced_metrics['roc_auc'] - baseline_metrics['roc_auc']
    brier_improvement = baseline_metrics['brier_score'] - enhanced_metrics['brier_score']  # меньше - лучше
    
    print(f"Улучшение ROC-AUC: {auc_improvement:+.4f}")
    print(f"Улучшение калибровки (Brier): {brier_improvement:+.4f}")
    
    if auc_improvement > 0.01 and brier_improvement > 0.005:
        print("✅ Значительное улучшение достигнуто!")
    elif auc_improvement > 0 or brier_improvement > 0:
        print("✅ Небольшое улучшение достигнуто")
    else:
        print("⚠️  Улучшений не наблюдается, требуется дальнейшая настройка")


if __name__ == "__main__":
    # Сначала запускаем baseline для сравнения
    print("Запуск baseline пайплайна для сравнения...")
    from ml.pipeline import run_full_pipeline as baseline_pipeline
    baseline_metrics = baseline_pipeline()
    
    # Добавляем Brier score к baseline метрикам для справедливого сравнения
    import numpy as np
    import joblib
    artifact = joblib.load("model.pkl")
    model = artifact["model"]
    
    # Перезагружаем данные для оценки baseline
    from ml.data_loader import load_xlsx
    from ml.feature_engineering import build_features
    df = load_xlsx("data/subsidies.xlsx")
    
    POSITIVE = ["Исполнена"]
    NEGATIVE = ["Отклонена", "Отозвано"]
    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(POSITIVE), "target"] = 1
    df.loc[df["Статус заявки"].isin(NEGATIVE), "target"] = 0
    
    resolved = df.dropna(subset=["target"]).copy()
    resolved["target"] = resolved["target"].astype(int)
    val = resolved[resolved["year"] == 2026].copy()
    X_val = build_features(val, fit=False)
    y_val = val["target"]
    
    # Оценка baseline модели
    baseline_eval = evaluate_model(model, X_val, y_val, "Baseline")
    baseline_metrics.update({
        "brier_score": baseline_eval["brier_score"],
        "best_f1": baseline_eval["best_f1"],
        "optimal_threshold": baseline_eval["optimal_threshold"]
    })
    
    print(f"\nBaseline метрики обновлены с Brier score: {baseline_metrics['brier_score']:.4f}")
    
    # Теперь запускаем улучшенный пайплайн
    print(f"\n{'#' * 80}")
    print("ЗАПУСК УЛУЧШЕННОГО ПАЙПЛАЙНА С СИНТЕТИЧЕСКИМИ ДАННЫМИ")
    print(f"{'#' * 80}")
    
    enhanced_metrics = run_enhanced_pipeline(
        data_path="data/subsidies.xlsx",
        use_synthetic=True,
        synthetic_method='combined'  # Комбинируем SMOTE + Gaussian noise
    )
    
    # Сравниваем результаты
    compare_models(baseline_metrics, enhanced_metrics)
    
    print(f"\nИтоговые улучшенные метрики: {enhanced_metrics}")