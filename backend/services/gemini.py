from fastapi import APIRouter, HTTPException
from supabase import create_client
from core.config import SUPABASE_URL, SUPABASE_KEY
from services.gemini_advisor import get_advice

router = APIRouter()


@router.get("/producers/{producer_id}/advice")
def get_producer_advice(producer_id: str):
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Проверяем кэш
    cached = client.table("gemini_advice").select("advice_json").eq("producer_id", producer_id).execute()
    if cached.data:
        return cached.data[0]["advice_json"]

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

    # Кэшируем
    client.table("gemini_advice").upsert({
        "producer_id": producer_id,
        "advice_json": advice,
    }).execute()

    return advice
