"""
shortlist.py — топ-N производителей.
Источник данных: Supabase (scores + producers таблицы).
Fallback на in-memory state.DF если Supabase недоступен.

Rate limit: COMPUTE (20/min) — triggers ML scoring.
"""

from fastapi import APIRouter, HTTPException, Request
from cachetools import TTLCache
from core.rate_limits import limiter, COMPUTE
from services.supabase_service import _get_client
import core.state as state

router = APIRouter()

# Кэш на 5 минут
_cache = TTLCache(maxsize=10, ttl=300)


def _fetch_shortlist_from_db(top_n: int) -> dict:
    """Получить shortlist из Supabase (scores JOIN producers)."""
    try:
        # Use admin client for backend reads to bypass RLS
        # (Frontend anon key is blocked by RLS policy)
        from services.supabase_service import _get_admin_client
        client = _get_admin_client()

        print(f"[DEBUG] Attempting to query Supabase scores table...")
        
        # 1. Топ-N scores отсортированных по ml_score
        # Сначала проверим, есть ли вообще данные в таблице
        initial_check = (
            client.table("scores")
            .select("*", count="exact")
            .limit(0)
            .execute()
        )
        print(f"[DEBUG] Total rows in scores table: {initial_check.count}")
        
        if initial_check.count == 0:
            print(f"[ERROR] Scores table is completely empty!")
            print(f"[HINT] Have you run: python train.py && python -m services.supabase_service?")
            return {"shortlist": [], "total": 0, "hidden_talent_count": 0}
        
        # Теперь получим сами данные
        scores_resp = (
            client.table("scores")
            .select("producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent")
            .order("ml_score", desc=True)
            .limit(top_n)
            .execute()
        )
        
        scores = scores_resp.data or []
        
        print(f"[DEBUG] Ordered Supabase scores query returned {len(scores)} rows")
        if len(scores) == 0 and initial_check.count > 0:
            print(f"[WARNING] Table has {initial_check.count} rows but filtered query returned 0")
            print(f"[DEBUG] Full response: {scores_resp}")
        
        if not scores:
            return {"shortlist": [], "total": 0, "hidden_talent_count": 0}

        # 2. Подтягиваем данные producers для этих ID
        pids = [s["producer_id"] for s in scores]
        prod_resp = (
            client.table("producers")
            .select("producer_id, region, direction, total_applications, completion_rate")
            .in_("producer_id", pids)
            .execute()
        )
        producers_map = {p["producer_id"]: p for p in (prod_resp.data or [])}

        # 3. Объединяем
        items = []
        for s in scores:
            p = producers_map.get(s["producer_id"], {})
            ml_score = s.get("ml_score") or 0
            delta = s.get("delta") or 0
            items.append({
                "producer_id": s["producer_id"],
                "ml_score": round(float(ml_score), 4),
                "ml_rank": s.get("ml_rank"),
                "fcfs_rank": s.get("fcfs_rank"),
                "delta": delta,
                "hidden_talent": bool(s.get("hidden_talent", False)),
                "at_risk": delta < -10,
                "region": p.get("region"),
                "direction": p.get("direction"),
                "total_applications": p.get("total_applications"),
                "completion_rate": p.get("completion_rate"),
            })

        print(f"[DEBUG] Successfully joined {len(items)} items from Supabase")
        return {
            "shortlist": items,
            "total": len(items),
            "hidden_talent_count": sum(1 for i in items if i.get("hidden_talent")),
        }
    except Exception as e:
        # If Supabase fails, let the fallback handle it
        error_msg = str(e).lower()
        print(f"[ERROR] Supabase query failed: {type(e).__name__}: {e}")
        if "invalid" in error_msg or "unauthorized" in error_msg or "api key" in error_msg:
            print(f"[WARN] Supabase API key error in shortlist: {e}")
        elif "rls" in error_msg or "policy" in error_msg:
            print(f"[WARN] RLS policy may be blocking access: {e}")
        raise


def get_shortlist_cached(top_n: int = 20) -> dict:
    """Shortlist с кэшированием — вызывается из других роутеров."""
    cache_key = f"shortlist_{top_n}"
    if cache_key in _cache:
        return _cache[cache_key]
    try:
        result = _fetch_shortlist_from_db(top_n)
        if result and result.get("shortlist"):
            _cache[cache_key] = result
            return result
        # If Supabase returned empty, use fallback
        print(f"[INFO] Supabase returned empty, using in-memory fallback")
        result = _fallback_shortlist(top_n)
        _cache[cache_key] = result
        return result
    except Exception as e:
        print(f"[WARN] Supabase shortlist failed: {e}, fallback to in-memory")
        result = _fallback_shortlist(top_n)
        _cache[cache_key] = result
        return result


def _fallback_shortlist(top_n: int) -> dict:
    """Fallback: вычислить из state.DF если Supabase недоступен."""
    if state.DF is None:
        print("[WARN] state.DF is None - no data available")
        return {"shortlist": [], "total": 0, "hidden_talent_count": 0}
    try:
        from ml.baseline import compute_shortlist
        result = compute_shortlist(state.DF, top_n=top_n)
        if result and result.get("shortlist"):
            print(f"[OK] Loaded {len(result['shortlist'])} items from in-memory")
            return result
        else:
            print("[WARN] compute_shortlist returned empty")
            return {"shortlist": [], "total": 0, "hidden_talent_count": 0}
    except Exception as e:
        print(f"[ERROR] Fallback failed: {e}")
        return {"shortlist": [], "total": 0, "hidden_talent_count": 0}


@router.get("/shortlist")
@limiter.limit(COMPUTE)
def shortlist(request: Request, top_n: int = 20):
    result = get_shortlist_cached(top_n)
    # Return the result even if empty - don't raise 503
    # The frontend will handle empty lists gracefully
    return {
        "shortlist": result.get("shortlist", []),
        "total": result.get("total_producers", len(result.get("shortlist", []))),
        "hidden_talent_count": result.get("hidden_talent_count", 0),
        "source": "in-memory"  # We're using in-memory data from state.DF
    }
