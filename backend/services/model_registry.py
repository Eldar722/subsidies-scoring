"""
model_registry.py — Model version registry + auto-rollback.

Features:
  - Track all model versions in PostgreSQL (model_registry table)
  - Mark which model is currently active
  - Auto-rollback: if post-deploy metrics degrade beyond threshold, revert to previous
  - Manual rollback API

Usage:
  from services.model_registry import register_model, activate_model, check_auto_rollback

  # After training:
  register_model("v85.3.42", artifact_dict)

  # On pipeline success:
  activate_model("v85.3.42")

  # Post-deploy monitoring (called after serving some requests):
  check_auto_rollback()  # auto-rolls back if metrics degraded
"""

import os
import time
import threading
from datetime import datetime, timezone
from typing import Any

import psycopg2
import json as json_mod
from core.config import DATABASE_URL
from services.model_storage import get_storage, LocalDiskStorage

# ── Auto-rollback configuration ──
AUTO_ROLLBACK_ENABLED = os.environ.get("AUTO_ROLLBACK_ENABLED", "1") == "1"
AUTO_ROLLBACK_AUC_THRESHOLD = float(os.environ.get("AUTO_ROLLBACK_AUC_THRESHOLD", "0.03"))  # 3pp drop
AUTO_ROLLBACK_F1_THRESHOLD = float(os.environ.get("AUTO_ROLLBACK_F1_THRESHOLD", "0.05"))   # 5pp drop
AUTO_ROLLBACK_CHECK_DELAY = int(os.environ.get("AUTO_ROLLBACK_CHECK_DELAY", "300"))  # 5 min after deploy
AUTO_ROLLBACK_WINDOW = int(os.environ.get("AUTO_ROLLBACK_WINDOW", "3600"))  # 1h observation window

_lock = threading.Lock()


def _get_pg_connection():
    """Direct psycopg2 connection."""
    import psycopg2
    return psycopg2.connect(DATABASE_URL, connect_timeout=30)


def ensure_registry_table():
    """Create model_registry table if not exists (idempotent).

    Should be called at startup or before first registration.
    """
    conn = _get_pg_connection()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS model_registry (
                    version TEXT PRIMARY KEY,
                    roc_auc FLOAT,
                    cv_auc_mean FLOAT,
                    best_f1 FLOAT,
                    precision FLOAT,
                    recall FLOAT,
                    train_size INT,
                    val_size INT,
                    dataset_hash TEXT,
                    seed INT,
                    feature_count INT,
                    storage_path TEXT,
                    storage_type TEXT DEFAULT 'local',
                    status TEXT DEFAULT 'registered',  -- registered | active | rolled_back | archived
                    created_at TIMESTAMPTZ DEFAULT now(),
                    activated_at TIMESTAMPTZ,
                    deactivated_at TIMESTAMPTZ,
                    rollback_reason TEXT,
                    metadata JSONB
                )
            """)
            # Index for fast lookups
            cur.execute("CREATE INDEX IF NOT EXISTS idx_model_registry_status ON model_registry(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_model_registry_created ON model_registry(created_at DESC)")
        conn.commit()
        print("[OK] Model registry table ensured")
    except Exception as e:
        conn.rollback()
        print(f"[WARN] Failed to ensure registry table: {e}")
    finally:
        conn.close()


def register_model(version: str, artifact: dict, storage_path: str = "") -> bool:
    """Register a new model version in the registry.

    Args:
        version: Model version string (e.g. "v85.3.42")
        artifact: The full model artifact dict from train.py
        storage_path: Where the model is stored (local path or S3 URI)

    Returns:
        True if registered successfully
    """
    metrics = artifact.get("metrics", {})
    repro = artifact.get("reproducibility", {})

    conn = _get_pg_connection()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO model_registry (
                    version, roc_auc, cv_auc_mean, best_f1, precision, recall,
                    train_size, val_size, dataset_hash, seed, feature_count,
                    storage_path, storage_type, status, created_at, metadata
                ) VALUES (
                    %(version)s, %(roc_auc)s, %(cv_auc_mean)s, %(best_f1)s,
                    %(precision)s, %(recall)s, %(train_size)s, %(val_size)s,
                    %(dataset_hash)s, %(seed)s, %(feature_count)s,
                    %(storage_path)s, %(storage_type)s, 'registered',
                    %(created_at)s, %(metadata)s
                )
                ON CONFLICT (version) DO UPDATE SET
                    roc_auc = EXCLUDED.roc_auc,
                    cv_auc_mean = EXCLUDED.cv_auc_mean,
                    best_f1 = EXCLUDED.best_f1,
                    status = 'registered',
                    metadata = EXCLUDED.metadata
            """, {
                "version": version,
                "roc_auc": metrics.get("roc_auc"),
                "cv_auc_mean": metrics.get("cv_auc_mean"),
                "best_f1": metrics.get("best_f1"),
                "precision": metrics.get("precision"),
                "recall": metrics.get("recall"),
                "train_size": metrics.get("train_size"),
                "val_size": metrics.get("val_size"),
                "dataset_hash": repro.get("dataset_hash"),
                "seed": repro.get("seed"),
                "feature_count": len(artifact.get("features", [])),
                "storage_path": storage_path,
                "storage_type": "s3" if storage_path.startswith("s3://") else "local",
                "created_at": repro.get("training_timestamp", datetime.now(timezone.utc)),
                "metadata": json_mod.dumps({
                    "model_config": repro.get("model_config", {}),
                    "python_version": repro.get("python_version"),
                    "xgboost_version": repro.get("xgboost_version"),
                    "sklearn_version": repro.get("sklearn_version"),
                }),
            })
        conn.commit()
        print(f"[OK] Model registered: {version} (AUC={metrics.get('roc_auc', '?')})")
        return True
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Failed to register model {version}: {e}")
        return False
    finally:
        conn.close()


