"""
health.py — health check endpoints.
Rate limit: HEALTH (10/min) — monitoring systems may poll frequently.
"""

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from core.rate_limits import limiter, HEALTH
import core.state as state

router = APIRouter()


@router.get("/health")
@limiter.limit(HEALTH)
def health(request: Request):
    """Health check with DB ping."""
    db_status = _check_db()
    return {
        "status": "ok",
        "model": "loaded" if state.MODEL_DATA is not None else "not loaded",
        "data": "loaded" if state.DF is not None else "not loaded",
        "rows": int(len(state.DF)) if state.DF is not None else 0,
        "database": db_status,
        "model_version": state.MODEL_DATA.get("reproducibility", {}).get("model_version", "v4")
                         if state.MODEL_DATA else "unknown",
        "model_auc": state.MODEL_DATA.get("metrics", {}).get("roc_auc")
                     if state.MODEL_DATA else None,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _check_db() -> dict:
    """Ping Postgres with SELECT 1. Returns status dict."""
    try:
        import psycopg2
        from core.config import DATABASE_URL
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "connected"}
    except ImportError:
        return {"status": "psycopg2_not_installed"}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:200]}


@router.post("/health/reload-model")
@limiter.limit("5/minute")
def reload_model(request: Request):
    """Перезагрузить модель из disk без рестарта backend.

    Uses safe_swap: load→validate→swap under RLock.
    """
    try:
        from core.state import safe_swap_model, get_model_auc, MODEL_PATH
        import os

        model_path = os.environ.get("MODEL_PATH", MODEL_PATH)
        if not os.path.exists(model_path):
            raise HTTPException(404, f"Model file not found: {model_path}")

        success = safe_swap_model(model_path)
        if not success:
            raise HTTPException(500, "Failed to validate/swap model (check logs)")

        # Rebuild caches
        try:
            from core.state import build_precomputed_caches
            build_precomputed_caches()
        except Exception as cache_err:
            print(f"[WARN] Cache rebuild after reload: {cache_err}")

        return {
            "status": "ok",
            "message": "Model swapped successfully",
            "auc": get_model_auc(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to reload model: {str(e)}")
