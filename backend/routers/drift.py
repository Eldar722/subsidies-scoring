from fastapi import APIRouter, HTTPException, Query
import core.state as state
from ml.drift_monitor import fit_monitor, compute_confidence, compute_drift_status
from ml.feature_engineering import build_features, FEATURES
from ml.scoring import score_dataframe
import numpy as np

router = APIRouter()
_monitor_fitted = False


def _ensure_monitor():
    global _monitor_fitted
    if _monitor_fitted:
        return
    if state.DF is None or state.MODEL_DATA is None:
        raise HTTPException(503, "Data or model not loaded")
    resolved = state.DF[state.DF["target"].notna()].copy()
    resolved["target"] = resolved["target"].astype(int)
    train = resolved[resolved["year"] == 2025].reset_index(drop=True)
    X_train = build_features(train, fit=True)
    fit_monitor(X_train)
    _monitor_fitted = True


@router.get("/drift/status")
def drift_status():
    _ensure_monitor()
    resolved = state.DF[state.DF["target"].notna()].copy()
    resolved["target"] = resolved["target"].astype(int)
    val = resolved[resolved["year"] == 2026].reset_index(drop=True)
    X_val = build_features(val, fit=False)
    return compute_drift_status(X_val)


@router.get("/confidence/{producer_id}")
def producer_confidence(producer_id: str):
    _ensure_monitor()
    scored = score_dataframe(state.DF)
    rows = scored[scored["producer_id"] == producer_id]
    if len(rows) == 0:
        raise HTTPException(404, "Producer not found")
    row = rows.iloc[0]
    x = row[FEATURES].values.astype(float)
    result = compute_confidence(x)
    result["producer_id"] = producer_id
    return result
