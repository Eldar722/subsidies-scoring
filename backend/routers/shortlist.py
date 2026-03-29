from fastapi import APIRouter, HTTPException
import core.state as state
from ml.baseline import compute_shortlist

router = APIRouter()


@router.get("/shortlist")
def shortlist(top_n: int = 20):
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")

    result = compute_shortlist(state.DF, top_n)
    if result is None:
        raise HTTPException(500, "Нет данных для скоринга")
    return result
