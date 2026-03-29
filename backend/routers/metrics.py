from fastapi import APIRouter, HTTPException
import core.state as state

router = APIRouter()


@router.get("/metrics")
def metrics():
    if state.MODEL_DATA is None:
        raise HTTPException(503, "Модель не загружена")

    m = state.MODEL_DATA["metrics"]
    return {
        "roc_auc": round(m.get("roc_auc", 0), 4),
        "avg_precision": round(m.get("avg_precision", 0), 4),
        "best_f1": round(m.get("best_f1", 0), 4),
        "optimal_threshold": round(m.get("best_threshold", 0.5), 4),
        "cv_auc_mean": round(m.get("cv_auc_mean", 0), 4),
        "cv_f1_mean": round(m.get("cv_f1_mean", 0), 4),
        "features": state.MODEL_DATA["features"],
        "n_features": len(state.MODEL_DATA["features"]),
    }


@router.get("/stats")
def stats():
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")
    return {
        "total_rows": int(len(state.DF)),
        "total_producers": int(state.DF["producer_id"].nunique()),
        "status_distribution": state.DF["Статус заявки"].value_counts().to_dict(),
        "year_distribution": {str(k): int(v) for k, v in state.DF["year"].value_counts().items()},
        "regions": state.DF["Область"].value_counts().to_dict(),
        "directions": state.DF["Направление водства"].value_counts().to_dict(),
        "avg_amount": round(float(state.DF["Причитающая сумма"].mean()), 2),
        "total_amount": round(float(state.DF["Причитающая сумма"].sum()), 2),
    }
