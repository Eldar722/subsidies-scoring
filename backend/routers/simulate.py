from fastapi import APIRouter, HTTPException, Query
from ml.simulator_service import simulate, DEFAULT_WEIGHTS

router = APIRouter()


@router.get("/simulate")
def run_simulation(
    completion_rate: float = Query(DEFAULT_WEIGHTS["completion_rate"]),
    approval_rate: float = Query(DEFAULT_WEIGHTS["approval_rate"]),
    direction_diversity: float = Query(DEFAULT_WEIGHTS["direction_diversity"]),
    apps_per_month: float = Query(DEFAULT_WEIGHTS["apps_per_month"]),
    working_hours: float = Query(DEFAULT_WEIGHTS["working_hours"]),
    top_n: int = Query(20, ge=5, le=100),
):
    try:
        weights = {
            "completion_rate": completion_rate,
            "approval_rate": approval_rate,
            "direction_diversity": direction_diversity,
            "apps_per_month": apps_per_month,
            "working_hours": working_hours,
        }
        return simulate(weights, top_n=top_n)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
