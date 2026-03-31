from fastapi import APIRouter
from cachetools import TTLCache

router = APIRouter()
# Храним советы в памяти до 24 часов (86400 сек)
advice_cache = TTLCache(maxsize=1000, ttl=86400)

@router.get("/producers/{producer_id}/advice")
def get_advice(producer_id: str):
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
