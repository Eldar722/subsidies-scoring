"""
producers.py — эндпоинты производителей.
Источник данных: Supabase (producers + scores + shap_values).
Fallback на state.DF для applications/history (сырые заявки не хранятся в Supabase).

Rate limits: READ_HEAVY (60/min), READ_LIGHT (120/min)
"""

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from cachetools import TTLCache
from core.rate_limits import limiter, READ_HEAVY, READ_LIGHT
from services.supabase_service import _get_admin_client
import core.state as state

router = APIRouter()

# Кэш для карты регионов (тяжёлая агрегация) — 5 минут
_regions_cache = TTLCache(maxsize=1, ttl=300)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_all_scores_with_producers() -> list:
    """Получить все scores JOIN producers из Supabase (для list и map)."""
    try:
        client = _get_admin_client()

        scores_resp = (
            client.table("scores")
            .select("producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent")
            .limit(20000)
            .execute()
        )
        scores = scores_resp.data or []
        if not scores:
            return []

        pids = [s["producer_id"] for s in scores]

        # Supabase IN-query лимит ~1000 элементов — батчим если надо
        producers_map = {}
        batch_size = 500
        for i in range(0, len(pids), batch_size):
            batch = pids[i:i + batch_size]
            prod_resp = (
                client.table("producers")
                .select("producer_id, region, direction, total_applications, completion_rate")
                .in_("producer_id", batch)
                .execute()
            )
            for p in (prod_resp.data or []):
                producers_map[p["producer_id"]] = p

        result = []
        for s in scores:
            p = producers_map.get(s["producer_id"], {})
            ml_score = s.get("ml_score") or 0
            delta = s.get("delta") or 0
            result.append({
                "producer_id": s["producer_id"],
                "ml_score": round(float(ml_score), 4),
                "ml_rank": s.get("ml_rank"),
                "fcfs_rank": s.get("fcfs_rank"),
                "delta": delta,
                "hidden_talent": bool(s.get("hidden_talent", False)),
                "at_risk": int(delta) < -10,
                "region": p.get("region"),
                "direction": p.get("direction"),
                "total_applications": p.get("total_applications"),
                "completion_rate": p.get("completion_rate"),
            })
        return result
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "unauthorized" in error_msg or "api key" in error_msg:
            print(f"[WARN] Supabase API key error in producers list: {e}")
        raise


def _get_all_items_cached() -> list:
    """Весь список с кэшем (для list и map)."""
    cache_key = "all_items"
    if cache_key in _regions_cache:
        return _regions_cache[cache_key]
    
    items = _fetch_all_scores_with_producers()
    if items:
        _regions_cache[cache_key] = items
    return items


def _get_full_shortlist() -> dict:
    """Полный shortlist (для startup warm-up и metrics).

    Возвращает dict с ключами: shortlist, total, hidden_talent_count.
    Вызывается из main.py (warmup) и metrics.py (агрегаты).
    """
    items = _get_all_items_cached()
    return {
        "shortlist": items,
        "total": len(items),
        "hidden_talent_count": sum(1 for i in items if i.get("hidden_talent")),
    }


def _fallback_all_items() -> list:
    """Fallback на state.DF."""
    if state.DF is None:
        return []
    from ml.baseline import compute_shortlist
    result = compute_shortlist(state.DF, top_n=len(state.DF))
    if not result or "shortlist" not in result:
        return []
    return result["shortlist"]


# ---------------------------------------------------------------------------
# GET /producers
# ---------------------------------------------------------------------------

@router.get("/producers")
@limiter.limit(READ_HEAVY)
def producers_list(
    request: Request,
    region: str = None,
    direction: str = None,
    talent_only: bool = False,
    min_score: float = None,
    page: int = 1,
    limit: int = 50,
):
    items = _get_all_items_cached()
    if not items:
        return {"total": 0, "page": page, "items": []}

    if region:
        items = [i for i in items if i.get("region") == region]
    if direction:
        items = [i for i in items if i.get("direction") == direction]
    if talent_only:
        items = [i for i in items if i.get("hidden_talent")]
    if min_score is not None:
        items = [i for i in items if (i.get("ml_score") or 0) >= min_score]

    # Сортировка по ml_score убывающий (scores в Supabase могут прийти в любом порядке)
    items = sorted(items, key=lambda x: x.get("ml_score") or 0, reverse=True)

    total = len(items)
    start = (page - 1) * limit
    paginated = items[start:start + limit]

    return {"total": total, "page": page, "items": paginated}


