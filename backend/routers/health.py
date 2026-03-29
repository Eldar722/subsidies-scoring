from fastapi import APIRouter
from datetime import datetime
import core.state as state

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "model": "loaded" if state.MODEL_DATA is not None else "not loaded",
        "data": "loaded" if state.DF is not None else "not loaded",
        "rows": int(len(state.DF)) if state.DF is not None else 0,
        "model_version": "v4",
        "timestamp": datetime.utcnow().isoformat(),
    }
