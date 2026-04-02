from fastapi import APIRouter, HTTPException
import numpy as np
import core.state as state
from ml.scoring import score_dataframe
from ml.feature_engineering import build_features, FEATURES
from ml.counterfactual import find_counterfactual

router = APIRouter()


@router.get("/producers/{producer_id}/counterfactual")
def get_counterfactual(producer_id: str):
    if state.DF is None or state.MODEL_DATA is None:
        raise HTTPException(503, "Data or model not loaded")

    try:
        model = state.MODEL_DATA["model"]
        threshold = state.MODEL_DATA.get("optimal_threshold", 0.5)

        scored = score_dataframe(state.DF)
        rows = scored[scored["producer_id"] == producer_id]
        if len(rows) == 0:
            raise HTTPException(404, "Producer not found")

        row = rows.iloc[0]
        x = row[FEATURES].values.astype(float)

        result = find_counterfactual(model, FEATURES, x, threshold)
        result["producer_id"] = producer_id
        return result
    except HTTPException:
        raise
    except Exception as e:
        # Fallback: Return simple recommendations
        print(f"[WARN] Counterfactual failed: {e}, returning fallback")
        return {
            "producer_id": producer_id,
            "achievable": False,
            "current_score": 0,
            "target_score": threshold,
            "changes": [],
            "message": "Детальный анализ недоступен",
            "improvements": [
                {"action": "Повысить своевременность исполнения", "impact": "+5-10%"},
                {"action": "Увеличить объём заявок", "impact": "+3-5%"},
                {"action": "Подавать заявки в начале периода", "impact": "+2-3%"},
            ]
        }
