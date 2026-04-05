"""
gemini.py — AI advisor endpoints (Gemini/Groq).
Rate limit: AI (5/min) — expensive external API calls.

Diagnostic: if AI keys are placeholder/unconfigured, returns a clear error
message instead of silently returning DEFAULT_ADVICE.
"""

from fastapi import APIRouter, HTTPException, Request
from core.rate_limits import limiter, AI
from core.config import GROQ_API_KEY, GEMINI_API_KEY
from services.supabase_service import _get_admin_client
from services.gemini_advisor import get_advice
from services.gemini_advice_store import get_cached_advice, upsert_advice
from cachetools import TTLCache

router = APIRouter()
# Храним советы в памяти до 24 часов (86400 сек)
advice_cache = TTLCache(maxsize=1000, ttl=86400)


def _ai_configured() -> bool:
    """Check if at least one AI provider has a real key (not placeholder)."""
    groq_real = GROQ_API_KEY and not GROQ_API_KEY.startswith("gsk_x") and len(GROQ_API_KEY) > 20
    gemini_real = GEMINI_API_KEY and not GEMINI_API_KEY.startswith("AIzaSyX") and len(GEMINI_API_KEY) > 20
    return groq_real or gemini_real


def _ai_error_response(producer_id: str) -> dict:
    """Return a helpful error when AI is not configured."""
    groq_set = bool(GROQ_API_KEY and len(GROQ_API_KEY) > 10)
    gemini_set = bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 10)
    return {
        "producer_id": producer_id,
        "score_explanation": (
            "AI-советник временно недоступен. ML-скоринг базируется на анализе "
            "истории заявок, своевременности исполнения и региональных факторах."
        ),
        "baseline_injustice": (
            "Для получения AI-объяснений настройте API-ключи в .env: "
            f"GROQ_API_KEY={'настроен' if groq_set else 'не настроен'}, "
            f"GEMINI_API_KEY={'настроен' if gemini_set else 'не настроен'}. "
            "Инструкция: backend/.env.example"
        ),
        "recommendations": [
            {
                "problem": "AI-объяснения недоступны",
                "cause": "API-ключи Groq/Gemini не настроены или невалидны",
                "action": "Добавьте реальные ключи в backend/.env (см. .env.example)",
                "impact": "+полный AI-анализ"
            },
            {
                "action": "Своевременно завершать исполнение заявок",
                "impact": "+10-15%"
            },
            {
                "action": "Увеличить долю одобренных заявок",
                "impact": "+5-10%"
            }
        ],
        "_ai_status": "not_configured",
        "_groq_configured": groq_set,
        "_gemini_configured": gemini_set,
    }


@router.get("/producers/{producer_id}/advice")
@limiter.limit(AI)
def get_producer_advice(request: Request, producer_id: str):
    # Check if AI is configured at all
    if not _ai_configured():
        print(f"[AI] Keys not configured for {producer_id} — returning config error")
        return _ai_error_response(producer_id)

    client = _get_admin_client()

    cached_payload = get_cached_advice(client, producer_id)
    if cached_payload is not None:
        return cached_payload

    # Собираем данные и генерируем
    score_res = client.table("scores").select("*").eq("producer_id", producer_id).execute()
    if not score_res.data:
        raise HTTPException(404, "Producer not found")
    score = score_res.data[0]

    prod_res = client.table("producers").select("region, direction").eq("producer_id", producer_id).execute()
    prod = prod_res.data[0] if prod_res.data else {"region": "?", "direction": "?"}

    shap_res = (
        client.table("shap_values")
        .select("feature, shap_value, feature_value, feature_label")
        .eq("producer_id", producer_id)
        .order("shap_value", desc=True)
        .limit(5)
        .execute()
    )

    producer_data = {
        "producer_id": producer_id,
        "ml_score": score["ml_score"],
        "ml_rank": score["ml_rank"],
        "fcfs_rank": score["fcfs_rank"],
        "delta": score["delta"],
        "region": prod["region"],
        "direction": prod["direction"],
        "shap_top5": shap_res.data if shap_res.data else [],
    }

    print(f"[AI] Generating advice for {producer_id} (Groq primary, Gemini fallback)")
    advice = get_advice(producer_data)

    # Check if we got DEFAULT_ADVICE back (both providers failed)
    if advice.get("score_explanation", "").startswith("Не удалось получить анализ"):
        print(f"[AI] Both providers failed for {producer_id} — returning fallback")
        return _ai_error_response(producer_id)

    upsert_advice(client, producer_id, advice)

    return advice
