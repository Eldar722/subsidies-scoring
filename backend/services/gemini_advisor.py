"""
gemini_advisor.py — AI-советник на базе Groq (Llama-3.3-70b) / Gemini 2.0 Flash.
Переводит SHAP в русский текст с рекомендациями для комиссии.
Поддерживает fallback-логику, если один из провайдеров недоступен.
"""

import json
import time
import google.generativeai as genai
from groq import Groq
from supabase import create_client
from core.config import GEMINI_API_KEY, GROQ_API_KEY, AI_PROVIDER, SUPABASE_URL, SUPABASE_KEY

genai.configure(api_key=GEMINI_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

SYSTEM_PROMPT = """Ты — AI-советник для комиссии МСХ Казахстана по субсидиям в животноводстве.
Отвечай только на русском языке. Будь конкретным и практичным.
Возвращай ТОЛЬКО валидный JSON без markdown блоков."""

USER_PROMPT_TEMPLATE = """Производитель {producer_id} из региона {region}, направление: {direction}.
ML балл: {ml_score:.1%}. FCFS ранг: #{fcfs_rank}. ML ранг: #{ml_rank}. Delta: {delta}.

Топ факторы влияющие на балл (SHAP):
{shap_factors}

Верни JSON:
{{
  "score_explanation": "2-3 предложения почему такой ML-балл с учётом SHAP-факторов",
  "baseline_injustice": "1 предложение — насколько справедлив FCFS-ранг для этого производителя",
  "recommendations": [
    {{
      "problem": "конкретная проблема из SHAP (что именно снижает балл)",
      "cause": "почему это происходит — реальная причина",
      "action": "конкретное действие для улучшения",
      "impact": "+X% к вероятности одобрения"
    }},
    {{
      "problem": "вторая проблема",
      "cause": "причина",
      "action": "второе действие",
      "impact": "+Y%"
    }}
  ]
}}"""

DEFAULT_ADVICE = {
    "score_explanation": "Не удалось получить анализ от AI-советника.",
    "baseline_injustice": "Данные недоступны.",
    "recommendations": [],
}


def _get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _format_shap(shap_items):
    lines = []
    for item in shap_items:
        sign = "+" if item["shap_value"] > 0 else ""
        lines.append(
            f"  {item['feature_label']}: {item['feature_value']:.2f} (SHAP {sign}{item['shap_value']:.4f})"
        )
    return "\n".join(lines)


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _call_groq(prompt: str) -> dict:
    if not groq_client:
        raise ValueError("GROQ_API_KEY not configured")
    response = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    text = response.choices[0].message.content
    return json.loads(_clean_json(text))


def _call_gemini(prompt: str) -> dict:
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        [{"role": "user", "parts": [SYSTEM_PROMPT + "\n\n" + prompt]}]
    )
    return json.loads(_clean_json(response.text))


def get_advice(producer_data: dict, max_retries=2) -> dict:
    """Получить совет AI (Groq или Gemini) для одного производителя."""
    shap_factors = _format_shap(producer_data.get("shap_top5", []))
    prompt = USER_PROMPT_TEMPLATE.format(
        shap_factors=shap_factors,
        **{k: producer_data[k] for k in
           ["producer_id", "region", "direction", "ml_score",
            "fcfs_rank", "ml_rank", "delta"]},
    )

    for attempt in range(max_retries + 1):
        try:
            if AI_PROVIDER.lower() == "groq":
                try:
                    return _call_groq(prompt)
                except Exception as e:
                    print(f"  [WARN] Groq failed, falling back to Gemini: {e}")
                    return _call_gemini(prompt)
            else:
                return _call_gemini(prompt)
        except (json.JSONDecodeError, Exception) as e:
            if attempt < max_retries:
                time.sleep(2)
            else:
                print(f"  [WARN] All AI providers failed for {producer_data['producer_id']}: {e}")
                return DEFAULT_ADVICE.copy()


def batch_advise(limit=100):
    """Получить советы для топ-N производителей и сохранить в Supabase."""
    client = _get_supabase()

    # Получаем топ производителей из scores
    scores_res = (
        client.table("scores")
        .select("producer_id, ml_score, ml_rank, fcfs_rank, delta")
        .order("ml_score", desc=True)
        .limit(limit)
        .execute()
    )
    scores = scores_res.data

    success = 0
    for i, score in enumerate(scores):
        pid = score["producer_id"]

        # Проверяем кэш
        cached = client.table("gemini_advice").select("producer_id").eq("producer_id", pid).execute()
        if cached.data:
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(scores)}] {pid} — кэш")
            continue

        # Получаем данные producer
        prod_res = client.table("producers").select("region, direction").eq("producer_id", pid).execute()
        prod = prod_res.data[0] if prod_res.data else {"region": "?", "direction": "?"}

        # SHAP
        shap_res = (
            client.table("shap_values")
            .select("feature, shap_value, feature_value, feature_label")
            .eq("producer_id", pid)
            .order("shap_value", desc=True)
            .limit(5)
            .execute()
        )

        producer_data = {
            "producer_id": pid,
            "ml_score": score["ml_score"],
            "ml_rank": score["ml_rank"],
            "fcfs_rank": score["fcfs_rank"],
            "delta": score["delta"],
            "region": prod["region"],
            "direction": prod["direction"],
            "shap_top5": shap_res.data if shap_res.data else [],
        }

        advice = get_advice(producer_data)

        # Сохраняем
        client.table("gemini_advice").upsert({
            "producer_id": pid,
            "advice_json": advice,
        }).execute()

        success += 1
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(scores)}] обработано, успешных: {success}")

        time.sleep(0.5)  # Rate limit

    print(f"\nГотово: {success} новых советов из {len(scores)} производителей")
    return success


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("Запуск batch_advise для топ-20...")
    batch_advise(limit=20)

    # Показать пример
    client = _get_supabase()
    sample = client.table("gemini_advice").select("*").limit(1).execute()
    if sample.data:
        print(f"\nПример совета для {sample.data[0]['producer_id']}:")
        print(json.dumps(sample.data[0]["advice_json"], ensure_ascii=False, indent=2))
