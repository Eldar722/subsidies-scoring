"""
model_management.py — API endpoints for model version management.

Rate limits:
  GET    /api/models                 — READ_LIGHT (120/min)
  GET    /api/models/active          — READ_LIGHT (120/min)
  POST   /api/models/{version}/activate — WRITE (10/min)
  POST   /api/models/rollback         — WRITE (10/min)
  GET    /api/models/auto-rollback    — READ_LIGHT (120/min)
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from core.rate_limits import limiter, READ_LIGHT, WRITE

router = APIRouter()


class ActivateRequest(BaseModel):
    """Request to activate a model."""
    version: Optional[str] = None
    force: bool = False


class RollbackRequest(BaseModel):
    """Request to rollback a model."""
    version: Optional[str] = None
    reason: str = "manual"


@router.get("/models")
@limiter.limit(READ_LIGHT)
def list_models(request: Request, limit: int = 20):
    """List all registered models, most recent first."""
    try:
        from services.model_registry import list_models as _list_models, ensure_registry_table
        ensure_registry_table()
        return {"models": _list_models(limit)}
    except Exception as e:
        raise HTTPException(500, f"Failed to list models: {str(e)}")


@router.get("/models/active")
@limiter.limit(READ_LIGHT)
def get_active_model(request: Request):
    """Get the currently active model."""
    try:
        from services.model_registry import get_active_model, ensure_registry_table
        ensure_registry_table()
        active = get_active_model()
        if not active:
            return {"active": None, "message": "No model is currently active"}
        return {"active": active}
    except Exception as e:
        raise HTTPException(500, f"Failed to get active model: {str(e)}")


@router.post("/models/{version}/activate")
@limiter.limit(WRITE)
def activate_model(request: Request, version: str, force: bool = False):
    """
    Activate a specific model version.

    - Validates model exists in storage
    - Deactivates current active model
    - Loads new model into memory
    - Schedules auto-rollback check
    """
    try:
        from services.model_registry import (
            activate_model as _activate, ensure_registry_table, list_models
        )
        ensure_registry_table()

        # Check model exists
        models = list_models(limit=1000)
        model_versions = [m["version"] for m in models]
        if version not in model_versions:
            # Check storage directly
            from services.model_storage import get_storage
            storage = get_storage()
            if not storage.exists(version):
                raise HTTPException(404, f"Model version '{version}' not found in registry or storage")

        result = _activate(version)
        if not result or not result.get("success"):
            raise HTTPException(500, result.get("error", "Activation failed"))

        return {
            "status": "ok",
            "activated": version,
            "previous": result.get("previous_active"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to activate model: {str(e)}")


@router.post("/models/rollback")
@limiter.limit(WRITE)
def rollback_model(request: Request, req: RollbackRequest = RollbackRequest()):
    """
    Rollback to a previous model version.

    - If version specified: rollback to that version
    - If no version: rollback to the previous active model
    - Logs the rollback reason
    """
    try:
        from services.model_registry import rollback_model as _rollback, ensure_registry_table
        ensure_registry_table()

        result = _rollback(version=req.version, reason=req.reason)
        if not result or not result.get("success"):
            raise HTTPException(500, result.get("error", "Rollback failed"))

        return {
            "status": "ok",
            "rolled_back_to": result.get("target"),
            "previous": result.get("previous"),
            "reason": req.reason,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to rollback: {str(e)}")


@router.get("/models/auto-rollback")
@limiter.limit(READ_LIGHT)
def auto_rollback_status(request: Request):
    """Get auto-rollback configuration and status."""
    try:
        from services.model_registry import check_auto_rollback
        return check_auto_rollback()
    except Exception as e:
        raise HTTPException(500, f"Failed to get auto-rollback status: {str(e)}")
