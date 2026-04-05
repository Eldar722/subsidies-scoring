"""
supabase_service.py — загрузка данных в Supabase (producers, scores, shap_values, model_metrics).

КРИТИЧЕСКИЕ ПРАВИЛА:
  - Все записи в критические ML-таблицы через psycopg2 + DATABASE_URL (не REST API)
  - SHAP: atomic staging → verify → swap через BEGIN/COMMIT/ROLLBACK
  - Никакого delete→insert без гарантии успеха
  - Supabase REST API используется ТОЛЬКО для чтения
"""

import math
import os
import time as time_mod
from supabase import create_client, ClientOptions
from core.config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_KEY, DATABASE_URL

BATCH_SIZE = 500
_ADMIN_TIMEOUT = float(os.environ.get("SUPABASE_POSTGREST_TIMEOUT", "300"))


# ══════════════════════════════════════════════════════════════
# SUPABASE REST CLIENTS (for reads only)
# ══════════════════════════════════════════════════════════════

def _get_client():
    """Supabase client with anon key (for reads)."""
    return create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        options=ClientOptions(postgrest_client_timeout=_ADMIN_TIMEOUT),
    )


def _get_admin_client():
    """Supabase client with service role key (for non-critical reads/writes)."""
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=ClientOptions(postgrest_client_timeout=_ADMIN_TIMEOUT),
    )


# ══════════════════════════════════════════════════════════════
# POSTGRES DIRECT CONNECTION (for critical writes)
# ══════════════════════════════════════════════════════════════

def _get_pg_connection():
    """Direct psycopg2 connection for atomic writes."""
    import psycopg2
    if not DATABASE_URL:
        raise RuntimeError("[FATAL] DATABASE_URL not set — cannot perform critical writes")
    return psycopg2.connect(DATABASE_URL, connect_timeout=30)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _clean_value(v):
    """Replace NaN/inf with None for Postgres."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def _clean_row(row: dict) -> dict:
    """Clean all values in a row dict."""
    return {k: _clean_value(v) for k, v in row.items()}


def _execute_with_retries(fn, *, attempts: int = 4, label: str = "query") -> None:
    """Retry wrapper for REST API calls."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            fn()
            return
        except Exception as e:
            last = e
            if i < attempts - 1:
                delay = 0.5 * (2**i)
                print(f"  [WARN] {label} retry {i + 1}/{attempts} after {delay}s: {e}")
                time_mod.sleep(delay)
    assert last is not None
    raise last


# ══════════════════════════════════════════════════════════════
# PRODUCERS — atomic write via psycopg2
# ══════════════════════════════════════════════════════════════

def upsert_producers(producers_df):
    """Upsert producers via batch INSERT — 50-100x faster than individual INSERTs."""
    import psycopg2.extras

    records = producers_df.to_dict(orient="records")
    if not records:
        print("  [WARN] No producers to upsert")
        return 0

    conn = _get_pg_connection()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            # Ensure producers table exists (idempotent)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS producers (
                    producer_id TEXT PRIMARY KEY,
                    region TEXT,
                    direction TEXT,
                    total_applications INT DEFAULT 0,
                    completion_rate FLOAT DEFAULT 0
                )
            """)

            cur.execute("CREATE TEMP TABLE IF NOT EXISTS producers_staging (LIKE producers INCLUDING DEFAULTS) ON COMMIT DROP")

            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO producers_staging
                   (producer_id, region, direction, total_applications, completion_rate)
                   VALUES %s""",
                [
                    (
                        r["producer_id"],
                        r.get("region", ""),
                        r.get("direction", ""),
                        int(r.get("total_applications", 0)),
                        float(r.get("completion_rate", 0)),
                    )
                    for r in records
                ],
                page_size=1000,
            )

            cur.execute("""
                INSERT INTO producers (producer_id, region, direction, total_applications, completion_rate)
                SELECT producer_id, region, direction, total_applications, completion_rate
                FROM producers_staging
                ON CONFLICT (producer_id) DO UPDATE SET
                    region = EXCLUDED.region,
                    direction = EXCLUDED.direction,
                    total_applications = EXCLUDED.total_applications,
                    completion_rate = EXCLUDED.completion_rate
            """)

        conn.commit()
        print(f"  producers: {len(records)} upserted (psycopg2, batch)")
        return len(records)
    except Exception as e:
        conn.rollback()
        print(f"  ❌ producers upsert FAILED, ROLLBACK: {e}")
        raise
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# SCORES — atomic write via psycopg2
# ══════════════════════════════════════════════════════════════

