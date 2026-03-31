from fastapi import APIRouter, HTTPException
import subprocess
import time
import sys
import os
import core.state as state

router = APIRouter()

@router.post("/pipeline/run")
async def run_pipeline():
    start_time = time.time()
    try:
        # Абсолютный путь к train.py
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        train_script = os.path.join(current_dir, "train.py")
        
        # Запускаем скрипт обучения отдельным процессом, чтобы не трогать ML код
        # cwd=current_dir гарантирует, что train.py найдет файлы данных
        result = subprocess.run(
            [sys.executable, train_script], 
            capture_output=True, 
            text=True, 
            check=True,
            cwd=current_dir
        )
        
        # Обновляем глобальное состояние после сохранения новой model.pkl
        state.load_model()
        state.load_data()
        
        duration = time.time() - start_time
        
        # Извлекаем метрики прямо из свежезагруженной модели
        metrics = {}
        if state.MODEL_DATA and "metrics" in state.MODEL_DATA:
            metrics = state.MODEL_DATA["metrics"]
            
        return {
            "status": "success",
            "message": "Пайплайн завершён, новая модель загружена",
            "metrics": metrics,
            "duration_seconds": round(duration, 2)
        }
    except subprocess.CalledProcessError as e:
        error_msg = f"Ошибка обучения модели:\n{e.stderr}"
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
