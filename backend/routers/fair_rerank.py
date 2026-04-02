from fastapi import APIRouter, HTTPException, Query
import core.state as state
from ml.scoring import score_dataframe
from ml.fair_reranker import compute_fair_shortlist
from routers.shortlist import get_shortlist_cached

router = APIRouter()


@router.get("/shortlist/fair")
def fair_shortlist(
    group_by: str = Query("region", regex="^(region|direction)$"),
    top_n: int = Query(20, ge=5, le=100),
    tolerance: float = Query(0.5, ge=0, le=2),
):
    if state.DF is None or state.MODEL_DATA is None:
        raise HTTPException(503, "Data or model not loaded")

    try:
        scored = score_dataframe(state.DF)
        producers = scored.groupby("producer_id").agg(
            ml_score=("ml_score", "mean"),
            region=("Область", "first"),
            direction=("Направление водства", "first"),
        ).reset_index()

        return compute_fair_shortlist(
            producers, score_col="ml_score",
            group_col=group_by, top_n=top_n, tolerance=tolerance,
        )
    except Exception as e:
        # Fallback: return regular shortlist от fair weighting
        print(f"[WARN] Fair rerank failed: {e}, using fallback shortlist")
        return get_shortlist_cached(top_n)
