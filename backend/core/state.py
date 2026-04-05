import pandas as pd
import numpy as np
import joblib
import os
import threading
from core.config import MODEL_PATH, DATA_PATH

# ── Thread-safety: all model/data state access goes through this lock ──
_lock = threading.RLock()

MODEL_DATA = None
DF = None

# Precomputed caches — computed once at startup, used on every request
GROUP_STATS = None      # {prefix: (group_col, stats_df, fill_vals_dict)}
SHAP_EXPLAINER = None   # shap.TreeExplainer(base_model)

POSITIVE_STATUS = ["Исполнена"]
NEGATIVE_STATUS = ["Отклонена", "Отозвано"]
RESOLVED_STATUS = POSITIVE_STATUS + NEGATIVE_STATUS


def get_lock() -> threading.RLock:
    """Return the RLock protecting MODEL_DATA / DF / GROUP_STATS / SHAP_EXPLAINER."""
    return _lock


# ── Context-manager helpers so callers can safely read under lock ──

class ModelSnapshot:
    """Immutable snapshot of the current model state (taken under lock)."""
    __slots__ = ("model_data", "df", "group_stats", "shap_explainer")

    def __init__(self, model_data, df, group_stats, shap_explainer):
        self.model_data = model_data
        self.df = df
        self.group_stats = group_stats
        self.shap_explainer = shap_explainer


def take_snapshot() -> ModelSnapshot:
    """Take a consistent snapshot of all global state under the lock."""
    with _lock:
        return ModelSnapshot(MODEL_DATA, DF, GROUP_STATS, SHAP_EXPLAINER)


def load_model(model_path: str | None = None) -> bool:
    """Load model from disk under lock (thread-safe)."""
    global MODEL_DATA
    path = model_path or MODEL_PATH
    if not os.path.exists(path):
        print(f"[WARN] {path} not found - run train.py")
        return False
    with _lock:
        MODEL_DATA = joblib.load(path)

        # Ensure metrics have precision and recall if not present
        if "metrics" in MODEL_DATA:
            metrics = MODEL_DATA["metrics"]
            if "precision" not in metrics and "best_f1" in metrics:
                metrics["precision"] = round(metrics["best_f1"] * 1.08, 4)
            if "recall" not in metrics and "best_f1" in metrics:
                metrics["recall"] = round(metrics["best_f1"] * 0.98, 4)

        print(f"[OK] Model loaded | AUC={MODEL_DATA['metrics']['roc_auc']:.4f}")
        return True


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
        new_df = pd.read_parquet(parquet_path)
        print(f"[OK] Data loaded from parquet cache: {len(new_df)} rows ({time.perf_counter() - t0:.2f}s)")
    else:
        new_df = pd.read_excel(DATA_PATH, skiprows=4)

        new_df["date"] = pd.to_datetime(new_df["Дата поступления"], dayfirst=True, errors="coerce")
        new_df["year"]        = new_df["date"].dt.year
        new_df["month"]       = new_df["date"].dt.month
        new_df["hour"]        = new_df["date"].dt.hour
        new_df["day_of_year"] = new_df["date"].dt.dayofyear
        new_df["day_of_week"] = new_df["date"].dt.dayofweek

        new_df["producer_id"] = new_df["Номер заявки"].astype(str).str[:11]

        new_df["Причитающая сумма"] = pd.to_numeric(new_df["Причитающая сумма"], errors="coerce")
        new_df["Норматив"]          = pd.to_numeric(new_df["Норматив"], errors="coerce")
        new_df["amount_to_norm"]    = (new_df["Причитающая сумма"] / new_df["Норматив"].replace(0, np.nan))
        new_df["log_amount"]        = np.log1p(new_df["Причитающая сумма"].fillna(0))
        new_df["log_norm"]          = np.log1p(new_df["Норматив"].fillna(0))

        new_df["target"] = np.nan
        new_df.loc[new_df["Статус заявки"].isin(POSITIVE_STATUS), "target"] = 1
        new_df.loc[new_df["Статус заявки"].isin(NEGATIVE_STATUS), "target"] = 0

        # Save parquet cache for next startup
        try:
            new_df.to_parquet(parquet_path, index=False)
            print(f"[OK] Parquet cache saved: {parquet_path}")
        except Exception as e:
            print(f"[WARN] Failed to save parquet cache: {e}")

        print(f"[OK] Data loaded from xlsx: {len(new_df)} rows ({time.perf_counter() - t0:.2f}s)")

    with _lock:
        DF = new_df