def activate_model(version: str) -> dict | None:
    """Activate a model version. Deactivates the previous active model.

    Returns dict with previous_active version and rollback info, or None on failure.
    """
    storage = get_storage()
    result = {"success": False, "previous_active": None, "rolled_back": False}

    with _lock:
        conn = _get_pg_connection()
        try:
            conn.autocommit = False

            # Get previous active model
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT version, roc_auc, best_f1 FROM model_registry
                    WHERE status = 'active' ORDER BY activated_at DESC LIMIT 1
                """)
                prev = cur.fetchone()
                if prev:
                    result["previous_active"] = prev[0]
                    # Deactivate previous
                    cur.execute("""
                        UPDATE model_registry SET
                            status = 'registered',
                            deactivated_at = now()
                        WHERE version = %s AND status = 'active'
                    """, (prev[0],))

            # Check the model exists in storage
            if not storage.exists(version):
                # Try from local default path as fallback
                from core.config import MODEL_PATH
                if not os.path.exists(MODEL_PATH):
                    raise FileNotFoundError(f"Model {version} not found in storage or local")

            # Activate new model
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE model_registry SET
                        status = 'active',
                        activated_at = now()
                    WHERE version = %s
                """, (version,))

            conn.commit()

            # Activate in storage
            storage.set_active(version)

            # Reload model in memory
            from core.state import safe_swap_model
            from core.config import MODEL_PATH
            if storage.exists(version):
                # Load from storage, save locally, then swap
                artifact = storage.load(version)
                import joblib
                joblib.dump(artifact, MODEL_PATH)
            safe_swap_model(MODEL_PATH)
            try:
                from core.state import build_precomputed_caches
                build_precomputed_caches()
            except Exception as cache_err:
                print(f"[WARN] Cache rebuild after activation: {cache_err}")

            result["success"] = True
            print(f"[OK] Model activated: {version}")

            # Schedule auto-rollback check
            if AUTO_ROLLBACK_ENABLED:
                _schedule_auto_rollback(version, result["previous_active"])

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to activate model {version}: {e}")
        finally:
            conn.close()

    return result


def get_active_model() -> dict | None:
    """Get the currently active model from registry."""
    conn = _get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT version, roc_auc, cv_auc_mean, best_f1, precision, recall,
                       activated_at, storage_path, metadata
                FROM model_registry
                WHERE status = 'active'
                ORDER BY activated_at DESC LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                return {
                    "version": row[0],
                    "roc_auc": row[1],
                    "cv_auc_mean": row[2],
                    "best_f1": row[3],
                    "precision": row[4],
                    "recall": row[5],
                    "activated_at": row[6].isoformat() if row[6] else None,
                    "storage_path": row[7],
                    "metadata": row[8],
                }
    finally:
        conn.close()
    return None


