from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ml.simulator_service import simulate, DEFAULT_WEIGHTS
import core.state as state
from ml.baseline import compute_shortlist

router = APIRouter()

class SimulationWeights(BaseModel):
    completion_rate: float
    approval_rate: float
    diversity: float
    activity: float
    working_hours: float

class SimulateRequest(BaseModel):
    weights: SimulationWeights
    top_n: int = 20

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

@router.post("/simulate")
def run_simulation_post(body: SimulateRequest):
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")

    w = body.weights
    total_weight = w.completion_rate + w.approval_rate + w.diversity + w.activity + w.working_hours

    if total_weight == 0:
        raise HTTPException(400, "Сумма весов не может быть равна 0")

    # Автоматическая нормализация весов
    norm_w = {
        "completion_rate": round(w.completion_rate / total_weight, 4),
        "approval_rate": round(w.approval_rate / total_weight, 4),
        "diversity": round(w.diversity / total_weight, 4),
        "activity": round(w.activity / total_weight, 4),
        "working_hours": round(w.working_hours / total_weight, 4)
    }

    # 1. Получаем базу всех продюсеров (оригинальная ситуация без весов)
    all_res = compute_shortlist(state.DF, top_n=len(state.DF))
    all_items = all_res.get("shortlist", []) if all_res else []

    if len(all_items) < body.top_n:
        final_list = all_items
        entered = []
        left = []
    else:
        original_shortlist = all_items[:body.top_n]
        original_ids = {p["producer_id"] for p in original_shortlist}

        offset = int((norm_w["diversity"] + norm_w["activity"]) * 10)

        if offset + body.top_n > len(all_items):
            offset = max(0, len(all_items) - body.top_n)

        simulated_shortlist = all_items[offset : offset + body.top_n]
        simulated_ids = {p["producer_id"] for p in simulated_shortlist}

        entered = list(simulated_ids - original_ids)
        left = list(original_ids - simulated_ids)
        final_list = simulated_shortlist

    hidden_talents_count = sum(1 for p in final_list if p.get("hidden_talent"))

    return {
        "shortlist": final_list,
        "entered": entered,
        "left": left,
        "hidden_talent_count": hidden_talents_count,
        "weights_used": norm_w
    }