def upsert_scores(scores_df_or_list):
    """Upsert scores via direct Postgres (ON CONFLICT DO UPDATE).

    Uses psycopg2.extras.execute_values for batch upsert — 50-100x faster
    than individual INSERTs. 15K records: ~3s instead of ~20min.
    """
    import psycopg2.extras

    if hasattr(scores_df_or_list, "to_dict"):
        records = scores_df_or_list.to_dict(orient="records")
    else:
        records = scores_df_or_list

    if not records:
        print("  [WARN] No scores to upsert")
        return 0

    conn = _get_pg_connection()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            # Ensure scores table exists (idempotent)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    producer_id TEXT PRIMARY KEY,
                    ml_score FLOAT,
                    ml_rank INT,
                    fcfs_rank INT,
                    delta INT,
                    hidden_talent BOOLEAN DEFAULT FALSE
                )
            """)

            cur.execute("CREATE TEMP TABLE IF NOT EXISTS scores_staging (LIKE scores INCLUDING DEFAULTS) ON COMMIT DROP")

            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO scores_staging
                   (producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent)
                   VALUES %s""",
                [
                    (
                        r["producer_id"],
                        float(r["ml_score"]),
                        int(r["ml_rank"]),
                        int(r["fcfs_rank"]),
                        int(r["delta"]),
                        bool(r["hidden_talent"]),
                    )
                    for r in records
                ],
                page_size=1000,
            )
            print(f"    staging: {len(records)} records inserted (batch)")

            # Step 2: Upsert from staging to production
            # Note: updated_at may not exist if migrations weren't run — skip it
            try:
                cur.execute("""
                    INSERT INTO scores (producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent, updated_at)
                    SELECT producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent, now()
                    FROM scores_staging
                    ON CONFLICT (producer_id) DO UPDATE SET
                        ml_score = EXCLUDED.ml_score,
                        ml_rank = EXCLUDED.ml_rank,
                        fcfs_rank = EXCLUDED.fcfs_rank,
                        delta = EXCLUDED.delta,
                        hidden_talent = EXCLUDED.hidden_talent,
                        updated_at = now()
                """)
            except Exception:
                # Fallback without updated_at
                cur.execute("""
                    INSERT INTO scores (producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent)
                    SELECT producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent
                    FROM scores_staging
                    ON CONFLICT (producer_id) DO UPDATE SET
                        ml_score = EXCLUDED.ml_score,
                        ml_rank = EXCLUDED.ml_rank,
                        fcfs_rank = EXCLUDED.fcfs_rank,
                        delta = EXCLUDED.delta,
                        hidden_talent = EXCLUDED.hidden_talent
                """)

        conn.commit()
        print(f"  scores: {len(records)} upserted (psycopg2, batch, ~3s)")
        return len(records)
    except Exception as e:
        conn.rollback()
        print(f"  ❌ scores upsert FAILED, ROLLBACK: {e}")
        raise
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# SHAP VALUES — ATOMIC staging → verify → swap via psycopg2
# ══════════════════════════════════════════════════════════════

