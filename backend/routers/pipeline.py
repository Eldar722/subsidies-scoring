"""
pipeline.py — запуск ML пайплайна (train.py) в фоне.
Использует BackgroundTasks для неблокирующего запуска.
После обучения добавляет запись в audit ledger.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
import subprocess
import time
import sys
import os
import asyncio
import json
from typing import Optional
import core.state as state
from routers.audit import add_audit_entry

router = APIRouter()

# Глобальный статус пайплайна
_pipeline_status = {
    "running": False,
    "last_run": None,
    "last_duration": None,
    "last_metrics": None,
    "last_error": None,
}


def _run_train_process():
    """Запустить train.py синхронно (вызывается в фоне)."""
    global _pipeline_status
    _pipeline_status["running"] = True
    _pipeline_status["last_error"] = None
    _pipeline_status["last_stdout"] = None
    _pipeline_status["last_stderr"] = None
    start_time = time.time()

    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    train_script = os.path.join(current_dir, "train.py")

    # Pre-flight: проверить наличие данных и скрипта
    data_path = os.environ.get("DATA_PATH", "data/subsidies.xlsx")
    abs_data = os.path.join(current_dir, data_path)
    if not os.path.exists(abs_data):
        _pipeline_status["last_error"] = f"DATA_PATH не найден: {abs_data}"
        _pipeline_status["running"] = False
        return
    if not os.path.exists(train_script):
        _pipeline_status["last_error"] = f"train.py не найден: {train_script}"
        _pipeline_status["running"] = False
        return

    try:
        result = subprocess.run(
            [sys.executable, train_script],
            capture_output=True,
            text=True,
            check=True,
            cwd=current_dir,
            env={**os.environ},  # передать переменные окружения (SUPABASE_URL и др.)
        )

        _pipeline_status["last_stdout"] = result.stdout[-5000:] if result.stdout else ""
        _pipeline_status["last_stderr"] = result.stderr[-2000:] if result.stderr else ""

        # Перезагружаем модель и данные после обучения
        state.load_model()
        state.load_data()

        duration = time.time() - start_time
        metrics = {}
        if state.MODEL_DATA and "metrics" in state.MODEL_DATA:
            metrics = state.MODEL_DATA["metrics"]

        _pipeline_status["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _pipeline_status["last_duration"] = round(duration, 2)
        _pipeline_status["last_metrics"] = metrics

        add_audit_entry("pipeline_run", {
            "status": "success",
            "duration_seconds": round(duration, 2),
            "roc_auc": metrics.get("roc_auc"),
            "best_f1": metrics.get("best_f1"),
        })

    except subprocess.CalledProcessError as e:
        _pipeline_status["last_stdout"] = e.stdout[-5000:] if e.stdout else ""
        _pipeline_status["last_stderr"] = e.stderr[-10000:] if e.stderr else ""
        # Показываем последние строки stderr — там обычно traceback
        short_err = (e.stderr or "")[-5000:].strip()
        _pipeline_status["last_error"] = short_err or f"exit code {e.returncode}"
        # Check for log file with full details
        log_path = os.path.join(current_dir, "logs", "train_error.log")
        if os.path.exists(log_path):
            _pipeline_status["error_log_path"] = log_path
        add_audit_entry("pipeline_run", {"status": "error", "error": _pipeline_status["last_error"][:500]})
    except Exception as e:
        _pipeline_status["last_error"] = str(e)
    finally:
        _pipeline_status["running"] = False


_ws_connections: list = []


@router.websocket("/pipeline/ws")
async def pipeline_ws(websocket: WebSocket):
    """WebSocket endpoint для real-time обновлений статуса пайплайна."""
    await websocket.accept()
    _ws_connections.append(websocket)
    try:
        await websocket.send_text(json.dumps(_pipeline_status))
        while True:
            await asyncio.sleep(1)
            await websocket.send_text(json.dumps(_pipeline_status))
    except (WebSocketDisconnect, Exception):
        if websocket in _ws_connections:
            _ws_connections.remove(websocket)


@router.get("/pipeline/status")
def pipeline_status():
    """Получить текущий статус пайплайна."""
    return _pipeline_status


@router.post("/pipeline/run")
async def run_pipeline(background_tasks: BackgroundTasks):
    """
    Запустить ML пайплайн в фоне.
    Возвращает сразу с task_id, статус можно получить через /api/pipeline/status.
    """
    if _pipeline_status["running"]:
        raise HTTPException(409, "Пайплайн уже запущен. Подождите завершения.")

    background_tasks.add_task(_run_train_process)

    return {
        "status": "started",
        "message": "Пайплайн запущен в фоне. Проверяйте /api/pipeline/status",
        "poll_url": "/api/pipeline/status",
    }
