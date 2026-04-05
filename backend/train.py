"""
train.py — обучение модели скоринга субсидий (v6 — production-stable)

Ключевые принципы:
  - Фиксированный seed (42) для полной воспроизводимости
  - Temporal split: train 2025 → hold-out 2026
  - Distribution shift monitoring (2025 vs 2026)
  - Class imbalance tracking (pos_rate drift)
  - Quality gate: ROC AUC >= 0.72 (модель НЕ сохраняется при нарушении)
  - Dataset hash + feature version + model config для трассируемости
  - Stable preprocessing (детерминированные fillna, без случайных заполнений)

Запуск: cd backend && python train.py
"""

import sys
import os
import json
import hashlib
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════════════
# ENCODING FIX (Windows)
# ══════════════════════════════════════════════════════════════
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold, GroupKFold
from sklearn.metrics import (
    roc_auc_score, f1_score, classification_report,
    average_precision_score, precision_recall_curve,
    precision_score, recall_score, confusion_matrix,
)
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from xgboost import XGBClassifier
import xgboost as xgb
import sklearn
import joblib
import warnings
import traceback

# Selective warning suppression — only silence known-non-critical noise
warnings.filterwarnings("ignore", category=UserWarning, module="xgboost")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*is_categorical_dtype.*")
warnings.filterwarnings("ignore", message=".*Setting an item of incompatible dtype.*")

# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════
SEED = 42
MIN_AUC = 0.72  # Quality gate — model NOT saved below this

POSITIVE = ["Исполнена"]
NEGATIVE = ["Отклонена", "Отозвано"]

FEATURES = [
    # Временные (4)
    "month", "hour", "day_of_year", "day_of_week",
    # Финансовые (5)
    "Норматив", "Причитающая сумма", "amount_to_norm", "log_amount", "log_norm",
    # Кодированные категории (3)
    "region_enc", "direction_enc", "subsidy_enc",
    # Агрегаты: регион (3)
    "reg_sr", "reg_vol", "reg_avg_amt",
    # Агрегаты: направление (3)
    "dir_sr", "dir_vol", "dir_avg_amt",
    # Агрегаты: субсидия (3)
    "sub_sr", "sub_vol", "sub_avg_amt",
    # Агрегаты: район (3)
    "dist_sr", "dist_vol", "dist_avg_amt",
    # ═══ v7 — interaction & trend features ═══
    # Financial × temporal interactions (3)
    "month_amount_inter", "norm_per_app", "completion_trend",
    # Behavioral patterns (3)
    "app_frequency", "amount_consistency", "region_bias",
    # Relative position (2)
    "rel_amount_in_region", "rel_amount_in_direction",
]


# ══════════════════════════════════════════════════════════════
# REPRODUCIBILITY HELPERS
# ══════════════════════════════════════════════════════════════

def _fix_seeds(seed: int = SEED):
    """Fix all random seeds for reproducibility."""
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def _dataset_hash(df: pd.DataFrame) -> str:
    """Deterministic SHA-256 hash of the dataset."""
    # Sort for determinism, convert to CSV bytes
    sorted_df = df.sort_values(list(df.columns)).reset_index(drop=True)
    csv_bytes = sorted_df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()[:16]


def _feature_list_version(features: list[str]) -> str:
    """Hash of sorted feature list for version tracking."""
    return hashlib.sha256(str(sorted(features)).encode()).hexdigest()[:16]


def _compute_model_version(auc: float) -> str:
    """Generate semantic version based on AUC: v{major}.{minor}.{patch}.

    major = int(AUC * 100) — e.g. 0.85 → 85
    minor = int((AUC * 1000) % 10) — e.g. 0.853 → 3
    patch = timestamp seconds % 100 — ensures uniqueness across runs
    """
    major = int(auc * 100)
    minor = int((auc * 1000) % 10)
    patch = int(datetime.now(timezone.utc).timestamp()) % 100
    return f"v{major}.{minor}.{patch}"


def _get_previous_model_auc() -> float | None:
    """Load previous model.pkl and return its AUC (or None if missing/corrupt)."""
    prev_path = "model.pkl"
    if not os.path.exists(prev_path):
        return None
    try:
        prev = joblib.load(prev_path)
        return prev.get("metrics", {}).get("roc_auc")
    except Exception:
        return None


