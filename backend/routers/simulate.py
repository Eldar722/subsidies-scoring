from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
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

@router.post("/simulate")
def simulate(body: SimulateRequest):
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
    
    # Так как ML компонента ml/simulator_service.py пока не существует, будем эмулировать логику
    # с помощью полного базового скоринга (baseline), смещая выборку (offset) для имитации перестроения.
    
    # 1. Получаем базу всех продюсеров (Оригинальная ситуация без весов)
    all_res = compute_shortlist(state.DF, top_n=len(state.DF))
    all_items = all_res.get("shortlist", []) if all_res else []
    
    if len(all_items) < body.top_n:
        final_list = all_items
        entered = []
        left = []
    else:
        # Оригинальный "честный" шортлист (baseline)
        original_shortlist = all_items[:body.top_n]
        original_ids = {p["producer_id"] for p in original_shortlist}
        
        # Симулированный шортлист с "влиянием" весов.
        # В качестве мок-заглушки: сдвигаем индекс старта списка в зависимости от веса 'diversity'.
        # Это выбьет часть старых производителей (left) и закинет случайных новых (entered).
        offset = int((norm_w["diversity"] + norm_w["activity"]) * 10) 
        
        # Защита от выхода за границы массива
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
