"""
counterfactual.py — counterfactual explanations for producers.
Rate limit: COMPUTE (20/min)

Response adapter: translates backend keys → frontend-expected keys.
"""

from fastapi import APIRouter, HTTPException, Request
import numpy as np
from core.rate_limits import limiter, COMPUTE
import core.state as state
from ml.scoring import score_dataframe
from ml.feature_engineering import build_features, FEATURES
from ml.counterfactual import find_counterfactual

router = APIRouter()

# ── Feature display names for counterfactual recommendations ──
_FEATURE_NAMES_RU = {
    "month": "Месяц подачи",
    "hour": "Час подачи",
    "day_of_year": "День года",
    "day_of_week": "День недели",
    "Норматив": "Норматив",
    "Причитающая сумма": "Сумма",
    "amount_to_norm": "Сумма / Норматив",
    "log_amount": "Логарифм суммы",
    "log_norm": "Логарифм норматива",
    "region_enc": "Регион",
    "direction_enc": "Направление",
    "subsidy_enc": "Тип субсидии",
}


def _format_value(feature: str, val) -> str:
    """Human-readable value formatting."""
    if feature in ("month", "hour", "day_of_year", "day_of_week", "region_enc", "direction_enc", "subsidy_enc"):
        return str(int(round(val)))
    return f"{val:.2f}"


def _make_recommendation(feature: str, old_val, new_val, impact: float) -> dict:
    """Build a frontend-friendly recommendation dict."""
    display_name = _FEATURE_NAMES_RU.get(feature, feature)
    old_str = _format_value(feature, old_val)
    new_str = _format_value(feature, new_val)
    impact_pct = int(round(abs(impact) * 100))

    # Build explanation text
    direction = "увеличить" if new_val > old_val else "уменьшить"
    explanation = f"Попробуйте {direction} «{display_name}» с {old_str} до {new_str}"

    return {
        "feature": display_name,
        "feature_key": feature,
        "impact_pct": impact_pct,
        "current": old_str,
        "recommended": new_str,
        "explanation": explanation,
    }


@router.get("/producers/{producer_id}/counterfactual")
@limiter.limit(COMPUTE)
def get_counterfactual(request: Request, producer_id: str):
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

        # ── Adapt response for frontend compatibility ──
        adapted_changes = []
        for ch in result.get("changes", []):
            adapted_changes.append(
                _make_recommendation(ch["feature"], ch["old_value"], ch["new_value"], ch["impact"])
            )

        return {
            "producer_id": producer_id,
            "achievable": result.get("achievable", False),
            "current_score": result.get("current_score", 0),
            "target_score": result.get("target_score", threshold),
            "threshold": threshold,  # Frontend reads this key
            "changes": adapted_changes,
            "message": result.get("message", ""),
        }

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
            "threshold": threshold,
            "changes": [],
            "message": "Детальный анализ недоступен",
            "improvements": [
                {"action": "Повысить своевременность исполнения", "impact": "+5-10%"},
                {"action": "Увеличить объём заявок", "impact": "+3-5%"},
                {"action": "Подавать заявки в начале периода", "impact": "+2-3%"},
            ]
        }