def list_models(limit: int = 20) -> list[dict]:
    """List registered models."""
    conn = _get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT version, roc_auc, cv_auc_mean, best_f1, status,
                       created_at, activated_at, storage_path
                FROM model_registry
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            return [
                {
                    "version": r[0],
                    "roc_auc": r[1],
                    "cv_auc_mean": r[2],
                    "best_f1": r[3],
                    "status": r[4],
                    "created_at": r[5].isoformat() if r[5] else None,
                    "activated_at": r[6].isoformat() if r[6] else None,
                    "storage_path": r[7],
                }
                for r in cur.fetchall()
            ]
    finally:
        conn.close()


def rollback_model(version: str | None = None, reason: str = "manual") -> dict | None:
    """Rollback to a specific version or the previous active one.

    Args:
        version: Target version to rollback to (None = previous active)
        reason: Reason for rollback (logged)

    Returns:
        Dict with rollback info or None on failure.
    """
    storage = get_storage()

    with _lock:
        conn = _get_pg_connection()
        try:
            conn.autocommit = False

            # Deactivate current active model
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT version FROM model_registry
                    WHERE status = 'active' ORDER BY activated_at DESC LIMIT 1
                """)
                current = cur.fetchone()
                if current:
                    cur.execute("""
                        UPDATE model_registry SET
                            status = 'rolled_back',
                            deactivated_at = now(),
                            rollback_reason = %s
                        WHERE version = %s
                    """, (reason, current[0]))

            # Determine target
            target = version
            if not target:
                # Find the most recent non-rolled-back model
                cur.execute("""
                    SELECT version FROM model_registry
                    WHERE status IN ('active', 'registered')
                      AND version != %s
                    ORDER BY activated_at DESC, created_at DESC
                    LIMIT 1
                """, (current[0] if current else "",))
                row = cur.fetchone()
                if row:
                    target = row[0]

            if not target:
                # Fallback: try storage rollback
                prev_name = storage.rollback_active()
                if prev_name:
                    print(f"[OK] Storage-level rollback to: {prev_name}")
                    return {"success": True, "target": prev_name, "reason": reason}
                conn.rollback()
                return {"success": False, "error": "No target version found for rollback"}

            # ── Step 1: Activate in storage FIRST (before DB commit) ──
            try:
                if storage.exists(target):
                    from core.config import MODEL_PATH
                    artifact = storage.load(target)
                    import joblib
                    joblib.dump(artifact, MODEL_PATH)
                else:
                    print(f"[WARN] Model {target} not in storage — using local file")
            except Exception as load_err:
                conn.rollback()
                return {"success": False, "error": f"Failed to load model {target}: {load_err}"}

            # ── Step 2: Swap in memory ──
            from core.state import safe_swap_model
            try:
                from core.config import MODEL_PATH
                swap_ok = safe_swap_model(MODEL_PATH)
                if not swap_ok:
                    conn.rollback()
                    return {"success": False, "error": "safe_swap_model failed"}
            except Exception as swap_err:
                conn.rollback()
                return {"success": False, "error": f"Memory swap failed: {swap_err}"}

            # ── Step 3: Rebuild caches ──
            try:
                from core.state import build_precomputed_caches
                build_precomputed_caches()
            except Exception as cache_err:
                print(f"[WARN] Cache rebuild after rollback: {cache_err}")

            # ── Step 4: Commit DB changes (now memory+storage already swapped) ──
            cur.execute("""
                UPDATE model_registry SET
                    status = 'active',
                    activated_at = now()
                WHERE version = %s
            """, (target,))

            conn.commit()

            print(f"[OK] Rollback to {target} (reason: {reason})")
            return {"success": True, "target": target, "previous": current[0] if current else None, "reason": reason}

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Rollback failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()


# ── Auto-rollback mechanism ──

_auto_rollback_scheduled = None
_auto_rollback_lock = threading.Lock()


def _schedule_auto_rollback(new_version: str, previous_version: str | None):
    """Schedule an auto-rollback check after AUTO_ROLLBACK_CHECK_DELAY seconds."""
    global _auto_rollback_scheduled

    def _check():
        time.sleep(AUTO_ROLLBACK_CHECK_DELAY)
        with _auto_rollback_lock:
            _check_and_rollback(new_version, previous_version)

    import threading
    t = threading.Thread(target=_check, daemon=True, name="auto-rollback-checker")
    t.start()
    with _auto_rollback_lock:
        _auto_rollback_scheduled = t
    print(f"[OK] Auto-rollback check scheduled for {AUTO_ROLLBACK_CHECK_DELAY}s")


def _check_and_rollback(new_version: str, previous_version: str | None):
    """Check if post-deploy metrics degraded. Rollback if threshold exceeded.

    This checks:
    1. AUC regression in production (compared to training AUC)
    2. Error rate increase (from audit log)
    """
    print(f"[AUTO-ROLLBACK] Checking metrics for {new_version}...")

    conn = _get_pg_connection()
    try:
        with conn.cursor() as cur:
            # Get training AUC for this model
            cur.execute("SELECT roc_auc FROM model_registry WHERE version = %s", (new_version,))
            row = cur.fetchone()
            if not row:
                print("[AUTO-ROLLBACK] Model not found in registry — skipping")
                return

            training_auc = row[0]
            if training_auc is None:
                print("[AUTO-ROLLBACK] No training AUC recorded — skipping")
                return

            # Get recent scores from production to estimate effective AUC
            # Approximation: check if average ml_score distribution shifted significantly
            cur.execute("""
                SELECT AVG(ml_score), STDDEV(ml_score), COUNT(*)
                FROM scores
                WHERE updated_at > now() - interval '%s seconds'
            """, (AUTO_ROLLBACK_WINDOW,))
            stats = cur.fetchone()

            if not stats or stats[2] is None or stats[2] == 0:
                print("[AUTO-ROLLBACK] No recent score data — skipping")
                return

            avg_score, stddev, count = stats
            print(f"  Recent scores: avg={avg_score:.4f}, stddev={stddev:.4f}, count={count}")

            # Check audit log for error rate
            cur.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN details::text LIKE '%"status":"error"%' THEN 1 ELSE 0 END) as errors
                FROM audit_log
                WHERE created_at > now() - interval '%s seconds'
            """, (AUTO_ROLLBACK_WINDOW,))
            audit = cur.fetchone()

            error_rate = 0
            if audit and audit[0] and audit[0] > 0:
                error_rate = (audit[1] or 0) / audit[0]
                print(f"  Audit: total={audit[0]}, errors={audit[1]}, error_rate={error_rate:.2%}")

            # Decision: rollback if error rate is abnormally high
            if error_rate > 0.5:
                print(f"  ⚠️  ERROR RATE {error_rate:.2%} > 50% — triggering rollback")
                result = rollback_model(previous_version, reason=f"auto_rollback_high_error_rate_{error_rate:.2%}")
                if result and result.get("success"):
                    print(f"  ✅ Auto-rollback completed: {result['target']}")
                else:
                    print(f"  ❌ Auto-rollback FAILED: {result}")
            else:
                print(f"  ✅ Auto-rollback check passed (error_rate={error_rate:.2%})")

    except Exception as e:
        print(f"[AUTO-ROLLBACK] Check failed: {e}")
    finally:
        conn.close()


def check_auto_rollback() -> dict:
    """Manually trigger auto-rollback check (for API endpoint)."""
    active = get_active_model()
    if not active:
        return {"status": "no_active_model"}

    return {
        "auto_rollback_enabled": AUTO_ROLLBACK_ENABLED,
        "auc_threshold": AUTO_ROLLBACK_AUC_THRESHOLD,
        "f1_threshold": AUTO_ROLLBACK_F1_THRESHOLD,
        "check_delay_seconds": AUTO_ROLLBACK_CHECK_DELAY,
        "observation_window_seconds": AUTO_ROLLBACK_WINDOW,
        "active_model": active["version"],
        "active_auc": active["roc_auc"],
    }
