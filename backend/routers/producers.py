import pandas as pd
from fastapi import APIRouter, HTTPException
import core.state as state
from ml.scoring import score_dataframe

router = APIRouter()


@router.get("/producers")
def producers_list():
    raise HTTPException(501, "Not implemented yet — P1 task")


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

    return result