def _atomic_save_model(artifact: dict, new_auc: float) -> bool:
    """Atomically save model: backup → tmp → os.replace → verify.

    Also checks AUC regression — if new model is worse than previous,
    abort and keep old model.

    Steps:
      1. Check AUC regression (new >= old - 0.02 tolerance)
      2. Backup existing model.pkl → model.pkl.bak
      3. Write to model.pkl.tmp
      4. os.replace (atomic on both Linux and Windows)
      5. Verify by re-loading
      6. On failure: restore from .bak
    """
    model_path = "model.pkl"
    tmp_path = "model.pkl.tmp"
    bak_path = "model.pkl.bak"

    # ── Step 1: AUC regression check ──
    prev_auc = _get_previous_model_auc()
    if prev_auc is not None:
        auc_drop = prev_auc - new_auc
        if auc_drop > 0.02:  # 2pp tolerance
            print(f"\n⚠️  AUC REGRESSION: prev={prev_auc:.4f} → new={new_auc:.4f} (Δ={auc_drop:.4f})")
            print(f"    Threshold: 0.02 — model NOT saved to prevent quality degradation.")
            print(f"    If intentional, retrain with better features/data.")
            # Still save metrics for debugging
            _save_training_metrics_from_artifact(artifact, gate_passed=True, auc_regressed=True)
            return False
        elif auc_drop > 0:
            print(f"    AUC slightly lower: {prev_auc:.4f} → {new_auc:.4f} (Δ={auc_drop:.4f}, within tolerance)")

    # ── Step 2: Backup existing model ──
    had_backup = False
    if os.path.exists(model_path):
        try:
            import shutil
            shutil.copy2(model_path, bak_path)
            had_backup = True
            print(f"    Backup created: {bak_path}")
        except Exception as e:
            print(f"    [WARN] Failed to create backup: {e}")

    # ── Step 3: Write to tmp ──
    try:
        joblib.dump(artifact, tmp_path)
    except Exception as e:
        print(f"    [FAIL] Failed to write tmp: {e}")
        _rollback_model_save(tmp_path, bak_path, had_backup)
        return False

    # ── Step 4: Atomic replace ──
    try:
        os.replace(tmp_path, model_path)
    except Exception as e:
        print(f"    [FAIL] os.replace failed: {e}")
        _rollback_model_save(tmp_path, bak_path, had_backup)
        return False

    # ── Step 5: Verify by re-loading ──
    try:
        verify = joblib.load(model_path)
        verify_auc = verify.get("metrics", {}).get("roc_auc")
        if verify_auc is None:
            raise ValueError("Re-loaded model has no roc_auc metric")
        if abs(verify_auc - new_auc) > 1e-6:
            raise ValueError(f"Re-loaded model AUC mismatch: expected {new_auc:.6f}, got {verify_auc:.6f}")
        print(f"    Verification: model.pkl re-loaded OK (AUC={verify_auc:.4f}) ✓")
    except Exception as e:
        print(f"    [FAIL] Verification failed: {e}")
        _rollback_model_save(tmp_path, bak_path, had_backup)
        return False

    # Cleanup tmp (os.replace already removed it, but just in case)
    _safe_remove(tmp_path)

    return True


def _rollback_model_save(tmp_path: str, bak_path: str, had_backup: bool):
    """Rollback model save: restore from .bak, clean up tmp."""
    _safe_remove(tmp_path)
    if had_backup and os.path.exists(bak_path):
        try:
            os.replace(bak_path, "model.pkl")
            print(f"    ROLLBACK: restored model.pkl from {bak_path}")
        except Exception as e:
            print(f"    [CRITICAL] ROLLBACK FAILED: {e}")


def _safe_remove(path: str):
    """Remove file if exists, ignore errors."""
    try:
        os.remove(path)
    except OSError:
        pass


def _save_training_metrics_from_artifact(artifact: dict, *, gate_passed: bool, auc_regressed: bool = False):
    """Save training metrics JSON from artifact dict (used when AUC regression detected)."""
    os.makedirs("logs", exist_ok=True)
    metrics = artifact.get("metrics", {})
    repro = artifact.get("reproducibility", {})
    path = "logs/training_metrics.json"
    data = {
        "timestamp": repro.get("training_timestamp", datetime.now(timezone.utc).isoformat()),
        "gate_passed": gate_passed,
        "auc_regressed": auc_regressed,
        "min_auc_gate": MIN_AUC,
        "metrics": {k: v for k, v in metrics.items()},
        "reproducibility": {k: v for k, v in repro.items()},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"    📝 Metrics saved → {path}")


# ══════════════════════════════════════════════════════════════
# DISTRIBUTION SHIFT MONITORING
# ══════════════════════════════════════════════════════════════

