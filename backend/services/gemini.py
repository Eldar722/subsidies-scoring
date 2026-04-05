"""
gemini.py — AI advisor endpoints (Gemini/Groq).
Rate limit: AI (5/min) — expensive external API calls.
"""

from fastapi import APIRouter, HTTPException, Request
from core.rate_limits import limiter, AI
from services.supabase_service import _get_admin_client
from services.gemini_advisor import get_advice
from services.gemini_advice_store import get_cached_advice, upsert_advice
from cachetools import TTLCache

router = APIRouter()
# Храним советы в памяти до 24 часов (86400 сек)
advice_cache = TTLCache(maxsize=1000, ttl=86400)


@router.get("/producers/{producer_id}/advice")
@limiter.limit(AI)
def get_producer_advice(request: Request, producer_id: str):
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

    advice = get_advice(producer_data)

    upsert_advice(client, producer_id, advice)

    return advice
def get_advice_fallback(producer_id: str):
    # 1. Проверяем кэш
    if producer_id in advice_cache:
        return advice_cache[producer_id]
        
    # 2. Если бы был подключен ML_AI, здесь был бы вызов get_advice() из ML.
    # Так как ML трогать нельзя, возвращаем Fallback JSON согласно Промпту 5.1 "Если Gemini недоступен"
    fallback_response = {
        "producer_id": producer_id,
        "score_explanation": "Анализ от AI временно недоступен. ML-скоринг базируется на истории заявок и своевременности исполнения.",
        "baseline_injustice": "Системных аномалий или ярко выраженной несправедливости не выявлено.",
        "recommendations": [
            {
                "action": "Своевременно завершать исполнение заявок",
                "impact": "Повысит ML-скоринг на 10-15% в следующем квартале"
            },
            {
                "action": "Избегать отзывов заявок в конце месяца",
                "impact": "Снизит вероятность попадания в серую зону (outlier)"
            }
        ]
    }
    
    # 3. Сохраняем в кэш
    advice_cache[producer_id] = fallback_response
    
    return fallback_response
