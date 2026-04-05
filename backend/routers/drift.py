"""
drift.py — drift detection and confidence scoring.
Rate limit: READ_LIGHT (120/min)

Response adapters:
  - /confidence/{id}: translates backend keys → frontend-expected keys
  - /drift/status: adds `drifted_features` alias for frontend compat
"""

from fastapi import APIRouter, HTTPException, Request, Query
from core.rate_limits import limiter, READ_LIGHT
import threading
import core.state as state
from ml.drift_monitor import fit_monitor, compute_confidence, compute_drift_status
from ml.feature_engineering import build_features, FEATURES
from ml.scoring import score_dataframe
import numpy as np

router = APIRouter()
_monitor_fitted = False
_monitor_lock = threading.Lock()


def _ensure_monitor():
    global _monitor_fitted
    if _monitor_fitted:
        return
    with _monitor_lock:
        # Double-check after acquiring lock
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
@limiter.limit(READ_LIGHT)
def drift_status(request: Request):
    _ensure_monitor()
    resolved = state.DF[state.DF["target"].notna()].copy()
    resolved["target"] = resolved["target"].astype(int)
    val = resolved[resolved["year"] == 2026].reset_index(drop=True)
    X_val = build_features(val, fit=False)
    result = compute_drift_status(X_val)

    # ── Frontend compatibility: drifted_features alias ──
    result["drifted_features"] = [
        item["feature"] for item in result.get("top_drift_features", []) if item.get("drifted", False)
    ]
    return result


@router.get("/confidence/{producer_id}")
@limiter.limit(READ_LIGHT)
def producer_confidence(request: Request, producer_id: str):
    _ensure_monitor()
    scored = score_dataframe(state.DF)
    rows = scored[scored["producer_id"] == producer_id]
    if len(rows) == 0:
        raise HTTPException(404, "Producer not found")
    row = rows.iloc[0]
    x = row[FEATURES].values.astype(float)
    result = compute_confidence(x)

    # ── Adapt response for frontend compatibility ──
    # Frontend reads: is_low_confidence, confidence_score, explanation, anomalous_features
    # Backend returns: confidence, risk_level, reasons
    anomalous = [r["feature"] for r in result.get("reasons", [])]
    explanation_parts = [f"Confidence: {result['confidence']:.0%}"]
    if result["risk_level"] == "low_confidence":
        explanation_parts.append("Модель не уверена в этом прогнозе")
    if anomalous:
        explanation_parts.append(f"Аномальные признаки: {', '.join(anomalous)}")
    elif result.get("reasons"):
        for r in result["reasons"]:
            explanation_parts.append(f"{r.get('feature', '?')}: {r.get('description', '')}")

    return {
        "producer_id": producer_id,
        "is_low_confidence": result["risk_level"] == "low_confidence",
        "confidence_score": result["confidence"],
        "confidence": result["confidence"],  # Also keep original
        "distance": result["distance"],
        "risk_level": result["risk_level"],
        "explanation": ". ".join(explanation_parts),
        "anomalous_features": anomalous,
        "reasons": result.get("reasons", []),  # Also keep original
    }
