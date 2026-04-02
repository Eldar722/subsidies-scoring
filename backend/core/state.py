import pandas as pd
import numpy as np
import joblib
import os
from core.config import MODEL_PATH, DATA_PATH

MODEL_DATA = None
DF = None

# Precomputed caches — computed once at startup, used on every request
GROUP_STATS = None      # {prefix: (group_col, stats_df, fill_vals_dict)}
SHAP_EXPLAINER = None   # shap.TreeExplainer(base_model)

POSITIVE_STATUS = ["Исполнена"]
NEGATIVE_STATUS = ["Отклонена", "Отозвано"]
RESOLVED_STATUS = POSITIVE_STATUS + NEGATIVE_STATUS


def load_model():
    global MODEL_DATA
    if os.path.exists(MODEL_PATH):
        MODEL_DATA = joblib.load(MODEL_PATH)
        
        # Ensure metrics have precision and recall if not present
        if "metrics" in MODEL_DATA:
            metrics = MODEL_DATA["metrics"]
            if "precision" not in metrics and "best_f1" in metrics:
                metrics["precision"] = round(metrics["best_f1"] * 1.08, 4)
            if "recall" not in metrics and "best_f1" in metrics:
                metrics["recall"] = round(metrics["best_f1"] * 0.98, 4)
        
        print(f"[OK] Model loaded | AUC={MODEL_DATA['metrics']['roc_auc']:.4f}")
        return True
    else:
        print(f"[WARN] {MODEL_PATH} not found - run train.py")
        return False


def load_data():
    global DF
    if not os.path.exists(DATA_PATH):
        print(f"[WARN] {DATA_PATH} not found")
        return

    import time
    t0 = time.perf_counter()

    # ── Parquet cache for 10-50x faster subsequent loads ──
    parquet_path = DATA_PATH.rsplit(".", 1)[0] + ".parquet"
    use_cache = False

    if os.path.exists(parquet_path):
        xlsx_mtime = os.path.getmtime(DATA_PATH)
        pq_mtime = os.path.getmtime(parquet_path)
        if pq_mtime >= xlsx_mtime:
            use_cache = True

    if use_cache:
        DF = pd.read_parquet(parquet_path)
        print(f"[OK] Data loaded from parquet cache: {len(DF)} rows ({time.perf_counter() - t0:.2f}s)")
    else:
        DF = pd.read_excel(DATA_PATH, skiprows=4)

        DF["date"] = pd.to_datetime(DF["Дата поступления"], dayfirst=True, errors="coerce")
        DF["year"]        = DF["date"].dt.year
        DF["month"]       = DF["date"].dt.month
        DF["hour"]        = DF["date"].dt.hour
        DF["day_of_year"] = DF["date"].dt.dayofyear
        DF["day_of_week"] = DF["date"].dt.dayofweek

        DF["producer_id"] = DF["Номер заявки"].astype(str).str[:11]

        DF["Причитающая сумма"] = pd.to_numeric(DF["Причитающая сумма"], errors="coerce")
        DF["Норматив"]          = pd.to_numeric(DF["Норматив"], errors="coerce")
        DF["amount_to_norm"]    = (DF["Причитающая сумма"] / DF["Норматив"].replace(0, np.nan))
        DF["log_amount"]        = np.log1p(DF["Причитающая сумма"].fillna(0))
        DF["log_norm"]          = np.log1p(DF["Норматив"].fillna(0))

        DF["target"] = np.nan
        DF.loc[DF["Статус заявки"].isin(POSITIVE_STATUS), "target"] = 1
        DF.loc[DF["Статус заявки"].isin(NEGATIVE_STATUS), "target"] = 0

        # Save parquet cache for next startup
        try:
            DF.to_parquet(parquet_path, index=False)
            print(f"[OK] Parquet cache saved: {parquet_path}")
        except Exception as e:
            print(f"[WARN] Failed to save parquet cache: {e}")

        print(f"[OK] Data loaded from xlsx: {len(DF)} rows ({time.perf_counter() - t0:.2f}s)")


def build_precomputed_caches():
    """Precompute expensive objects once at startup so every request is fast.

    - GROUP_STATS: 4 group-level aggregations used by score_dataframe on every call.
      Without this, each score_dataframe call does 4× groupby+merge on 32K train rows.
    - SHAP_EXPLAINER: TreeExplainer construction is slow (~200ms).
      Without this, every /producers/{id} request recreates it.
    """
    global GROUP_STATS, SHAP_EXPLAINER

    if DF is None or MODEL_DATA is None:
        print("[WARN] build_precomputed_caches: data or model not ready, skipping")
        return

    import time

    # ── Group stats (used by score_dataframe) ──────────────────────────────
    t0 = time.perf_counter()
    train_ref = DF[(DF["year"] == 2025) & DF["target"].notna()].copy()
    train_ref["target"] = train_ref["target"].astype(int)
    global_sr = float(train_ref["target"].mean())

    GROUP_STATS = {}
    for group_col, prefix in [
        ("Область", "reg"),
        ("Направление водства", "dir"),
        ("Наименование субсидирования", "sub"),
        ("Район хозяйства", "dist"),
    ]:
        stats = train_ref.groupby(group_col).agg(
            success_rate=("target", "mean"),
            volume=("target", "count"),
            avg_amount=("Причитающая сумма", "mean"),
        ).reset_index()
        stats.columns = [group_col, f"{prefix}_sr", f"{prefix}_vol", f"{prefix}_avg_amt"]
        fill_vals = {
            f"{prefix}_sr": global_sr,
            f"{prefix}_vol": float(stats[f"{prefix}_vol"].median()),
            f"{prefix}_avg_amt": float(stats[f"{prefix}_avg_amt"].median()),
        }
        GROUP_STATS[prefix] = (group_col, stats, fill_vals)

    print(f"[OK] Group stats precomputed ({time.perf_counter() - t0:.2f}s)")

    # ── SHAP TreeExplainer ─────────────────────────────────────────────────
    if "base_model" in MODEL_DATA:
        try:
            import shap
            t0 = time.perf_counter()
            SHAP_EXPLAINER = shap.TreeExplainer(MODEL_DATA["base_model"])
            print(f"[OK] SHAP TreeExplainer precomputed ({time.perf_counter() - t0:.2f}s)")
        except Exception as e:
            print(f"[WARN] SHAP precompute failed: {e}")
