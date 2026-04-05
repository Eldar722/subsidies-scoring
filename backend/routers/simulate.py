"""
simulate.py — weighted score simulation with custom weights.
Rate limit: COMPUTE (20/min) — recalculates scores.
"""

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import Optional
from core.rate_limits import limiter, COMPUTE
from ml.simulator_service import simulate, DEFAULT_WEIGHTS
import core.state as state

router = APIRouter()


class SimulationWeights(BaseModel):
    completion_rate: float = 35
    approval_rate: float = 25
    # Поддерживаем оба ключа: diversification (frontend) и diversity (старый)
    diversification: Optional[float] = None
    diversity: Optional[float] = None
    activity: float = 10
    working_hours: float = 10

    def get_diversity(self) -> float:
        """Получить значение диверсификации из любого из двух ключей."""
        if self.diversification is not None:
            return self.diversification
        if self.diversity is not None:
            return self.diversity
        return 20.0


class SimulateRequest(BaseModel):
    weights: SimulationWeights
    top_n: int = 20


@router.get("/simulate")
@limiter.limit(COMPUTE)
def run_simulation(
    request: Request,
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
@limiter.limit(COMPUTE)
def run_simulation_post(request: Request, body: SimulateRequest):
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")
    if state.MODEL_DATA is None:
        raise HTTPException(503, "Модель не загружена. Запустите пайплайн.")

    w = body.weights
    diversity_val = w.get_diversity()

    # Map frontend keys → simulator_service keys
    sim_weights = {
        "completion_rate": w.completion_rate,
        "approval_rate": w.approval_rate,
        "direction_diversity": diversity_val,
        "apps_per_month": w.activity,
        "working_hours": w.working_hours,
    }

    try:
        result = simulate(sim_weights, top_n=body.top_n)
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    return result
