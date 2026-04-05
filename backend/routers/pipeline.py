"""
pipeline.py — запуск ML пайплайна (train.py) в фоне.
Использует BackgroundTasks для неблокирующего запуска.
После обучения добавляет запись в audit ledger.

Thread-safety: _pipeline_status protected by threading.Lock.
WebSocket connections properly cleaned up on disconnect.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
import subprocess
import time
import sys
import os
import asyncio
import json
import threading
from core.rate_limits import limiter, WRITE, READ_LIGHT
import core.state as state
from routers.audit import add_audit_entry

router = APIRouter()

# ── Thread-safe pipeline status ──
_pipeline_lock = threading.Lock()
_pipeline_status = {
    "running": False,
    "last_run": None,
    "last_duration": None,
    "last_metrics": None,
    "last_error": None,
}


def _decode_utf8_output(raw: bytes | None, tail: int) -> str:
    if not raw:
        return ""
    s = raw.decode("utf-8", errors="replace")
    return s[-tail:] if len(s) > tail else s


def _set_status(**kwargs):
    """Thread-safe status update."""
    with _pipeline_lock:
        _pipeline_status.update(kwargs)


def _get_status() -> dict:
    """Thread-safe status snapshot."""
    with _pipeline_lock:
        return dict(_pipeline_status)


def _run_train_process():
    """Запустить train.py синхронно (вызывается в фоне)."""
    _set_status(last_error=None, last_stdout=None, last_stderr=None)
    start_time = time.time()

    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    train_script = os.path.join(current_dir, "train.py")

    # Pre-flight: проверить наличие данных и скрипта
    data_path = os.environ.get("DATA_PATH", "data/subsidies.xlsx")
    abs_data = os.path.join(current_dir, data_path)
    if not os.path.exists(abs_data):
        _set_status(running=False, last_error=f"DATA_PATH не найден: {abs_data}")
        add_audit_entry("pipeline_run", {"status": "error", "error": f"DATA_PATH не найден: {abs_data}"})
        return
    if not os.path.exists(train_script):
        _set_status(running=False, last_error=f"train.py не найден: {train_script}")
        add_audit_entry("pipeline_run", {"status": "error", "error": f"train.py не найден: {train_script}"})
        return

    train_env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }

    try:
        # Байтовый capture + UTF-8 decode: избегаем UnicodeDecodeError (cp1251) на Windows
        result = subprocess.run(
            [sys.executable, train_script],
            capture_output=True,
            check=True,
            cwd=current_dir,
            env=train_env,
        )

        _set_status(
            last_stdout=_decode_utf8_output(result.stdout, 5000),
            last_stderr=_decode_utf8_output(result.stderr, 2000),
        )

        # Перезагружаем модель и данные после обучения (thread-safe swap)
        state.load_model()
        state.load_data()
        try:
            state.build_precomputed_caches()
        except Exception as cache_err:
            print(f"[WARN] build_precomputed_caches after train: {cache_err}")

        # Activate new model in registry (triggers auto-rollback scheduling)
        try:
            from services.model_registry import (
                ensure_registry_table, activate_model, get_active_model
            )
            ensure_registry_table()
            # Get the version from the loaded model
            model_version = state.MODEL_DATA.get("reproducibility", {}).get("model_version") if state.MODEL_DATA else None
            if model_version:
                activation_result = activate_model(model_version)
                print(f"    ✓ Model activated: {model_version}")
            else:
                # Fallback: just reload
                print("    [WARN] No model version found — skipped registry activation")
        except Exception as act_err:
            print(f"    [WARN] Model activation failed (model loaded but not registered): {act_err}")

        state.clear_api_caches()

        duration = time.time() - start_time
        metrics = {}
        snap = state.take_snapshot()
        if snap.model_data and "metrics" in snap.model_data:
            metrics = snap.model_data["metrics"]

        _set_status(
            running=False,
            last_run=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            last_duration=round(duration, 2),
            last_metrics=metrics,
            last_error=None,
        )

        add_audit_entry("pipeline_run", {
            "status": "success",
            "duration_seconds": round(duration, 2),
            "roc_auc": metrics.get("roc_auc"),
            "best_f1": metrics.get("best_f1"),
        })

    except subprocess.CalledProcessError as e:
        if isinstance(e.stdout, bytes):
            stdout_tail = _decode_utf8_output(e.stdout, 5000)
        else:
            stdout_tail = (e.stdout or "")[-5000:]
        if isinstance(e.stderr, bytes):
            stderr_tail = _decode_utf8_output(e.stderr, 10000)
        else:
            stderr_tail = (e.stderr or "")[-10000:]
        short_err = (stderr_tail or "").strip()[-5000:]
        _set_status(
            running=False,
            last_stdout=stdout_tail,
            last_stderr=stderr_tail,
            last_error=short_err or f"exit code {e.returncode}",
        )
        log_path = os.path.join(current_dir, "logs", "train_error.log")
        if os.path.exists(log_path):
            _set_status(error_log_path=log_path)
        add_audit_entry("pipeline_run", {"status": "error", "error": short_err[:500]})
    except Exception as e:
        err_type = type(e).__name__
        err_msg = f"{err_type}: {e}"
        _set_status(running=False, last_error=err_msg)
        add_audit_entry("pipeline_run", {"status": "error", "error": err_msg[:500]})


# ── WebSocket connections with proper cleanup ──
_ws_connections: set[WebSocket] = set()


@router.websocket("/pipeline/ws")
async def pipeline_ws(websocket: WebSocket):
    """WebSocket endpoint для real-time обновлений статуса пайплайна."""
    await websocket.accept()
    _ws_connections.add(websocket)
    try:
        while True:
            await websocket.send_text(json.dumps(_get_status()))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _ws_connections.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/pipeline/status")
@limiter.limit(READ_LIGHT)
def pipeline_status(request: Request):
    """Получить текущий статус пайплайна."""
    return _get_status()


@router.post("/pipeline/run")
@limiter.limit(WRITE)
async def run_pipeline(request: Request, background_tasks: BackgroundTasks):
    """
    Запустить ML пайплайн в фоне.
    Возвращает сразу с task_id, статус можно получить через /api/pipeline/status.
    """
    with _pipeline_lock:
        if _pipeline_status["running"]:
            raise HTTPException(409, "Пайплайн уже запущен. Подождите завершения.")
        # Помечаем running атомарно внутри lock
        _pipeline_status["running"] = True
        _pipeline_status["last_error"] = None
        _pipeline_status["run_started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    background_tasks.add_task(_run_train_process)

    return {
        "status": "started",
        "message": "Пайплайн запущен в фоне. Проверяйте /api/pipeline/status",
        "poll_url": "/api/pipeline/status",
    }
