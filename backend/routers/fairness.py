from fastapi import APIRouter, HTTPException
import core.state as state
from ml.fairness import compute_fairness_report

router = APIRouter()


@router.get("/fairness")
def fairness():
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")
    return compute_fairness_report(state.DF)
