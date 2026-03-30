"""
shap_service.py — вычисление SHAP values для объяснимости ML скоринга.
Использует TreeExplainer на base_model из CalibratedClassifierCV.
"""

import numpy as np
import pandas as pd
import shap

FEATURE_LABELS = {
    "month": "Месяц подачи",
    "hour": "Час подачи",
    "day_of_year": "День года",
    "day_of_week": "День недели",
    "Норматив": "Норматив субсидии",
    "Причитающая сумма": "Причитающая сумма",
    "amount_to_norm": "Отношение суммы к нормативу",
    "log_amount": "Сумма субсидии (лог)",
    "log_norm": "Норматив (лог)",
    "region_enc": "Регион",
    "direction_enc": "Направление",
    "subsidy_enc": "Тип субсидии",
    "reg_sr": "Успешность в регионе",
    "reg_vol": "Объём заявок в регионе",
    "reg_avg_amt": "Средняя сумма в регионе",
    "dir_sr": "Успешность по направлению",
    "dir_vol": "Объём по направлению",
    "dir_avg_amt": "Средняя сумма по направлению",
    "sub_sr": "Успешность по типу субсидии",
    "sub_vol": "Объём по типу субсидии",
    "sub_avg_amt": "Средняя сумма по типу субсидии",
    "dist_sr": "Успешность в районе",
    "dist_vol": "Объём заявок в районе",
    "dist_avg_amt": "Средняя сумма в районе",
}


def compute_shap(base_model, X, producer_ids, top_n=5):
    """Вычислить SHAP values и вернуть топ-N признаков на каждого производителя.

    Args:
        base_model: GradientBoostingClassifier (не калиброванный).
        X: DataFrame с features.
        producer_ids: Series/list producer_id, соответствующий строкам X.
        top_n: сколько топ-признаков вернуть на производителя.

    Returns:
        list[dict] — [{producer_id, feature, shap_value, feature_value, feature_label}, ...]
    """
    explainer = shap.TreeExplainer(base_model)
    shap_values = explainer.shap_values(X)

    features = list(X.columns)
    results = []

    for i, pid in enumerate(producer_ids):
        vals = shap_values[i]
        top_idx = np.argsort(np.abs(vals))[-top_n:][::-1]

        for idx in top_idx:
            feat = features[idx]
            results.append({
                "producer_id": str(pid),
                "feature": feat,
                "shap_value": round(float(vals[idx]), 4),
                "feature_value": round(float(X.iloc[i, idx]), 4),
                "feature_label": FEATURE_LABELS.get(feat, feat),
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