# ---------------------------------------------------------------------------
# GET /producers/{producer_id}
# ---------------------------------------------------------------------------

@router.get("/producers/{producer_id}")
@limiter.limit(READ_LIGHT)
def producer_detail(request: Request, producer_id: str):
    try:
        client = _get_admin_client()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed. Check server logs."
        )

    # 1. producers
    prod_resp = (
        client.table("producers")
        .select("producer_id, region, direction, total_applications, completion_rate")
        .eq("producer_id", producer_id)
        .limit(1)
        .execute()
    )
    prod_data = (prod_resp.data or [None])[0]

    # 2. scores
    score_resp = (
        client.table("scores")
        .select("producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent")
        .eq("producer_id", producer_id)
        .limit(1)
        .execute()
    )
    score_data = (score_resp.data or [None])[0]

    # Если нет ни в producers, ни в scores — 404
    if prod_data is None and score_data is None:
        # Попробуем fallback на state.DF
        if state.DF is not None and producer_id in state.DF["producer_id"].values:
            return _fallback_producer_detail(producer_id)
        raise HTTPException(404, f"Производитель {producer_id} не найден")

    # 3. shap_values
    shap_resp = (
        client.table("shap_values")
        .select("feature, shap_value, feature_label")
        .eq("producer_id", producer_id)
        .order("shap_value", desc=True)
        .limit(7)
        .execute()
    )
    shap_raw = shap_resp.data or []
    # Дедуп по feature (старые дубликаты в БД до UNIQUE) — оставляем строку с max |shap_value|
    by_feature = {}
    for r in shap_raw:
        feat = r["feature"]
        sv = round(float(r["shap_value"]), 4)
        row = {
            "feature": feat,
            "shap_value": sv,
            "feature_label": r.get("feature_label") or feat,
        }
        if feat not in by_feature or abs(sv) > abs(by_feature[feat]["shap_value"]):
            by_feature[feat] = row
    shap_values = sorted(by_feature.values(), key=lambda x: abs(x["shap_value"]), reverse=True)[:7]

    # 4. applications + history из state.DF (сырые данные не хранятся в Supabase)
    applications = []
    history = []
    status_breakdown = {}
    total_amount = 0.0
    avg_amount = 0.0
    stats = {}

    if state.DF is not None:
        producer_rows = state.DF[state.DF["producer_id"] == producer_id]
        if len(producer_rows) > 0:
            for _, row in producer_rows.iterrows():
                applications.append({
                    "date": row["date"].isoformat() if pd.notna(row["date"]) else None,
                    "status": row["Статус заявки"],
                    "region": row["Область"],
                    "direction": row["Направление водства"],
                    "subsidy": row["Наименование субсидирования"],
                    "amount": round(float(row["Причитающая сумма"]), 2) if pd.notna(row["Причитающая сумма"]) else None,
                    "norm": round(float(row["Норматив"]), 2) if pd.notna(row["Норматив"]) else None,
                })

            producer_rows_copy = producer_rows.copy()
            if "date" in producer_rows_copy.columns and not producer_rows_copy["date"].isna().all():
                producer_rows_copy.loc[:, "month_year"] = producer_rows_copy["date"].dt.strftime("%Y-%m")
                for name, group in producer_rows_copy.groupby("month_year"):
                    history.append({
                        "month": name,
                        "count": int(len(group)),
                        "amount": round(float(group["Причитающая сумма"].sum()), 2),
                        "status_breakdown": group["Статус заявки"].value_counts().to_dict(),
                    })

            status_breakdown = producer_rows["Статус заявки"].value_counts().to_dict()
            total_amount = round(float(producer_rows["Причитающая сумма"].sum()), 2)
            avg_amount = round(float(producer_rows["Причитающая сумма"].mean()), 2)
            directions_count = int(producer_rows["Направление водства"].nunique())
            n_apps = len(producer_rows)
            stats = {
                "total_applications": n_apps,
                "completed": int((producer_rows["Статус заявки"] == "Исполнена").sum()),
                "approved": int((producer_rows["Статус заявки"] == "Исполнена").sum()),
                "rejected": int(producer_rows["Статус заявки"].isin(["Отклонена", "Отозвано"]).sum()),
                "active_months": len(history),
                "directions_count": directions_count,
            }

    # Собираем ответ
    ml_score = None
    ml_rank = None
    fcfs_rank = None
    delta = None
    hidden_talent = False
    at_risk = False

    if score_data:
        raw_delta = score_data.get("delta") or 0
        ml_score = round(float(score_data.get("ml_score") or 0), 4)
        ml_rank = score_data.get("ml_rank")
        fcfs_rank = score_data.get("fcfs_rank")
        delta = int(raw_delta)
        hidden_talent = bool(score_data.get("hidden_talent", False))
        at_risk = delta < -10

    region = (prod_data or {}).get("region")
    direction = (prod_data or {}).get("direction")
    total_applications = (prod_data or {}).get("total_applications") or stats.get("total_applications", 0)

    return {
        "producer_id": producer_id,
        "region": region,
        "direction": direction,
        "ml_score": ml_score,
        "ml_rank": ml_rank,
        "fcfs_rank": fcfs_rank,
        "delta": delta,
        "hidden_talent": hidden_talent,
        "at_risk": at_risk,
        "total_applications": total_applications,
        "status_breakdown": status_breakdown,
        "total_amount": total_amount,
        "avg_amount": avg_amount,
        "applications": applications,
        "history": history,
        "stats": stats,
        "shap_values": shap_values,
    }


