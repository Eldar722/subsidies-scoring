"""
Чтение/запись кэша AI-советов в Supabase.
Поддерживает и advice_json, и legacy-колонку advice — без обязательной миграции.
"""

from __future__ import annotations

from typing import Any


def get_cached_advice(client, producer_id: str) -> dict | None:
    """Вернуть JSON совета или None."""
    for col in ("advice_json", "advice"):
        try:
            r = (
                client.table("gemini_advice")
                .select(col)
                .eq("producer_id", producer_id)
                .limit(1)
                .execute()
            )
            if r.data:
                val = r.data[0].get(col)
                if val is not None:
                    return val
        except Exception:
            continue
    return None


def upsert_advice(client, producer_id: str, advice: dict[str, Any]) -> None:
    """Сохранить совет; пробуем колонку, совместимую с текущей схемой."""
    last: Exception | None = None
    for col in ("advice_json", "advice"):
        try:
            client.table("gemini_advice").upsert(
                {"producer_id": producer_id, col: advice}
            ).execute()
            return
        except Exception as e:
            last = e
            continue
    if last:
        raise last


def sample_advice_payload(row: dict) -> dict | None:
    """Достать JSON из строки select('*')."""
    if not row:
        return None
    return row.get("advice_json") if row.get("advice_json") is not None else row.get("advice")