def _log_distribution_shift(train_df: pd.DataFrame, val_df: pd.DataFrame):
    """Compare key distributions between train (2025) and val (2026)."""
    print("\n📊 Distribution Shift Analysis (2025 vs 2026):")
    
    pos_rate_train = train_df["target"].mean()
    pos_rate_val = val_df["target"].mean() if len(val_df) > 0 else None
    
    print(f"   pos_rate_train (2025): {pos_rate_train:.4f}")
    if pos_rate_val is not None:
        print(f"   pos_rate_val   (2026): {pos_rate_val:.4f}")
        drift = abs(pos_rate_train - pos_rate_val)
        drift_pct = drift / max(pos_rate_train, 1e-8) * 100
        status = "✅" if drift_pct < 10 else ("⚠️" if drift_pct < 25 else "❌")
        print(f"   pos_rate drift:        {drift:.4f} ({drift_pct:.1f}%) {status}")
    else:
        print(f"   pos_rate_val   (2026): N/A (empty)")

    # Numeric feature shifts
    numeric_cols = ["Причитающая сумма", "Норматив"]
    for col in numeric_cols:
        if col in train_df.columns and col in val_df.columns:
            train_mean = train_df[col].mean()
            val_mean = val_df[col].mean() if len(val_df) > 0 else None
            if val_mean is not None and train_mean > 0:
                shift_pct = abs(train_mean - val_mean) / train_mean * 100
                status = "✅" if shift_pct < 20 else ("⚠️" if shift_pct < 50 else "❌")
                print(f"   {col}: train_mean={train_mean:.0f}, val_mean={val_mean:.0f}, shift={shift_pct:.1f}% {status}")

    # Class imbalance
    train_pos = int((train_df["target"] == 1).sum())
    train_neg = int((train_df["target"] == 0).sum())
    ratio = train_neg / max(train_pos, 1)
    status = "✅" if ratio < 5 else ("⚠️" if ratio < 10 else "❌")
    print(f"   class_imbalance: pos={train_pos}, neg={train_neg}, ratio={ratio:.2f}:1 {status}")

    return {
        "pos_rate_train": float(pos_rate_train),
        "pos_rate_val": float(pos_rate_val) if pos_rate_val is not None else None,
        "class_ratio": float(ratio),
        "train_pos": train_pos,
        "train_neg": train_neg,
    }


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    # Fix seeds FIRST
    _fix_seeds(SEED)

    # ══════════════════════════════════════════════════════════════
    # 1. ЗАГРУЗКА
    # ══════════════════════════════════════════════════════════════
    print("=" * 60)
    print("  Скоринг субсидий — обучение v6 (production-stable)")
    print("=" * 60)

    df = pd.read_excel("data/subsidies.xlsx", skiprows=4)
    print(f"\n📂 Всего строк: {len(df)}")

    # Dataset hash for reproducibility
    ds_hash = _dataset_hash(df)
    print(f"   Dataset hash: {ds_hash}")

    # ══════════════════════════════════════════════════════════════
    # 2. ПОДГОТОВКА
    # ══════════════════════════════════════════════════════════════
    df["date"] = pd.to_datetime(df["Дата поступления"], dayfirst=True, errors="coerce")
    df["year"]        = df["date"].dt.year
    df["month"]       = df["date"].dt.month
    df["hour"]        = df["date"].dt.hour
    df["day_of_year"] = df["date"].dt.dayofyear
    df["day_of_week"] = df["date"].dt.dayofweek

    df["producer_id"] = df["Номер заявки"].astype(str).str[:11]

    df["Причитающая сумма"] = pd.to_numeric(df["Причитающая сумма"], errors="coerce")
    df["Норматив"]          = pd.to_numeric(df["Норматив"], errors="coerce")

    # Производные финансовые (deterministic fillna — NOT random)
    df["amount_to_norm"] = (df["Причитающая сумма"] / df["Норматив"].replace(0, np.nan))
    df["log_amount"]     = np.log1p(df["Причитающая сумма"].fillna(0))
    df["log_norm"]       = np.log1p(df["Норматив"].fillna(0))

    # Целевая: только завершённые
    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(POSITIVE), "target"] = 1
    df.loc[df["Статус заявки"].isin(NEGATIVE), "target"] = 0

    df_resolved = df.dropna(subset=["target"]).copy()
    df_resolved["target"] = df_resolved["target"].astype(int)

    print(f"   Завершённых: {len(df_resolved)}  (pos={df_resolved['target'].mean():.1%})")

    # ══════════════════════════════════════════════════════════════
    # 3. TRAIN / VAL (по времени — фиксированный split)
    # ══════════════════════════════════════════════════════════════
    train_raw = df_resolved[df_resolved["year"] == 2025].copy()
    val_raw   = df_resolved[df_resolved["year"] == 2026].copy()

    print(f"\n📊 Train (2025): {len(train_raw)}  pos={train_raw['target'].mean():.1%}")
    print(f"   Val   (2026): {len(val_raw)}  pos={val_raw['target'].mean():.1%}" if len(val_raw) > 0 else "   Val   (2026): EMPTY")

    if len(train_raw) == 0:
        raise ValueError("Train set (2025) is empty — check data/subsidies.xlsx")
    if len(val_raw) == 0:
        print("   ⚠️ Val set (2026) is empty — will skip hold-out evaluation")

    # Distribution shift analysis
    shift_stats = _log_distribution_shift(train_raw, val_raw)

    # ══════════════════════════════════════════════════════════════
    # 4. АГРЕГАТЫ (из ALL 2025 data incl unresolved — for better coverage)
    # ══════════════════════════════════════════════════════════════
    #
    # SAFETY: success_rate вычисляется ТОЛЬКО на resolved (target not NaN).
    # Но volume и avg_amount — на ВСЕХ 2025 записях (включая незавершённые).
    # Это улучшает coverage group features для 2026 producers.
    # NO LEAKAGE: не используем target из 2026.
    # ══════════════════════════════════════════════════════════════
    def build_group_stats(all_train_df, resolved_train_df, df_to_enrich, group_col, prefix):
        """Compute group stats on ALL 2025 data (for coverage) + resolved (for success_rate).

        - success_rate: только на resolved (целевая, без leakage)
        - volume, avg_amount: на ВСЕХ записях 2025 (лучше покрытие)
        """
        # success_rate — только на resolved
        stats_sr = resolved_train_df.groupby(group_col).agg(
            success_rate=("target", "mean"),
        ).reset_index()

        # volume, avg_amount — на ВСЕХ 2025 записях
        stats_vol = all_train_df.groupby(group_col).agg(
            volume=("Причитающая сумма", "count"),
            avg_amount=("Причитающая сумма", "mean"),
        ).reset_index()

        stats = stats_sr.merge(stats_vol, on=group_col, how="outer")
        stats.columns = [group_col, f"{prefix}_sr", f"{prefix}_vol", f"{prefix}_avg_amt"]
        enriched = df_to_enrich.merge(stats, on=group_col, how="left")

        # Deterministic fallback values
        global_sr = float(resolved_train_df["target"].mean())
        median_vol = float(stats[f"{prefix}_vol"].median())
        median_amt = float(stats[f"{prefix}_avg_amt"].median())

        enriched[f"{prefix}_sr"] = enriched[f"{prefix}_sr"].fillna(global_sr)
        enriched[f"{prefix}_vol"] = enriched[f"{prefix}_vol"].fillna(median_vol)
        enriched[f"{prefix}_avg_amt"] = enriched[f"{prefix}_avg_amt"].fillna(median_amt)
        return enriched

    # ALL 2025 data (включая незавершённые) — для улучшения coverage
    train_all_2025 = df[df["year"] == 2025].copy()

    print("\n🛡️  Агрегаты по region / direction / subsidy / district (ALL 2025 incl unresolved)...")

    train_e = build_group_stats(train_all_2025, train_raw, train_raw, "Область", "reg")
    val_e   = build_group_stats(train_all_2025, train_raw, val_raw,   "Область", "reg")

    train_e = build_group_stats(train_all_2025, train_raw, train_e, "Направление водства", "dir")
    val_e   = build_group_stats(train_all_2025, train_raw, val_e,   "Направление водства", "dir")

    train_e = build_group_stats(train_all_2025, train_raw, train_e, "Наименование субсидирования", "sub")
    val_e   = build_group_stats(train_all_2025, train_raw, val_e,   "Наименование субсидирования", "sub")

    train_e = build_group_stats(train_all_2025, train_raw, train_e, "Район хозяйства", "dist")
    val_e   = build_group_stats(train_all_2025, train_raw, val_e,   "Район хозяйства", "dist")

    # ══════════════════════════════════════════════════════════════
    # 4b. v7 INTERACTION & TREND FEATURES (train only — no leakage)
    # ══════════════════════════════════════════════════════════════
    print("\n🛡️  v7 — Interaction & behavioral features (train only)...")

    # Per-producer aggregates (computed on train, applied to both)
    producer_stats = train_raw.groupby("producer_id").agg(
        app_count=("target", "count"),
        app_completion=("target", "mean"),
        avg_amount_producer=("Причитающая сумма", "mean"),
        std_amount_producer=("Причитающая сумма", "std"),
    ).reset_index()
    producer_stats["std_amount_producer"] = producer_stats["std_amount_producer"].fillna(0)
    producer_stats["amount_cv"] = producer_stats["std_amount_producer"] / (
        producer_stats["avg_amount_producer"].replace(0, np.nan)
    )
    producer_stats["amount_cv"] = producer_stats["amount_cv"].fillna(0).clip(upper=5)

    train_e = train_e.merge(producer_stats, on="producer_id", how="left")
    val_e = val_e.merge(producer_stats, on="producer_id", how="left")

    # Global fallback for unseen producers
    global_app_count = float(train_raw["producer_id"].value_counts().median())
    global_completion = float(train_raw["target"].mean())
    global_avg_amount = float(train_raw["Причитающая сумма"].median())
    global_amount_cv = float(producer_stats["amount_cv"].median())

    for col, fallback in [
        ("app_count", global_app_count),
        ("app_completion", global_completion),
        ("avg_amount_producer", global_avg_amount),
        ("amount_cv", global_amount_cv),
    ]:
        train_e[col] = train_e[col].fillna(fallback)
        val_e[col] = val_e[col].fillna(fallback)

    # month × amount interaction
    train_e["month_amount_inter"] = train_e["month"] * train_e["log_amount"]
    val_e["month_amount_inter"]   = val_e["month"] * val_e["log_amount"]

    # Norm per application (normalized)
    train_e["norm_per_app"] = train_e["Норматив"] / train_e["app_count"].replace(0, np.nan)
    val_e["norm_per_app"]   = val_e["Норматив"] / val_e["app_count"].replace(0, np.nan)
    for dset in [train_e, val_e]:
        med = train_e["norm_per_app"].median()
        dset["norm_per_app"] = dset["norm_per_app"].fillna(med).clip(upper=1e6)

    # Completion trend: producer's completion rate vs their region's average
    train_e["completion_trend"] = train_e["app_completion"] - train_e["reg_sr"]
    val_e["completion_trend"]   = val_e["app_completion"] - val_e["reg_sr"]

    # Application frequency: log(app_count + 1)
    train_e["app_frequency"] = np.log1p(train_e["app_count"])
    val_e["app_frequency"]   = np.log1p(val_e["app_count"])

    # Amount consistency (1 / (CV + 1)) — higher = more consistent amounts
    train_e["amount_consistency"] = 1.0 / (train_e["amount_cv"] + 1.0)
    val_e["amount_consistency"]   = 1.0 / (val_e["amount_cv"] + 1.0)

    # Region bias: is this producer from an over/under-subsidized region?
    train_e["region_bias"] = train_e["reg_sr"] - global_completion
    val_e["region_bias"]   = val_e["reg_sr"] - global_completion

    # Relative amount within region
    train_e["rel_amount_in_region"] = train_e["Причитающая сумма"] / (
        train_e["reg_avg_amt"].replace(0, np.nan)
    )
    val_e["rel_amount_in_region"] = val_e["Причитающая сумма"] / (
        val_e["reg_avg_amt"].replace(0, np.nan)
    )
    for dset in [train_e, val_e]:
        med = train_e["rel_amount_in_region"].median()
        dset["rel_amount_in_region"] = dset["rel_amount_in_region"].fillna(med).clip(upper=10)

    # Relative amount within direction
    train_e["rel_amount_in_direction"] = train_e["Причитающая сумма"] / (
        train_e["dir_avg_amt"].replace(0, np.nan)
    )
    val_e["rel_amount_in_direction"] = val_e["Причитающая сумма"] / (
        val_e["dir_avg_amt"].replace(0, np.nan)
    )
    for dset in [train_e, val_e]:
        med = train_e["rel_amount_in_direction"].median()
        dset["rel_amount_in_direction"] = dset["rel_amount_in_direction"].fillna(med).clip(upper=10)

    print(f"   ✓ Added {len(FEATURES) - 24} new features (total: {len(FEATURES)})")

    # ══════════════════════════════════════════════════════════════
    # 5. ENCODE + STABLE NaN FILL
    # ══════════════════════════════════════════════════════════════
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

    # ══════════════════════════════════════════════════════════════
    # 6. FEATURES — stable fill (deterministic 0, not median-of-column)
    # ══════════════════════════════════════════════════════════════
    # Compute train medians ONCE for deterministic fill
    train_medians = {}
    for c in FEATURES:
        if c in train_e.columns and train_e[c].dtype != object:
            med = train_e[c].median()
            train_medians[c] = float(med) if pd.notna(med) else 0.0

    for dset in [train_e, val_e]:
        for c in FEATURES:
            if c in dset.columns:
                # Use TRAIN medians for both sets (no data leakage)
                fill_val = train_medians.get(c, 0.0)
                dset[c] = dset[c].fillna(fill_val)

    X_train = train_e[FEATURES].copy()
    y_train = train_e["target"].copy()
    X_val   = val_e[FEATURES].copy()
    y_val   = val_e["target"].copy()

    # Final NaN safety net
    X_train = X_train.fillna(0)
    X_val   = X_val.fillna(0)

    print(f"\n   Train: {len(X_train)} | Val: {len(X_val)} | Признаков: {len(FEATURES)}")
    print(f"   Feature version: {_feature_list_version(FEATURES)}")

    pos_n = max(int((y_train == 1).sum()), 1)
    neg_n = int((y_train == 0).sum())
    scale_pos_weight = neg_n / pos_n
    print(f"\n   class balance: pos={pos_n} neg={neg_n}  scale_pos_weight={scale_pos_weight:.3f}")

    # ══════════════════════════════════════════════════════════════
    # 7. MODEL DEFINITION (deterministic — fixed seed)
    # ══════════════════════════════════════════════════════════════

    def _xgb_base(n_trees: int, early_stop: int | None, sample_weight=None) -> XGBClassifier:
        kw = dict(
            n_estimators=n_trees,
            max_depth=4,              # v7: reduced from 5 → less overfitting
            learning_rate=0.03,       # v7: reduced from 0.045 → more stable
            min_child_weight=6,       # v7: increased from 4 → more conservative
            subsample=0.75,           # v7: reduced from 0.82 → more regularization
            colsample_bytree=0.70,    # v7: reduced from 0.82 → fewer features per tree
            colsample_bylevel=0.80,   # v7: new — additional feature sampling
            reg_lambda=3.5,           # v7: increased from 2.0 → stronger L2
            reg_alpha=0.15,           # v7: increased from 0.05 → stronger L1
            gamma=0.25,               # v7: increased from 0.15 → more conservative splits
            scale_pos_weight=scale_pos_weight,
            random_state=SEED,
            n_jobs=-1,
            tree_method="hist",
            eval_metric="auc",
        )
        if early_stop is not None:
            kw["early_stopping_rounds"] = early_stop
        return XGBClassifier(**kw)

    model_config = _xgb_base(1, None).get_params()

    # ══════════════════════════════════════════════════════════════
    # 8. CROSS-VALIDATION (GroupKFold by producer_id — no leakage)
    # ══════════════════════════════════════════════════════════════
    print("\n🔄 GroupKFold CV на 2025 данных (XGBoost) — без leakage через producer_id...")

    # GroupKFold: все строки одного producer в train ИЛИ в test
    groups = train_e["producer_id"].values
    gkf = GroupKFold(n_splits=5)
    cv_aucs, cv_f1s = [], []

    # Time-decay sample weights для CV
    # Более поздние заявки 2025 получают больший вес → ближе к 2026 паттернам
    if "date" in train_e.columns:
        dates_numeric = pd.to_numeric(train_e["date"])
        min_d, max_d = dates_numeric.min(), dates_numeric.max()
        if max_d > min_d:
            time_decay = (0.5 + 0.5 * (dates_numeric - min_d) / (max_d - min_d)).astype(np.float32)
        else:
            time_decay = np.ones(len(train_e), dtype=np.float32)
    else:
        time_decay = np.ones(len(train_e), dtype=np.float32)

    for fold, (tr_idx, te_idx) in enumerate(gkf.split(X_train, y_train, groups), 1):
        Xtr, Xte = X_train.iloc[tr_idx], X_train.iloc[te_idx]
        ytr, yte = y_train.iloc[tr_idx], y_train.iloc[te_idx]
        wtr = time_decay[tr_idx]

        m = _xgb_base(n_trees=450, early_stop=None)
        m.fit(Xtr.values, ytr.values, sample_weight=wtr, verbose=False)
        p = m.predict_proba(Xte.values)[:, 1]
        a = roc_auc_score(yte, p)
        f = f1_score(yte, (p >= 0.5).astype(int))
        cv_aucs.append(a)
        cv_f1s.append(f)
        n_train_producers = len(set(groups[tr_idx]))
        n_test_producers = len(set(groups[te_idx]))
        print(f"   Fold {fold}: AUC={a:.4f}  F1={f:.4f}  (train producers: {n_train_producers}, test: {n_test_producers})")

    cv_auc_mean = float(np.mean(cv_aucs))
    cv_auc_std = float(np.std(cv_aucs))
    print(f"   ── Mean CV AUC: {cv_auc_mean:.4f} ± {cv_auc_std:.4f}")
    print(f"   ── Mean CV F1 : {np.mean(cv_f1s):.4f} ± {np.std(cv_f1s):.4f}")

    # ══════════════════════════════════════════════════════════════
    # 9. FINAL MODEL TRAINING (с time-decay weighting)
    # ══════════════════════════════════════════════════════════════
    print("\n🚀 Обучение финальной модели (XGBoost + early stopping + time-decay)...")
    train_ord = train_e.sort_values("date").reset_index(drop=True)
    X_ord = train_ord[FEATURES].astype(np.float64).fillna(0.0)
    y_ord = train_ord["target"].astype(int)
    n = len(train_ord)
    cut = max(int(n * 0.88), min(n - 2000, n - 1))
    X_fit, X_es = X_ord.iloc[:cut], X_ord.iloc[cut:]
    y_fit, y_es = y_ord.iloc[:cut], y_ord.iloc[cut:]

    # Time-decay weights для training (float32 для sklearn calibration)
    dates_fit = pd.to_numeric(train_ord.iloc[:cut]["date"])
    min_d_fit, max_d_fit = dates_fit.min(), dates_fit.max()
    if max_d_fit > min_d_fit:
        w_fit = (0.5 + 0.5 * (dates_fit - min_d_fit) / (max_d_fit - min_d_fit)).astype(np.float32)
    else:
        w_fit = np.ones(len(dates_fit), dtype=np.float32)

    es_model = _xgb_base(n_trees=900, early_stop=55)
    es_model.fit(
        X_fit.values, y_fit.values,
        sample_weight=w_fit,
        eval_set=[(X_es.values, y_es.values)],
        verbose=False,
    )
    best_it = getattr(es_model, "best_iteration", None)
    if best_it is not None and best_it >= 0:
        n_final = int(min(best_it + 1 + 24, 1000))
    else:
        n_final = 500
    print(f"   выбрано деревьев: {n_final} (best_iteration={best_it})")

    base_model = _xgb_base(n_trees=n_final, early_stop=None)
    base_model.fit(X_train.values, y_train.values, sample_weight=time_decay, verbose=False)

    # Калибровка — sigmoid более робастный к distribution shift чем isotonic
    print("   Калибровка (sigmoid, 3-fold, time-decay)...")
    model = CalibratedClassifierCV(base_model, method="sigmoid", cv=3)
    model.fit(X_train.values, y_train.values, sample_weight=time_decay)

    # ══════════════════════════════════════════════════════════════
    # 10. HOLD-OUT EVALUATION
    # ══════════════════════════════════════════════════════════════
    if len(y_val) > 0:
        proba = model.predict_proba(X_val.values)[:, 1]
        auc = roc_auc_score(y_val, proba)
        ap = average_precision_score(y_val, proba)
        precisions, recalls, thresholds = precision_recall_curve(y_val, proba)
        f1_arr = 2 * precisions * recalls / (precisions + recalls + 1e-8)
        best_idx = np.argmax(f1_arr)
        best_thr = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5
        best_f1 = float(f1_arr[best_idx])
        pred_opt = (proba >= best_thr).astype(int)
        prec_t = float(precision_score(y_val, pred_opt, zero_division=0))
        rec_t = float(recall_score(y_val, pred_opt, zero_division=0))
    else:
        proba = np.array([])
        auc = cv_auc_mean  # Use CV AUC as proxy when no val data
        ap = best_f1 = prec_t = rec_t = 0.0
        best_thr = 0.5
        pred_opt = np.array([])

    print(f"\n{'=' * 55}")
    print(f"  HOLD-OUT 2026  (только завершённые заявки)")
    print(f"{'=' * 55}")
    print(f"  ROC-AUC          : {auc:.4f}  {'✅' if auc >= MIN_AUC else '❌ BELOW GATE'}")
    print(f"  Average Precision : {ap:.4f}")
    print(f"  Лучший порог     : {best_thr:.3f}  →  F1 = {best_f1:.4f}")
    print(f"  Precision         : {prec_t:.4f}")
    print(f"  Recall            : {rec_t:.4f}")
    print(f"{'=' * 55}")

    if len(y_val) > 0:
        print(f"\n  Classification Report (порог={best_thr:.3f}):")
        print(classification_report(y_val, pred_opt,
              target_names=["Отклон./Отозв.", "Исполнена"]))

        # Confusion Matrix
        cm = confusion_matrix(y_val, pred_opt)
        tn, fp, fn, tp = cm.ravel()
        print(f"\n  Confusion Matrix (порог={best_thr:.3f}):")
        print(f"  ┌──────────────┬──────────┬──────────┐")
        print(f"  │              │ Pred −   │ Pred +   │")
        print(f"  ├──────────────┼──────────┼──────────┤")
        print(f"  │ Actual − (TN)│ {tn:>8} │ {fp:>8} │  FP={fp}")
        print(f"  │ Actual + (TP)│ {fn:>8} │ {tp:>8} │  FN={fn}")
        print(f"  └──────────────┴──────────┴──────────┘")
        print(f"  Accuracy : {(tp+tn)/(tp+tn+fp+fn):.4f}")
        print(f"  Precision: {tp/(tp+fp):.4f}" if (tp+fp) > 0 else "  Precision: N/A")
        print(f"  Recall   : {tp/(tp+fn):.4f}" if (tp+fn) > 0 else "  Recall: N/A")

    # Калибровка
    print("📉 Калибровка:")
    if len(y_val) > 100:
        try:
            pt, pp = calibration_curve(
                y_val, proba, n_bins=min(8, len(y_val) // 200 + 3), strategy="quantile"
            )
            for t, p in zip(pt, pp):
                d = t - p
                m = "✅" if abs(d) < 0.10 else ("⚠️" if abs(d) < 0.20 else "❌")
                print(f"   {m} pred={p:.2f} → real={t:.2f}  (Δ={d:+.2f})")
        except Exception as e:
            print(f"   ⚠️ {e}")
    else:
        print("   (пропуск: мало точек для кривой калибровки)")

    # Feature importance
    print("\n📈 Важность признаков:")
    imp = pd.Series(base_model.feature_importances_, index=FEATURES).sort_values(ascending=False)
    for feat, val in imp.items():
        bar = "█" * int(val * 40)
        print(f"   {feat:22s} {val:.4f}  {bar}")

    # ══════════════════════════════════════════════════════════════
    # 11. QUALITY GATE
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'=' * 55}")
    print(f"  QUALITY GATE (min AUC = {MIN_AUC})")
    print(f"{'=' * 55}")

    gate_auc = auc  # hold-out AUC (or CV AUC if no val)
    if gate_auc < MIN_AUC:
        print(f"  ❌ QUALITY GATE FAILED: AUC={gate_auc:.4f} < {MIN_AUC}")
        print(f"  Model NOT saved. Fix data or features before retraining.")
        print(f"  CV AUC was: {cv_auc_mean:.4f} ± {cv_auc_std:.4f}")
        
        # Still save metrics for debugging
        _save_training_metrics(
            auc=gate_auc, ap=ap, best_f1=best_f1, best_thr=best_thr,
            prec_t=prec_t, rec_t=rec_t, cv_auc_mean=cv_auc_mean,
            cv_auc_std=cv_auc_std, ds_hash=ds_hash, shift_stats=shift_stats,
            model_config=model_config, gate_passed=False,
            train_size=len(X_train), val_size=len(X_val),
        )
        sys.exit(2)  # Exit code 2 = quality gate failure

    print(f"  ✅ QUALITY GATE PASSED: AUC={gate_auc:.4f} >= {MIN_AUC}")

    # ══════════════════════════════════════════════════════════════
    # 12. ATOMIC SAVE MODEL + REPRODUCIBILITY METADATA (tmp→replace + backup)
    # ══════════════════════════════════════════════════════════════

    # Model versioning: v{major}.{minor}.{patch}
    model_version = _compute_model_version(auc)

    def _sanitize_for_json(val):
        """Convert numpy NaN/inf to None for safe JSON serialization."""
        if val is None:
            return None
        if isinstance(val, (float, np.floating)):
            if np.isnan(val) or np.isinf(val):
                return None
        return val

    def _sanitize_config(cfg):
        """Sanitize model config for JSON/JSONB storage."""
        cleaned = {}
        for k, v in cfg.items():
            if isinstance(v, (int, float, bool, type(None))):
                cleaned[k] = _sanitize_for_json(v)
            elif isinstance(v, np.floating):
                cleaned[k] = _sanitize_for_json(float(v))
            else:
                cleaned[k] = str(v)
        # Double-check: serialize and parse back to guarantee no NaN
        return json.loads(json.dumps(cleaned, allow_nan=False))

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
        "train_medians": train_medians,  # For consistent inference (same as training)
        "producer_stats": {
            "df": producer_stats.to_dict(orient="list"),
            "fallbacks": {
                "app_count": global_app_count,
                "app_completion": global_completion,
                "avg_amount_producer": global_avg_amount,
                "amount_cv": global_amount_cv,
            }
        },
        "metrics": {
            "roc_auc": float(auc),
            "avg_precision": float(ap),
            "best_f1": float(best_f1),
            "best_threshold": float(best_thr),
            "precision": prec_t,
            "recall": rec_t,
            "cv_auc_mean": cv_auc_mean,
            "cv_auc_std": cv_auc_std,
            "cv_f1_mean": float(np.mean(cv_f1s)),
            "train_size": int(len(X_train)),
            "val_size": int(len(X_val)),
        },
        "reproducibility": {
            "seed": SEED,
            "feature_list_version": _feature_list_version(FEATURES),
            "dataset_hash": ds_hash,
            "model_version": model_version,
            "model_config": _sanitize_config(model_config),
            "training_timestamp": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version.split()[0],
            "xgboost_version": xgb.__version__,
            "sklearn_version": sklearn.__version__,
            "min_auc_gate": MIN_AUC,
            "model_version": model_version,
        },
    }

    # ── Atomic save: backup → tmp → os.replace → verify ──
    save_success = _atomic_save_model(artifact, auc)
    if not save_success:
        print(f"\n❌ FAILED to save model atomically. Exiting without modifying model.pkl")
        sys.exit(3)

    print(f"\n✅ Модель сохранена → model.pkl  (version: {model_version})")
    print(f"   Порог: {best_thr:.3f} | AUC: {auc:.4f} | F1: {best_f1:.4f}")
    print(f"   CV AUC: {cv_auc_mean:.4f} ± {cv_auc_std:.4f}")
    print(f"   Seed: {SEED} | Dataset hash: {ds_hash}")

    # ══════════════════════════════════════════════════════════════
    # 12b. REGISTER IN MODEL STORAGE + REGISTRY
    # ══════════════════════════════════════════════════════════════
    try:
        from services.model_storage import get_storage
        from services.model_registry import register_model, ensure_registry_table

        storage = get_storage()
        storage_path = storage.save(model_version, artifact)
        print(f"    ✓ Model stored in {storage._storage_type if hasattr(storage, '_storage_type') else 'local'}: {storage_path}")

        # Register in DB
        ensure_registry_table()
        registered = register_model(model_version, artifact, storage_path)
        if registered:
            print(f"    ✓ Model registered in registry: {model_version}")
    except Exception as reg_err:
        print(f"    [WARN] Model storage/registry failed (model still saved locally): {reg_err}")

    # Save training metrics JSON
    _save_training_metrics(
        auc=float(auc), ap=float(ap), best_f1=float(best_f1), best_thr=float(best_thr),
        prec_t=prec_t, rec_t=rec_t, cv_auc_mean=cv_auc_mean,
        cv_auc_std=cv_auc_std, ds_hash=ds_hash, shift_stats=shift_stats,
        model_config=model_config, gate_passed=True,
        train_size=len(X_train), val_size=len(X_val),
    )

    # ══════════════════════════════════════════════════════════════
    # 13. SYNC TO SUPABASE
    # ══════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  СИНХРОНИЗАЦИЯ С SUPABASE")
    print("=" * 60)
    try:
        from ml.sync_to_supabase import sync_scores_to_supabase
        success = sync_scores_to_supabase(df, artifact)
        if success:
            print("\n✅ УСПЕШНО: Scores синхронизированы в Supabase")
        else:
            print("\n❌ ОШИБКА: sync_scores_to_supabase вернула False")
    except Exception as e:
        print(f"\n❌ ИСКЛЮЧЕНИЕ при синхронизации: {type(e).__name__}: {e}")
        traceback.print_exc()
        print("\n⚠️ WARNING: Frontend будет показывать устаревшие данные")


