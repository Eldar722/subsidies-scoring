"""
shap_service.py — вычисление SHAP values для объяснимости ML скоринга.
Использует TreeExplainer на base_model из CalibratedClassifierCV.
"""

import numpy as np
import pandas as pd
import shap

FEATURE_LABELS = {
    "month": "Месяц подачи заявки",
    "hour": "Час подачи заявки",
    "day_of_year": "День года подачи",
    "day_of_week": "День недели подачи",
    "Норматив": "Норматив субсидии",
    "Причитающая сумма": "Сумма субсидии",
    "amount_to_norm": "Сумма относительно норматива",
    "log_amount": "Логарифм суммы субсидии",
    "log_norm": "Логарифм норматива",
    "region_enc": "Код региона",
    "direction_enc": "Код направления",
    "subsidy_enc": "Код типа субсидии",
    "reg_sr": "Успешность в регионе",
    "reg_vol": "Число заявок в регионе",
    "reg_avg_amt": "Средняя сумма в регионе",
    "dir_sr": "Успешность по направлению",
    "dir_vol": "Число заявок по направлению",
    "dir_avg_amt": "Средняя сумма по направлению",
    "sub_sr": "Успешность по типу субсидии",
    "sub_vol": "Число заявок по типу субсидии",
    "sub_avg_amt": "Средняя сумма по типу субсидии",
    "dist_sr": "Успешность в районе",
    "dist_vol": "Число заявок в районе",
    "dist_avg_amt": "Средняя сумма в районе",
    # ═══ v7 features ═══
    "month_amount_inter": "Месяц × Сумма (взаимосвязь)",
    "norm_per_app": "Норматив на заявку",
    "completion_trend": "Отклонение от региональной успешности",
    "app_frequency": "Частота подачи заявок (log)",
    "amount_consistency": "Стабильность сумм заявок",
    "region_bias": "Смещение региона от среднего",
    "rel_amount_in_region": "Сумма относительно региона",
    "rel_amount_in_direction": "Сумма относительно направления",
    # Producer-level features
    "app_count": "Количество заявок производителя",
    "app_completion": "Доля исполненных заявок",
    "avg_amount_producer": "Средняя сумма заявок",
    "amount_cv": "Вариация сумм (CV)",
}


def compute_shap(base_model, X, producer_ids, top_n=5):
    """Вычислить SHAP values и вернуть топ-N признаков на каждого производителя.

    Улучшенная логика выбора топ-факторов:
    - Используем |SHAP value| для ранжирования (сила влияния, не направление)
    - Фильтруем слабые признаки (|SHAP| < 0.001)
    - Минимум top_n признаков, даже если некоторые слабые
    - Уникальные feature_label для каждого производителя
    """
    # Use precomputed explainer if available (avoids ~200ms construction on every request)
    try:
        import core.state as state
        if state.SHAP_EXPLAINER is not None:
            explainer = state.SHAP_EXPLAINER
        else:
            explainer = shap.TreeExplainer(base_model)
    except Exception:
        explainer = shap.TreeExplainer(base_model)
    shap_values = explainer.shap_values(X)

    features = list(X.columns)
    results = []

    # Compute global median |SHAP| to filter weak features
    median_abs_shap = np.median(np.abs(shap_values), axis=0)
    weak_threshold = max(0.001, np.percentile(median_abs_shap, 25))  # bottom 25% are weak

    for i, pid in enumerate(producer_ids):
        vals = shap_values[i]
        abs_vals = np.abs(vals)

        # Sort by absolute SHAP value (strongest first)
        sorted_idx = np.argsort(abs_vals)[::-1]

        # Filter weak features for THIS producer
        strong_idx = [idx for idx in sorted_idx if abs_vals[idx] >= weak_threshold]

        # Take top_n strong features, or fall back to top_n overall if not enough strong
        if len(strong_idx) >= top_n:
            top_idx = strong_idx[:top_n]
        else:
            # Mix: all strong + fill with next strongest
            top_idx = list(strong_idx)
            for idx in sorted_idx:
                if len(top_idx) >= top_n:
                    break
                if idx not in top_idx:
                    top_idx.append(idx)
            top_idx = top_idx[:top_n]

        for idx in top_idx:
            feat = features[idx]
            results.append({
                "producer_id": str(pid),
                "feature": feat,
                "shap_value": round(float(vals[idx]), 4),
                "feature_value": round(float(X.iloc[i, idx]), 4),
                "feature_label": FEATURE_LABELS.get(feat, feat),
                "abs_shap": round(float(abs_vals[idx]), 4),  # For UI sorting
            })

    return results


def format_shap_for_ui(shap_data):
    """Переименовать технические названия в русские (уже делается в compute_shap)."""
    for item in shap_data:
        item["feature_label"] = FEATURE_LABELS.get(item["feature"], item["feature"])
    return shap_data


if __name__ == "__main__":
    import joblib
    from ml.data_loader import load_xlsx
    from ml.feature_engineering import build_features, FEATURES

    # Загрузка модели
    artifact = joblib.load("model.pkl")
    base_model = artifact["base_model"]

    # Загрузка данных
    df = load_xlsx()
    df["target"] = np.nan
    df.loc[df["Статус заявки"] == "Исполнена", "target"] = 1
    df.loc[df["Статус заявки"].isin(["Отклонена", "Отозвано"]), "target"] = 0
    resolved = df.dropna(subset=["target"]).copy()
    resolved["target"] = resolved["target"].astype(int)

    train = resolved[resolved["year"] == 2025].copy().reset_index(drop=True)
    X_train = build_features(train, fit=True)

    # SHAP для первых 100 производителей
    unique_pids = train["producer_id"].unique()[:100]
    mask = train["producer_id"].isin(unique_pids)
    X_subset = X_train[mask].reset_index(drop=True)
    pids_subset = train.loc[mask, "producer_id"].reset_index(drop=True)

    print(f"Вычисляю SHAP для {len(X_subset)} строк ({len(unique_pids)} производителей)...")
    shap_data = compute_shap(base_model, X_subset, pids_subset, top_n=5)

    print(f"\nВсего записей: {len(shap_data)}")
    print(f"\nПример (первый производитель {unique_pids[0]}):")
    for item in shap_data[:5]:
        sign = "+" if item["shap_value"] > 0 else ""
        print(f"  {item['feature_label']:30s} = {item['feature_value']:>10.2f}  SHAP: {sign}{item['shap_value']:.4f}")