def _fallback_producer_detail(producer_id: str) -> dict:
    """Полный fallback на state.DF если Supabase вернул пустоту."""
    from ml.scoring import score_dataframe
    producer_rows = state.DF[state.DF["producer_id"] == producer_id]
    scored = score_dataframe(producer_rows)

    region = producer_rows["Область"].mode().iloc[0] if len(producer_rows) > 0 else None
    direction = producer_rows["Направление водства"].mode().iloc[0] if len(producer_rows) > 0 else None

    applications = []
    for _, row in producer_rows.iterrows():
        applications.append({
            "date": row["date"].isoformat() if pd.notna(row["date"]) else None,
            "status": row["Статус заявки"],
            "region": row["Область"],
            "direction": row["Направление водства"],
            "subsidy": row["Наименование субсидирования"],
            "amount": round(float(row["Причитающая сумма"]), 2) if pd.notna(row["Причитающая сумма"]) else None,
            "norm": round(float(row["Норматив"]), 2) if pd.notna(row["Норматив"]) else None,
        })

    history = []
    producer_rows_copy = producer_rows.copy()
    if "date" in producer_rows_copy.columns and not producer_rows_copy["date"].isna().all():
        producer_rows_copy.loc[:, "month_year"] = producer_rows_copy["date"].dt.strftime("%Y-%m")
        for name, group in producer_rows_copy.groupby("month_year"):
            history.append({
                "month": name,
                "count": int(len(group)),
                "amount": round(float(group["Причитающая сумма"].sum()), 2),
                "status_breakdown": group["Статус заявки"].value_counts().to_dict(),
            })

    directions_count = int(producer_rows["Направление водства"].nunique())
    stats = {
        "total_applications": len(producer_rows),
        "completed": int((producer_rows["Статус заявки"] == "Исполнена").sum()),
        "approved": int((producer_rows["Статус заявки"] == "Исполнена").sum()),
        "rejected": int(producer_rows["Статус заявки"].isin(["Отклонена", "Отозвано"]).sum()),
        "active_months": len(history),
        "directions_count": directions_count,
    }

    ml_score = round(float(scored["ml_score"].mean()), 4) if len(scored) > 0 else None

    return {
        "producer_id": producer_id,
        "region": region,
        "direction": direction,
        "ml_score": ml_score,
        "ml_rank": None,
        "fcfs_rank": None,
        "delta": None,
        "hidden_talent": False,
        "at_risk": False,
        "total_applications": len(producer_rows),
        "status_breakdown": producer_rows["Статус заявки"].value_counts().to_dict(),
        "total_amount": round(float(producer_rows["Причитающая сумма"].sum()), 2),
        "avg_amount": round(float(producer_rows["Причитающая сумма"].mean()), 2),
        "applications": applications,
        "history": history,
        "stats": stats,
        "shap_values": [],
    }