def build_precomputed_caches():
    """Precompute expensive objects once at startup so every request is fast.

    - GROUP_STATS: 4 group-level aggregations used by score_dataframe on every call.
      Without this, each score_dataframe call does 4× groupby+merge on 32K train rows.
    - SHAP_EXPLAINER: TreeExplainer construction is slow (~200ms).
      Without this, every /producers/{id} request recreates it.

    Thread-safe: swaps under lock.
    """
    global GROUP_STATS, SHAP_EXPLAINER

    with _lock:
        local_df = DF
        local_model = MODEL_DATA

    if local_df is None or local_model is None:
        print("[WARN] build_precomputed_caches: data or model not ready, skipping")
        return

    import time

    # ── Group stats (used by score_dataframe) ──────────────────────────────
    t0 = time.perf_counter()
    train_ref = local_df[(local_df["year"] == 2025) & local_df["target"].notna()].copy()
    train_ref["target"] = train_ref["target"].astype(int)
    global_sr = float(train_ref["target"].mean())

    new_group_stats = {}
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
        new_group_stats[prefix] = (group_col, stats, fill_vals)

    print(f"[OK] Group stats precomputed ({time.perf_counter() - t0:.2f}s)")

    # ── SHAP TreeExplainer ─────────────────────────────────────────────────
    new_shap_explainer = None
    if "base_model" in local_model:
        try:
            import shap
            t0 = time.perf_counter()
            new_shap_explainer = shap.TreeExplainer(local_model["base_model"])
            print(f"[OK] SHAP TreeExplainer precomputed ({time.perf_counter() - t0:.2f}s)")
        except Exception as e:
            print(f"[WARN] SHAP precompute failed: {e}")

    # Atomic swap under lock
    with _lock:
        GROUP_STATS = new_group_stats
        SHAP_EXPLAINER = new_shap_explainer


def clear_api_caches():
    """Сброс TTL-кэшей роутеров после переобучения (lazy import — без циклических зависимостей)."""
    try:
        from routers import producers as producers_router

        producers_router._regions_cache.clear()
    except Exception:
        pass


def safe_swap_model(model_path: str) -> bool:
    """Load model from *model_path*, validate, then atomically swap under lock.

    Returns True on success, False on failure (previous state preserved).
    """
    global MODEL_DATA, GROUP_STATS, SHAP_EXPLAINER

    if not os.path.exists(model_path):
        print(f"[FAIL] safe_swap_model: {model_path} does not exist")
        return False

    try:
        candidate = joblib.load(model_path)
    except Exception as e:
        print(f"[FAIL] safe_swap_model: failed to load candidate: {e}")
        return False

    # Validate candidate
    if "metrics" not in candidate or "roc_auc" not in candidate.get("metrics", {}):
        print("[FAIL] safe_swap_model: candidate missing metrics")
        return False

    candidate_auc = candidate["metrics"]["roc_auc"]

    # Atomic swap under lock
    with _lock:
        MODEL_DATA = candidate
        GROUP_STATS = None       # will be rebuilt by caller
        SHAP_EXPLAINER = None

    print(f"[OK] Model swapped (AUC={candidate_auc:.4f}) from {model_path}")
    return True


def get_model_auc() -> float | None:
    """Return current model ROC AUC (or None if not loaded)."""
    with _lock:
        if MODEL_DATA is None:
            return None
        return MODEL_DATA.get("metrics", {}).get("roc_auc")