def _sanitize_for_json(val):
    """Convert numpy NaN/inf to None for safe JSON serialization."""
    if val is None:
        return None
    if isinstance(val, (float, np.floating)):
        if np.isnan(val) or np.isinf(val):
            return None
    return val


def _sanitize_config(cfg):
    """Sanitize model config for JSON/JSONB storage."""
    cleaned = {}
    for k, v in cfg.items():
        if isinstance(v, (int, float, bool, type(None))):
            cleaned[k] = _sanitize_for_json(v)
        elif isinstance(v, np.floating):
            cleaned[k] = _sanitize_for_json(float(v))
        else:
            cleaned[k] = str(v)
    return json.loads(json.dumps(cleaned, allow_nan=False))


def _save_training_metrics(*, auc, ap, best_f1, best_thr, prec_t, rec_t,
                           cv_auc_mean, cv_auc_std, ds_hash, shift_stats,
                           model_config, gate_passed, train_size, val_size):
    """Save training metrics to JSON for audit trail."""
    os.makedirs("logs", exist_ok=True)
    
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gate_passed": gate_passed,
        "min_auc_gate": MIN_AUC,
        "metrics": {
            "roc_auc": auc,
            "avg_precision": ap,
            "best_f1": best_f1,
            "best_threshold": best_thr,
            "precision": prec_t,
            "recall": rec_t,
            "cv_auc_mean": cv_auc_mean,
            "cv_auc_std": cv_auc_std,
            "train_size": train_size,
            "val_size": val_size,
        },
        "reproducibility": {
            "seed": SEED,
            "dataset_hash": ds_hash,
            "feature_list_version": _feature_list_version(FEATURES),
            "feature_count": len(FEATURES),
        },
        "distribution_shift": shift_stats,
        "model_config": _sanitize_config(model_config),
    }

    path = "logs/training_metrics.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"\n📝 Metrics saved → {path}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise  # Allow sys.exit() to propagate
    except Exception as e:
        os.makedirs("logs", exist_ok=True)
        with open("logs/train_error.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        print(f"\n❌ ОШИБКА ОБУЧЕНИЯ: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