# ---------------------------------------------------------------------------
# GET /map/regions
# ---------------------------------------------------------------------------

@router.get("/map/regions")
@limiter.limit(READ_LIGHT)
def get_map_regions(request: Request):
    cache_key = "map_regions"
    if cache_key in _regions_cache:
        return _regions_cache[cache_key]

    try:
        items = _get_all_items_cached()
        if not items:
            return []

        # Агрегируем по региону в Python
        region_data: dict = {}
        for item in items:
            reg = item.get("region")
            if not reg:
                continue
            if reg not in region_data:
                region_data[reg] = {"scores": [], "hidden_talent_count": 0, "producer_count": 0}
            region_data[reg]["scores"].append(item.get("ml_score") or 0)
            region_data[reg]["producer_count"] += 1
            if item.get("hidden_talent"):
                region_data[reg]["hidden_talent_count"] += 1

        if not region_data:
            return []

        agg = [
            {
                "region": reg,
                "avg_ml_score": sum(d["scores"]) / len(d["scores"]),
                "producer_count": d["producer_count"],
                "hidden_talent_count": d["hidden_talent_count"],
            }
            for reg, d in region_data.items()
        ]

        mean_score = sum(a["avg_ml_score"] for a in agg) / len(agg)
        variance = sum((a["avg_ml_score"] - mean_score) ** 2 for a in agg) / len(agg)
        std_score = variance ** 0.5 if variance > 0 else 1.0

        regions_map = []
        for a in agg:
            z_score = (a["avg_ml_score"] - mean_score) / (std_score + 1e-9)
            regions_map.append({
                "region": a["region"],
                "avg_ml_score": round(a["avg_ml_score"], 4),
                "producer_count": a["producer_count"],
                "hidden_talent_count": a["hidden_talent_count"],
                "z_score": round(z_score, 4),
                "is_outlier": bool(z_score < -1.5),
            })

        _regions_cache[cache_key] = regions_map
        return regions_map

    except Exception as e:
        print(f"[WARN] Supabase map/regions failed: {e}, fallback to in-memory")
        return _fallback_map_regions()


def _fallback_map_regions() -> list:
    """Fallback карты на state.DF."""
    if state.DF is None:
        return []
    from ml.baseline import compute_shortlist
    result = compute_shortlist(state.DF, top_n=len(state.DF))
    if not result or "shortlist" not in result:
        return []

    df_scores = pd.DataFrame(result["shortlist"])
    if df_scores.empty:
        return []

    agg = df_scores.groupby("region").agg(
        avg_ml_score=("ml_score", "mean"),
        producer_count=("producer_id", "count"),
        hidden_talent_count=("hidden_talent", "sum"),
    ).reset_index()

    mean_score = agg["avg_ml_score"].mean()
    std_score = agg["avg_ml_score"].std() if len(agg) > 1 else 1.0

    regions_map = []
    for _, row in agg.iterrows():
        z_score = (row["avg_ml_score"] - mean_score) / (std_score + 1e-9)
        regions_map.append({
            "region": row["region"],
            "avg_ml_score": round(float(row["avg_ml_score"]), 4),
            "producer_count": int(row["producer_count"]),
            "hidden_talent_count": int(row["hidden_talent_count"]),
            "z_score": round(float(z_score), 4),
            "is_outlier": bool(z_score < -1.5),
        })
    return regions_map
