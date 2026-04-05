"""
sync_to_supabase.py — Обновление Supabase после обучения модели.

Использует psycopg2 для атомарных записей (не REST API).
Все операции: producers → scores → SHAP (staging→swap) → metrics.
"""


def _sync_producers_and_shap(df, model_data):
    """Producers + SHAP в Supabase после обучения (atomic via psycopg2)."""
    import core.state as state
    from ml.scoring import score_dataframe
    from ml.feature_engineering import build_features
    from ml.shap_service import compute_shap
    from services.supabase_service import upsert_producers, upsert_shap

    print("\n  [STEP 6] Syncing producers + SHAP (atomic psycopg2)...")
    state.MODEL_DATA = model_data
    state.DF = df
    state.GROUP_STATS = None

    scored = score_dataframe(df)
    producers = scored.groupby("producer_id").agg(
        region=("Область", "first"),
        direction=("Направление водства", "first"),
        total_applications=("ml_score", "count"),
        completion_rate=("ml_score", "mean"),
    ).reset_index()
    upsert_producers(producers)
    print(f"    ✓ Producers upserted: {len(producers)}")

    base_model = model_data["base_model"]
    resolved = df.dropna(subset=["target"]).copy()
    resolved["target"] = resolved["target"].astype(int)
    train = resolved[resolved["year"] == 2025].reset_index(drop=True)
    if len(train) == 0:
        print("    [WARN] Нет строк 2025 для SHAP — пропуск")
        return

    X_train = build_features(train, fit=True)
    first_mask = train.index.isin(
        train.groupby("producer_id").apply(lambda g: g.index[0]).values
    )
    X_first = X_train[first_mask].reset_index(drop=True)
    pids_first = train[first_mask]["producer_id"].reset_index(drop=True)
    shap_data = compute_shap(base_model, X_first, pids_first, top_n=5)
    
    # Atomic SHAP upsert via staging table
    upsert_shap(shap_data)
    print(f"    ✓ SHAP upserted (atomic): {len(shap_data)} rows")


def sync_scores_to_supabase(df, model_data):
    """After training, update Supabase with new scores and hidden_talent.
    
    All writes go through psycopg2 with BEGIN/COMMIT/ROLLBACK.
    """
    print("\n📊 Syncing scores to Supabase (atomic psycopg2)...")
    print(f"  Input DataFrame shape: {df.shape}")
    print(f"  Input producers: {df['producer_id'].nunique() if 'producer_id' in df.columns else 'N/A'}")
    
    try:
        import core.state as state
        from ml.baseline import compute_shortlist
        from services.supabase_service import upsert_scores
        
        # Set model and data in global state
        print("  [STEP 1] Setting state...")
        state.MODEL_DATA = model_data
        state.DF = df
        state.GROUP_STATS = None
        
        # Compute all scores
        print("  [STEP 2] Computing shortlist...")
        result = compute_shortlist(df, top_n=len(df))
        
        if not result or "shortlist" not in result:
            print("[ERROR] compute_shortlist returned invalid result")
            return False
        
        shortlist = result["shortlist"]
        if len(shortlist) == 0:
            print("[WARN] Shortlist is empty")
            return False
        
        print(f"    ✓ Computed {len(shortlist)} producer scores")
        
        # Transform to records
        records = []
        for item in shortlist:
            records.append({
                "producer_id": item["producer_id"],
                "ml_score": float(item["ml_score"]),
                "ml_rank": int(item["ml_rank"]),
                "fcfs_rank": int(item["fcfs_rank"]),
                "delta": int(item["delta"]),
                "hidden_talent": bool(item["hidden_talent"]),
            })
        
        # Atomic upsert via psycopg2
        print(f"  [STEP 3] Upserting {len(records)} scores (psycopg2, atomic)...")
        upsert_scores(records)
        
        print(f"\n  [STEP 4] Syncing producers + SHAP...")
        try:
            _sync_producers_and_shap(df, model_data)
        except Exception as shap_err:
            print(f"\n  ❌ Producers/SHAP sync failed (scores OK): {shap_err}")
            import traceback
            traceback.print_exc()
            # Scores are already committed — partial success is better than total failure
            return True

        print(f"\n✅ SYNC COMPLETE: {len(records)} scores written to Supabase")
        return True
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR in sync_scores_to_supabase:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
