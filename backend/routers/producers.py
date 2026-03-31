import pandas as pd
from fastapi import APIRouter, HTTPException
import core.state as state
from ml.scoring import score_dataframe
from ml.baseline import compute_shortlist
import numpy as np

router = APIRouter()


@router.get("/producers")
def producers_list(
    region: str = None, 
    direction: str = None, 
    talent_only: bool = False, 
    min_score: float = None, 
    page: int = 1, 
    limit: int = 50
):
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")
    
    result = compute_shortlist(state.DF, top_n=len(state.DF))
    if not result or "shortlist" not in result:
        return {"total": 0, "page": page, "items": []}
        
    items = result["shortlist"]
    
    if region:
        items = [i for i in items if i["region"] == region]
    if direction:
        items = [i for i in items if i["direction"] == direction]
    if talent_only:
        items = [i for i in items if i["hidden_talent"]]
    if min_score is not None:
        items = [i for i in items if i["ml_score"] is not None and i["ml_score"] >= min_score]
        
    total = len(items)
    
    start = (page - 1) * limit
    end = start + limit
    paginated = items[start:end]
    
    return {
        "total": total,
        "page": page,
        "items": paginated
    }


@router.get("/producers/{producer_id}")
def producer_detail(producer_id: str):
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")

    producer_rows = state.DF[state.DF["producer_id"] == producer_id]
    if len(producer_rows) == 0:
        raise HTTPException(404, f"Производитель {producer_id} не найден")

    scored = score_dataframe(producer_rows)

    applications = []
    for _, row in producer_rows.iterrows():
        app_data = {
            "date": row["date"].isoformat() if pd.notna(row["date"]) else None,
            "status": row["Статус заявки"],
            "region": row["Область"],
            "direction": row["Направление водства"],
            "subsidy": row["Наименование субсидирования"],
            "amount": round(float(row["Причитающая сумма"]), 2) if pd.notna(row["Причитающая сумма"]) else None,
            "norm": round(float(row["Норматив"]), 2) if pd.notna(row["Норматив"]) else None,
        }
        applications.append(app_data)

    result = {
        "producer_id": producer_id,
        "total_applications": len(producer_rows),
        "status_breakdown": producer_rows["Статус заявки"].value_counts().to_dict(),
        "total_amount": round(float(producer_rows["Причитающая сумма"].sum()), 2),
        "avg_amount": round(float(producer_rows["Причитающая сумма"].mean()), 2),
        "region": producer_rows["Область"].mode().iloc[0] if len(producer_rows) > 0 else None,
        "applications": applications,
    }

    if len(scored) > 0:
        result["ml_score"] = round(float(scored["ml_score"].mean()), 4)
    else:
        result["ml_score"] = None

    history = []
    # Avoid warning on assignment, create a deepcopy or .loc
    producer_rows = producer_rows.copy()
    if "date" in producer_rows.columns and not producer_rows["date"].isna().all():
        producer_rows.loc[:, "month_year"] = producer_rows["date"].dt.strftime("%Y-%m")
        grouped = producer_rows.groupby("month_year")
        for name, group in grouped:
            history.append({
                "month": name,
                "count": int(len(group)),
                "amount": round(float(group["Причитающая сумма"].sum()), 2) if "Причитающая сумма" in group.columns else 0,
                "status_breakdown": group["Статус заявки"].value_counts().to_dict()
            })
            
    stats = {
        "total_applications": len(producer_rows),
        "completed": int(len(producer_rows[producer_rows["Статус заявки"] == "Исполнена"])),
        "approved": int(len(producer_rows[producer_rows["Статус заявки"] == "Исполнена"])), 
        "rejected": int(len(producer_rows[producer_rows["Статус заявки"].isin(["Отклонена", "Отозвано"])])),
        "active_months": len(history)
    }
    
    result["history"] = history
    result["stats"] = stats
    result["shap_values"] = [] 
    
    return result


@router.get("/map/regions")
def get_map_regions():
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")
        
    result = compute_shortlist(state.DF, top_n=len(state.DF))
    if not result or "shortlist" not in result:
        return []
        
    df_scores = pd.DataFrame(result["shortlist"])
    if df_scores.empty:
        return []
        
    agg = df_scores.groupby("region").agg(
        avg_ml_score=("ml_score", "mean"),
        producer_count=("producer_id", "count"),
        hidden_talent_count=("hidden_talent", "sum")
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
            "is_outlier": bool(z_score < -1.5)
        })
        
    return regions_map
