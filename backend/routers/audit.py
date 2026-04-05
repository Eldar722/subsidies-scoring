"""
audit.py — неизменяемый журнал аудита решений пайплайна.
Каждый запуск pipeline добавляет запись с SHA-256 хешем.

Rate limits: READ_LIGHT (120/min) — read-only audit log.
"""

import hashlib
import json
from datetime import datetime
from fastapi import APIRouter, Request
from core.rate_limits import limiter, READ_LIGHT
from collections import deque
import core.state as state

router = APIRouter()

# Хранение последних 100 записей в памяти
_audit_log: deque = deque(maxlen=100)


def add_audit_entry(event_type: str, payload: dict):
    """Добавить запись в журнал аудита. Вызывается из pipeline роутера."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "dataset_size": int(len(state.DF)) if state.DF is not None else 0,
        "payload": payload,
    }
    # SHA-256 хеш записи для неизменяемости
    entry_str = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    entry["hash"] = hashlib.sha256(entry_str.encode()).hexdigest()
    _audit_log.appendleft(entry)
    return entry


@router.get("/audit/ledger")
@limiter.limit(READ_LIGHT)
def get_audit_ledger(request: Request, limit: int = 50):
    """
    Возвращает журнал аудита (последние N записей).
    Каждая запись содержит hash, timestamp, dataset_size.
    """
    entries = list(_audit_log)[:limit]
    return {
        "total": len(_audit_log),
        "entries": entries,
    }


@router.get("/audit/verify/{record_hash}")
@limiter.limit(READ_LIGHT)
def verify_audit_entry(request: Request, record_hash: str):
    """Проверить целостность записи по её хешу."""
    for entry in _audit_log:
        if entry.get("hash") == record_hash:
            # Пересчитаем без поля hash для проверки
            check = {k: v for k, v in entry.items() if k != "hash"}
            check_str = json.dumps(check, ensure_ascii=False, sort_keys=True)
            computed = hashlib.sha256(check_str.encode()).hexdigest()
            return {
                "found": True,
                "valid": computed == record_hash,
                "timestamp": entry.get("timestamp"),
                "event_type": entry.get("event_type"),
            }
    return {"found": False, "valid": False}