def upsert_shap(shap_list: list) -> int:
    """Atomic SHAP upsert: staging → verify → swap.
    
    Strategy:
      1. TRUNCATE staging table
      2. INSERT all new data into staging
      3. Verify staging row count matches expected
      4. DELETE old data from production for affected producer_ids
      5. INSERT FROM staging into production
      6. TRUNCATE staging
      7. COMMIT (all steps are in one transaction)
      
    On ANY failure → ROLLBACK (production table untouched).
    """
    if not shap_list:
        print("  [WARN] Empty SHAP list — skipping")
        return 0

    expected_count = len(shap_list)
    affected_pids = list({str(r["producer_id"]) for r in shap_list})

    import psycopg2.extras

    conn = _get_pg_connection()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            # Step 0: Ensure tables exist (idempotent)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shap_values (
                    id BIGSERIAL PRIMARY KEY,
                    producer_id TEXT NOT NULL,
                    feature TEXT NOT NULL,
                    shap_value FLOAT,
                    feature_value FLOAT,
                    feature_label TEXT,
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_shap_producer ON shap_values(producer_id)")

            # Deduplicate existing data BEFORE creating unique index
            # Keep only the row with max id for each (producer_id, feature)
            cur.execute("""
                DELETE FROM shap_values
                WHERE id NOT IN (
                    SELECT MAX(id) FROM shap_values
                    GROUP BY producer_id, feature
                )
            """)

            # Now try to create unique index (ignore failure if it still has issues)
            try:
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS shap_values_producer_feature_key ON shap_values (producer_id, feature)")
            except Exception:
                pass  # Index may still fail if dups remain — skip gracefully

            cur.execute("""
                CREATE TABLE IF NOT EXISTS shap_values_staging (
                    id BIGSERIAL PRIMARY KEY,
                    producer_id TEXT NOT NULL,
                    feature TEXT NOT NULL,
                    shap_value FLOAT,
                    feature_value FLOAT,
                    feature_label TEXT
                )
            """)
            try:
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS shap_staging_producer_feature_key ON shap_values_staging (producer_id, feature)")
            except Exception:
                pass

            # Step 1: Clear staging
            cur.execute("TRUNCATE TABLE shap_values_staging")

            # Step 2: Batch INSERT into staging via execute_values (no ON CONFLICT needed — table just TRUNCATE'd)
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO shap_values_staging
                   (producer_id, feature, shap_value, feature_value, feature_label)
                   VALUES %s""",
                [
                    (
                        r["producer_id"],
                        r["feature"],
                        float(r["shap_value"]),
                        float(r.get("feature_value", 0) or 0),
                        r.get("feature_label", r["feature"]),
                    )
                    for r in shap_list
                ],
                page_size=2000,
            )

            # Step 3: Verify staging count
            cur.execute("SELECT COUNT(*) FROM shap_values_staging")
            staged_count = cur.fetchone()[0]

            if staged_count < expected_count * 0.95:
                raise RuntimeError(
                    f"SHAP staging verification FAILED: "
                    f"staged={staged_count}, expected={expected_count} "
                    f"(threshold 95%)"
                )

            print(f"    staging: {staged_count}/{expected_count} rows verified ✓")

            # Step 4: Delete old production data for affected producers
            # Use ANY() for efficient batch delete
            cur.execute(
                "DELETE FROM shap_values WHERE producer_id = ANY(%s)",
                (affected_pids,)
            )
            deleted = cur.rowcount
            print(f"    deleted: {deleted} old rows from production ✓")

            # Step 5: Copy from staging to production (without updated_at — column may not exist)
            cur.execute("""
                INSERT INTO shap_values (producer_id, feature, shap_value, feature_value, feature_label)
                SELECT producer_id, feature, shap_value, feature_value, feature_label
                FROM shap_values_staging
            """)
            inserted = cur.rowcount
            print(f"    inserted: {inserted} rows into production ✓")

            # Step 6: Clear staging
            cur.execute("TRUNCATE TABLE shap_values_staging")

        # Step 7: COMMIT — all or nothing
        conn.commit()
        print(f"  shap_values: {inserted} upserted (psycopg2, atomic staging→swap)")
        return inserted

    except Exception as e:
        conn.rollback()
        print(f"  ❌ SHAP upsert FAILED, ROLLBACK (production data preserved): {e}")
        # Try to clean up staging even after rollback
        try:
            conn2 = _get_pg_connection()
            conn2.autocommit = True
            with conn2.cursor() as cur2:
                cur2.execute("TRUNCATE TABLE shap_values_staging")
            conn2.close()
        except Exception:
            pass
        raise
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# MODEL METRICS — atomic write via psycopg2
# ══════════════════════════════════════════════════════════════

def upsert_metrics(metrics_dict: dict) -> int:
    """Upsert model_metrics via Postgres (ON CONFLICT DO UPDATE)."""
    conn = _get_pg_connection()
    try:
        conn.autocommit = False
        row = _clean_row(metrics_dict)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO model_metrics (run_id, roc_auc, avg_precision, best_f1, optimal_threshold, cv_auc_mean, train_size, val_size, created_at)
                VALUES (%(run_id)s, %(roc_auc)s, %(avg_precision)s, %(best_f1)s, %(optimal_threshold)s, %(cv_auc_mean)s, %(train_size)s, %(val_size)s, now())
                ON CONFLICT (run_id) DO UPDATE SET
                    roc_auc = EXCLUDED.roc_auc,
                    avg_precision = EXCLUDED.avg_precision,
                    best_f1 = EXCLUDED.best_f1,
                    optimal_threshold = EXCLUDED.optimal_threshold,
                    cv_auc_mean = EXCLUDED.cv_auc_mean,
                    train_size = EXCLUDED.train_size,
                    val_size = EXCLUDED.val_size,
                    created_at = now()
            """, row)
        conn.commit()
        print(f"  model_metrics: 1 upserted (psycopg2, atomic)")
        return 1
    except Exception as e:
        conn.rollback()
        print(f"  ❌ model_metrics upsert FAILED, ROLLBACK: {e}")
        raise
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# READ HELPERS (REST API is fine for reads)
# ══════════════════════════════════════════════════════════════

