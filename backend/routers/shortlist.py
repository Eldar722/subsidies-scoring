"""
shortlist.py — топ-N производителей.
Источник данных: Supabase (scores + producers таблицы).
Fallback на in-memory state.DF если Supabase недоступен.
"""

from fastapi import APIRouter, HTTPException
from cachetools import TTLCache
from services.supabase_service import _get_client
import core.state as state

router = APIRouter()

# Кэш на 5 минут
_cache = TTLCache(maxsize=10, ttl=300)


def _fetch_shortlist_from_db(top_n: int) -> dict:
    """Получить shortlist из Supabase (scores JOIN producers)."""
    client = _get_client()

    # 1. Топ-N scores отсортированных по ml_score
    scores_resp = (
        client.table("scores")
        .select("producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent")
        .order("ml_score", desc=True)
        .limit(top_n)
        .execute()
    )
    scores = scores_resp.data or []
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

    return {
        "shortlist": items,
        "total": len(items),
        "hidden_talent_count": sum(1 for i in items if i.get("hidden_talent")),
    }


def get_shortlist_cached(top_n: int = 20) -> dict:
    """Shortlist с кэшированием — вызывается из других роутеров."""
    cache_key = f"shortlist_{top_n}"
    if cache_key in _cache:
        return _cache[cache_key]
    try:
        result = _fetch_shortlist_from_db(top_n)
        _cache[cache_key] = result
        return result
    except Exception as e:
        print(f"[WARN] Supabase shortlist failed: {e}, fallback to in-memory")
        return _fallback_shortlist(top_n)


def _fallback_shortlist(top_n: int) -> dict:
    """Fallback: вычислить из state.DF если Supabase недоступен."""
    if state.DF is None:
        return {"shortlist": [], "total": 0, "hidden_talent_count": 0}
    from ml.baseline import compute_shortlist
    result = compute_shortlist(state.DF, top_n=top_n)
    return result or {"shortlist": [], "total": 0, "hidden_talent_count": 0}


@router.get("/shortlist")
def shortlist(top_n: int = 20):
    result = get_shortlist_cached(top_n)
    if not result or not result.get("shortlist"):
        raise HTTPException(503, "Нет данных для шортлиста")
    return result
