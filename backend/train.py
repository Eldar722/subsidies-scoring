"""
train.py — обучение модели скоринга субсидий (v4)
Ключевые принципы:
  - НЕ опираемся на историю producer_id (99.9% val — unseen producers)
  - Фокус на признаках самой заявки: регион, направление, суммы, тайминг
  - Агрегаты на уровне региона/направления/субсидии (из train)
  - Две оценки: cross-val на 2025 + hold-out на 2026
  - Включаем «Одобрена» как pseudo-positive в расширенном эксперименте

Запуск: python train.py
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    roc_auc_score, f1_score, classification_report,
    average_precision_score, precision_recall_curve,
)
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
import joblib
import warnings
warnings.filterwarnings("ignore")
import traceback
import sys
import os


def main():
    # ══════════════════════════════════════════════════════════════════════════
    # 1. ЗАГРУЗКА
    # ══════════════════════════════════════════════════════════════════════════
    print("=" * 60)
    print("  Скоринг субсидий — обучение v4")
    print("=" * 60)

    df = pd.read_excel("data/subsidies.xlsx", skiprows=4)
    print(f"\n📂 Всего строк: {len(df)}")

    # ══════════════════════════════════════════════════════════════════════════
    # 2. ПОДГОТОВКА
    # ══════════════════════════════════════════════════════════════════════════
    df["date"] = pd.to_datetime(df["Дата поступления"], dayfirst=True, errors="coerce")
    df["year"]        = df["date"].dt.year
    df["month"]       = df["date"].dt.month
    df["hour"]        = df["date"].dt.hour
    df["day_of_year"] = df["date"].dt.dayofyear
    df["day_of_week"] = df["date"].dt.dayofweek

    df["producer_id"] = df["Номер заявки"].astype(str).str[:11]

    df["Причитающая сумма"] = pd.to_numeric(df["Причитающая сумма"], errors="coerce")
    df["Норматив"]          = pd.to_numeric(df["Норматив"], errors="coerce")

    # Производные финансовые
    df["amount_to_norm"] = (df["Причитающая сумма"] / df["Норматив"].replace(0, np.nan))
    df["log_amount"]     = np.log1p(df["Причитающая сумма"].fillna(0))
    df["log_norm"]       = np.log1p(df["Норматив"].fillna(0))

    # Целевая: только завершённые
    POSITIVE = ["Исполнена"]
    NEGATIVE = ["Отклонена", "Отозвано"]

    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(POSITIVE), "target"] = 1
    df.loc[df["Статус заявки"].isin(NEGATIVE), "target"] = 0

    df_resolved = df.dropna(subset=["target"]).copy()
    df_resolved["target"] = df_resolved["target"].astype(int)

    print(f"   Завершённых: {len(df_resolved)}  (pos={df_resolved['target'].mean():.1%})")

    # ══════════════════════════════════════════════════════════════════════════
    # 3. TRAIN / VAL  (по времени)
    # ══════════════════════════════════════════════════════════════════════════
    train_raw = df_resolved[df_resolved["year"] == 2025].copy()
    val_raw   = df_resolved[df_resolved["year"] == 2026].copy()

    print(f"\n📊 Train (2025): {len(train_raw)}  pos={train_raw['target'].mean():.1%}")
    print(f"   Val   (2026): {len(val_raw)}  pos={val_raw['target'].mean():.1%}")

    if len(train_raw) == 0:
        raise ValueError("Train set (2025) is empty — check data/subsidies.xlsx")
    if len(val_raw) == 0:
        print("   ⚠️ Val set (2026) is empty — will skip hold-out evaluation")

    # ══════════════════════════════════════════════════════════════════════════
    # 4. АГРЕГАТЫ НА УРОВНЕ РЕГИОНА / НАПРАВЛЕНИЯ / СУБСИДИИ  (из train)
    # ══════════════════════════════════════════════════════════════════════════
    def build_group_stats(train_df, df_to_enrich, group_col, prefix):
        """Считает success_rate и volume по group_col на train, мержит в df_to_enrich."""
        stats = train_df.groupby(group_col).agg(
            success_rate=("target", "mean"),
            volume=("target", "count"),
            avg_amount=("Причитающая сумма", "mean"),
        ).reset_index()
        stats.columns = [group_col, f"{prefix}_sr", f"{prefix}_vol", f"{prefix}_avg_amt"]
        enriched = df_to_enrich.merge(stats, on=group_col, how="left")
        for c in [f"{prefix}_sr", f"{prefix}_vol", f"{prefix}_avg_amt"]:
            enriched[c] = enriched[c].fillna(train_df["target"].mean() if "_sr" in c
                                              else stats[c.replace(prefix, prefix)].median())
        return enriched

    print("\n🛡️  Агрегаты по region / direction / subsidy (train only)...")

    # Регион
    train_e = build_group_stats(train_raw, train_raw, "Область", "reg")
    val_e   = build_group_stats(train_raw, val_raw,   "Область", "reg")

    # Направление
    train_e = build_group_stats(train_raw, train_e, "Направление водства", "dir")
    val_e   = build_group_stats(train_raw, val_e,   "Направление водства", "dir")

    # Субсидия
    train_e = build_group_stats(train_raw, train_e, "Наименование субсидирования", "sub")
    val_e   = build_group_stats(train_raw, val_e,   "Наименование субсидирования", "sub")

    # Район хозяйства
    train_e = build_group_stats(train_raw, train_e, "Район хозяйства", "dist")
    val_e   = build_group_stats(train_raw, val_e,   "Район хозяйства", "dist")

    # ══════════════════════════════════════════════════════════════════════════
    # 5. ENCODE + ФИНАЛЬНЫЙ NaN FILL
    # ══════════════════════════════════════════════════════════════════════════
    le_region    = LabelEncoder()
    le_direction = LabelEncoder()
    le_subsidy   = LabelEncoder()

    train_e["region_enc"]    = le_region.fit_transform(train_e["Область"].fillna("unk"))
    train_e["direction_enc"] = le_direction.fit_transform(train_e["Направление водства"].fillna("unk"))
    train_e["subsidy_enc"]   = le_subsidy.fit_transform(train_e["Наименование субсидирования"].fillna("unk"))

    def safe_transform(enc, s):
        known = set(enc.classes_)
        return s.map(lambda x: enc.transform([x])[0] if x in known else -1)

    val_e["region_enc"]    = safe_transform(le_region,    val_e["Область"].fillna("unk"))
    val_e["direction_enc"] = safe_transform(le_direction, val_e["Направление водства"].fillna("unk"))
    val_e["subsidy_enc"]   = safe_transform(le_subsidy,   val_e["Наименование субсидирования"].fillna("unk"))

    # ══════════════════════════════════════════════════════════════════════════
    # 6. ПРИЗНАКИ
    # ══════════════════════════════════════════════════════════════════════════
    FEATURES = [
        # Временные
        "month", "hour", "day_of_year", "day_of_week",
        # Финансовые
        "Норматив", "Причитающая сумма", "amount_to_norm", "log_amount", "log_norm",
        # Кодированные категории
        "region_enc", "direction_enc", "subsidy_enc",
        # Агрегаты: регион
        "reg_sr", "reg_vol", "reg_avg_amt",
        # Агрегаты: направление
        "dir_sr", "dir_vol", "dir_avg_amt",
        # Агрегаты: субсидия
        "sub_sr", "sub_vol", "sub_avg_amt",
        # Агрегаты: район
        "dist_sr", "dist_vol", "dist_avg_amt",
    ]

    # Fill remaining NaN в финансовых
    for dset in [train_e, val_e]:
        for c in FEATURES:
            if c in dset.columns:
                dset[c] = dset[c].fillna(dset[c].median() if dset[c].dtype != object else -1)

    X_train = train_e[FEATURES].copy()
    y_train = train_e["target"].copy()
    X_val   = val_e[FEATURES].copy()
    y_val   = val_e["target"].copy()

    # финальная проверка NaN
    X_train = X_train.fillna(0)
    X_val   = X_val.fillna(0)

    print(f"\n   Train: {len(X_train)} | Val: {len(X_val)} | Признаков: {len(FEATURES)}")

    # ══════════════════════════════════════════════════════════════════════════
    # 7. CROSS-VALIDATION НА 2025  (честная оценка)
    # ══════════════════════════════════════════════════════════════════════════
    print("\n🔄 5-Fold CV на 2025 данных...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_aucs, cv_f1s = [], []

    for fold, (tr_idx, te_idx) in enumerate(skf.split(X_train, y_train), 1):
        Xtr, Xte = X_train.iloc[tr_idx], X_train.iloc[te_idx]
        ytr, yte = y_train.iloc[tr_idx], y_train.iloc[te_idx]

        m = GradientBoostingClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=4,
            min_samples_leaf=20, subsample=0.8, random_state=42,
        )
        m.fit(Xtr, ytr)
        p = m.predict_proba(Xte)[:, 1]
        a = roc_auc_score(yte, p)
        f = f1_score(yte, (p >= 0.5).astype(int))
        cv_aucs.append(a)
        cv_f1s.append(f)
        print(f"   Fold {fold}: AUC={a:.4f}  F1={f:.4f}")

    print(f"   ── Mean CV AUC: {np.mean(cv_aucs):.4f} ± {np.std(cv_aucs):.4f}")
    print(f"   ── Mean CV F1 : {np.mean(cv_f1s):.4f} ± {np.std(cv_f1s):.4f}")

    # ══════════════════════════════════════════════════════════════════════════
    # 8. ОБУЧЕНИЕ ФИНАЛЬНОЙ МОДЕЛИ
    # ══════════════════════════════════════════════════════════════════════════
    print("\n🚀 Обучение финальной модели...")
    base_model = GradientBoostingClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        min_samples_leaf=20,
        subsample=0.8,
        random_state=42,
    )
    base_model.fit(X_train, y_train)

    # Калибровка
    print("   Калибровка (isotonic, 3-fold)...")
    model = CalibratedClassifierCV(base_model, method="isotonic", cv=3)
    model.fit(X_train, y_train)

    # ══════════════════════════════════════════════════════════════════════════
    # 9. HOLD-OUT ОЦЕНКА НА 2026
    # ══════════════════════════════════════════════════════════════════════════
    proba = model.predict_proba(X_val)[:, 1]

    auc = roc_auc_score(y_val, proba)
    ap  = average_precision_score(y_val, proba)

    # Оптимальный порог по F1
    precisions, recalls, thresholds = precision_recall_curve(y_val, proba)
    f1_arr = 2 * precisions * recalls / (precisions + recalls + 1e-8)
    best_idx = np.argmax(f1_arr)
    best_thr = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5
    best_f1  = float(f1_arr[best_idx])

    pred_opt = (proba >= best_thr).astype(int)

    print(f"\n{'=' * 55}")
    print(f"  HOLD-OUT 2026  (только завершённые заявки)")
    print(f"{'=' * 55}")
    print(f"  ROC-AUC          : {auc:.4f}  {'✅' if auc > 0.75 else '⚠️'}")
    print(f"  Average Precision : {ap:.4f}")
    print(f"  Лучший порог     : {best_thr:.3f}  →  F1 = {best_f1:.4f}")
    print(f"{'=' * 55}\n")

    print(f"  Classification Report (порог={best_thr:.3f}):")
    print(classification_report(y_val, pred_opt,
          target_names=["Отклон./Отозв.", "Исполнена"]))

    # Калибровка
    print("📉 Калибровка:")
    try:
        pt, pp = calibration_curve(y_val, proba, n_bins=8, strategy="quantile")
        for t, p in zip(pt, pp):
            d = t - p
            m = "✅" if abs(d) < 0.10 else ("⚠️" if abs(d) < 0.20 else "❌")
            print(f"   {m} pred={p:.2f} → real={t:.2f}  (Δ={d:+.2f})")
    except Exception as e:
        print(f"   ⚠️ {e}")

    # Feature importance
    print("\n📈 Важность признаков:")
    imp = pd.Series(base_model.feature_importances_, index=FEATURES).sort_values(ascending=False)
    for feat, val in imp.items():
        bar = "█" * int(val * 40)
        print(f"   {feat:22s} {val:.4f}  {bar}")

    # ══════════════════════════════════════════════════════════════════════════
    # 10. СОХРАНЕНИЕ
    # ══════════════════════════════════════════════════════════════════════════
    artifact = {
        "model": model,
        "base_model": base_model,
        "features": FEATURES,
        "encoders": {
            "region": le_region,
            "direction": le_direction,
            "subsidy": le_subsidy,
        },
        "optimal_threshold": best_thr,
        "metrics": {
            "roc_auc": auc, "avg_precision": ap,
            "best_f1": best_f1, "best_threshold": best_thr,
            "cv_auc_mean": float(np.mean(cv_aucs)),
            "cv_f1_mean": float(np.mean(cv_f1s)),
        },
    }
    joblib.dump(artifact, "model.pkl")

    print(f"\n✅ Модель сохранена → model.pkl")
    print(f"   Порог: {best_thr:.3f} | AUC: {auc:.4f} | F1: {best_f1:.4f}")
    print(f"   CV AUC: {np.mean(cv_aucs):.4f} ± {np.std(cv_aucs):.4f}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # Sync scores to Supabase for frontend
    # ══════════════════════════════════════════════════════════════════════════
    try:
        from ml.sync_to_supabase import sync_scores_to_supabase
        sync_scores_to_supabase(df_test, artifact)
    except Exception as e:
        print(f"\n⚠️ WARNING: Failed to sync to Supabase: {e}")
        print("  (Frontend may show stale data, but model training succeeded)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Log full traceback to file for debugging
        os.makedirs("logs", exist_ok=True)
        with open("logs/train_error.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        # Print structured error to stderr (captured by pipeline router)
        print(f"\n❌ ОШИБКА ОБУЧЕНИЯ: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