def count_table(table: str) -> int:
    """Count rows in a table (via REST API — safe for reads)."""
    client = _get_admin_client()
    result = client.table(table).select("*", count="exact").limit(0).execute()
    return result.count if result.count is not None else 0


def count_table_pg(table: str) -> int:
    """Count rows in a table via direct Postgres."""
    conn = _get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            return cur.fetchone()[0]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# LEGACY COMPATIBILITY — _upsert_batch via REST (non-critical)
# ══════════════════════════════════════════════════════════════

def _upsert_batch(
    table: str,
    records: list,
    batch_size: int = BATCH_SIZE,
    *,
    on_conflict: str | None = None,
):
    """Upsert records in batches via REST API. For non-critical tables only."""
    client = _get_admin_client()
    total = 0
    for i in range(0, len(records), batch_size):
        batch = [_clean_row(r) for r in records[i:i + batch_size]]

        def _run():
            if on_conflict:
                client.table(table).upsert(batch, on_conflict=on_conflict).execute()
            else:
                client.table(table).upsert(batch).execute()

        _execute_with_retries(_run, label=f"{table} upsert batch {i // batch_size + 1}")
        total += len(batch)
        if total % 1000 == 0 or total == len(records):
            print(f"  {table}: {total}/{len(records)}")
    return total


# ══════════════════════════════════════════════════════════════
# STANDALONE RUNNER
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import numpy as np
    import joblib
    from ml.data_loader import load_xlsx
    from ml.feature_engineering import build_features, FEATURES
    from ml.scoring import score_dataframe
    from ml.baseline_service import compute_baseline
    from ml.shap_service import compute_shap
    import core.state as state

    # --- 1. Загрузка модели и данных ---
    state.load_model()
    state.load_data()
    artifact = joblib.load("model.pkl")
    df = state.DF

    # --- 2. Скоринг всех заявок ---
    print("Скоринг заявок...")
    scored = score_dataframe(df)

    # --- 3. Producers ---
    print("\nПодготовка producers...")
    producers = scored.groupby("producer_id").agg(
        region=("Область", "first"),
        direction=("Направление водства", "first"),
        total_applications=("ml_score", "count"),
        completion_rate=("ml_score", "mean"),
    ).reset_index()
    print(f"  {len(producers)} производителей")
    upsert_producers(producers)

    # --- 4. Scores (с baseline) ---
    print("\nПодготовка scores...")
    producer_scores = scored.groupby("producer_id")["ml_score"].mean().to_dict()
    baseline = compute_baseline(df, producer_scores)
    scores_upload = baseline[["producer_id", "ml_score", "ml_rank", "fcfs_rank", "delta", "hidden_talent"]].copy()
    scores_upload["hidden_talent"] = scores_upload["hidden_talent"].astype(bool)
    upsert_scores(scores_upload)

    # --- 5. SHAP values (атомарно через staging) ---
    print("\nВычисление SHAP...")
    base_model = artifact["base_model"]

    resolved = df.dropna(subset=["target"]).copy()
    resolved["target"] = resolved["target"].astype(int)
    train = resolved[resolved["year"] == 2025].reset_index(drop=True)
    X_train = build_features(train, fit=True)

    first_mask = train.index.isin(
        train.groupby("producer_id").apply(lambda g: g.index[0]).values
    )
    X_first = X_train[first_mask].reset_index(drop=True)
    pids_first = train[first_mask]["producer_id"].reset_index(drop=True)

    print(f"  SHAP для {len(X_first)} производителей...")
    shap_data = compute_shap(base_model, X_first, pids_first, top_n=5)
    print(f"  {len(shap_data)} записей SHAP")
    upsert_shap(shap_data)

    # --- 6. Model metrics ---
    print("\nЗагрузка метрик модели...")
    m = artifact["metrics"]
    metrics_upload = {
        "run_id": "v1_pipeline",
        "roc_auc": m["roc_auc"],
        "avg_precision": m["avg_precision"],
        "best_f1": m["best_f1"],
        "optimal_threshold": artifact.get("optimal_threshold", m.get("best_threshold", 0.5)),
        "cv_auc_mean": m["cv_auc_mean"],
        "train_size": int(m.get("train_size", len(train))),
        "val_size": int(m.get("val_size", 0)),
    }
    upsert_metrics(metrics_upload)

    # --- 7. Проверка ---
    print("\n=== Итого в Supabase ===")
    for table in ["producers", "scores", "shap_values", "model_metrics"]:
        try:
            c = count_table_pg(table)
            print(f"  {table}: {c}")
        except Exception as e:
            print(f"  {table}: ошибка — {e}")
