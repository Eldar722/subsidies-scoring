"""
sync_to_supabase.py — Обновление Supabase scores таблицы после обучения модели.

Использует compute_shortlist для получения производителей с ml_score, ranks, hidden_talent.
Затем upsert в Supabase для фронтенда.
"""

def sync_scores_to_supabase(df, model_data):
    """After training, update Supabase with new scores and hidden_talent.
    
    Args:
        df: DataFrame с train/val данными
        model_data: Загруженная модель (не используется, но для API консистентности)
    """
    print("\n📊 Syncing scores to Supabase...")
    
    try:
        from ml.baseline import compute_shortlist
        from services.supabase_service import _get_client
        
        # Compute all scores + hidden_talent
        result = compute_shortlist(df, top_n=len(df))
        if not result or "shortlist" not in result:
            print("[WARN] compute_shortlist returned empty")
            return False
        
        shortlist = result["shortlist"]
        if len(shortlist) == 0:
            print("[WARN] Shortlist is empty")
            return False
        
        print(f"  Computed {len(shortlist)} producer scores")
        
        # Connect to Supabase
        client = _get_client()
        
        # Batch upsert (Supabase: ~1000/sec rate limit)
        batch_size = 100
        success_count = 0
        
        for i in range(0, len(shortlist), batch_size):
            batch = shortlist[i:i+batch_size]
            
            try:
                # Transform to Supabase format
                records = []
                for item in batch:
                    records.append({
                        "producer_id": item["producer_id"],
                        "ml_score": float(item["ml_score"]),
                        "ml_rank": int(item["ml_rank"]),
                        "fcfs_rank": int(item["fcfs_rank"]),
                        "delta": int(item["delta"]),
                        "hidden_talent": bool(item["hidden_talent"]),
                    })
                
                # Upsert to Supabase (insert or update if exists)
                client.table("scores").upsert(records, ignore_duplicates=False).execute()
                success_count += len(batch)
                print(f"  ✓ Synced {i+len(batch)}/{len(shortlist)}")
                
            except Exception as e:
                print(f"  ⚠ Error upserting batch {i//batch_size}: {e}")
                continue
        
        print(f"✅ Synced {success_count} scores to Supabase")
        return True
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False
