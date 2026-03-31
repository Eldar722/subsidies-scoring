from fastapi import APIRouter, HTTPException
from cachetools import TTLCache
import core.state as state
from ml.fairness import compute_fairness_report

router = APIRouter()

# Кэш на 1 час (3600 секунд)
fairness_cache = TTLCache(maxsize=1, ttl=3600)


@router.get("/fairness")
def fairness():
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")
        
    cache_key = "fairness_report"
    if cache_key in fairness_cache:
        return fairness_cache[cache_key]
        
    report = compute_fairness_report(state.DF)
    fairness_cache[cache_key] = report
    return report
