from fastapi import APIRouter, HTTPException
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


@router.post("/health/reload-model")
def reload_model():
    """Перезагрузить модель из disk без рестарта backend.
    
    Используйте после train.py для обновления модели в памяти.
    """
    try:
        success = state.load_model()
        if not success:
            raise HTTPException(500, "Failed to load model from disk")
        
        return {
            "status": "ok",
            "message": "Model reloaded successfully",
            "auc": state.MODEL_DATA['metrics']['roc_auc'] if state.MODEL_DATA else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to reload model: {str(e)}")
