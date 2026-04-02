#!/usr/bin/env python3
"""
post_training_sync.py — автоматизированная синхронизация после обучения

Использование:
  python post_training_sync.py --reload-model --check-sync
"""

import requests
import subprocess
import time
import sys
import argparse
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
MODEL_ENDPOINT = f"{BACKEND_URL}/api/health/reload-model"
HEALTH_ENDPOINT = f"{BACKEND_URL}/api/health"

def print_status(msg: str, level="✓"):
    emojis = {"✓": "✅", "!": "⚠️", "✗": "❌", "→": "→"}
    print(f"{emojis.get(level, level)} {msg}")

def check_backend_running():
    """Проверить, запущен ли backend"""
    try:
        resp = requests.get(HEALTH_ENDPOINT, timeout=2)
        if resp.status_code == 200:
            print_status("Backend запущен и отвечает", "✓")
            return True
    except:
        pass
    print_status("Backend НЕ запущен на localhost:8000", "✗")
    return False


def reload_model():
    """Перезагрузить модель в памяти backend"""
    print("\n📦 Перезагрузка модели...")
    try:
        resp = requests.post(MODEL_ENDPOINT, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            auc = data.get("auc", "?")
            print_status(f"Модель перезагружена | AUC={auc:.4f}", "✓")
            return True
        else:
            print_status(f"Backend вернул {resp.status_code}: {resp.text}", "!")
            return False
    except Exception as e:
        print_status(f"Ошибка при перезагрузке: {e}", "✗")
        return False


def check_sync_status():
    """Проверить синхронизацию с Supabase"""
    print("\n🔄 Проверка синхронизации с Supabase...")
    
    # Проверим Supabase данные
    try:
        from services.supabase_service import _get_client
        client = _get_client()
        
        # Получить количество записей в scores таблице
        result = client.table("scores").select("*", count='exact').limit(0).execute()
        count = result.count if hasattr(result, 'count') else 0
        
        print_status(f"Supabase scores таблица: {count} записей", "✓")
        return True
    except Exception as e:
        print_status(f"Не удалось проверить Supabase: {e}", "!")
        return False


def main():
    parser = argparse.ArgumentParser(description="Post-training synchronization")
    parser.add_argument("--reload-model", action="store_true", help="Перезагрузить модель в backend")
    parser.add_argument("--check-sync", action="store_true", help="Проверить синхронизацию Supabase")
    parser.add_argument("--wait-backend", type=int, default=0, help="Ждать backend N секунд перед проверкой")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("  📊 POST-TRAINING SYNCHRONIZATION")
    print("=" * 60)
    
    # Ждем backend если нужно
    if args.wait_backend > 0:
        print(f"\n⏱️  Ожидание {args.wait_backend}s для запуска backend...")
        for i in range(args.wait_backend, 0, -1):
            print(f"   {i}...", end="\r")
            time.sleep(1)
        print("   ✓              ")
    
    # Проверяем backend
    if not check_backend_running():
        print("\n⚠️  Перезагрузка моделей требует запущенным backend:")
        print("   cd backend && uvicorn main:app --reload")
        print("\n Запуск локально все еще может быть проверено без backend.")
        return 1
    
    # Перезагрузка модели
    if args.reload_model:
        if not reload_model():
            print("\n❌ Не удалось перезагрузить модель")
            return 1
    
    # Проверка синхронизации
    if args.check_sync:
        if not check_sync_status():
            print("\n⚠️  Синхронизация может быть недоступна")
            # Не сбиваем - это не критично
    
    print("\n" + "=" * 60)
    print("  ✅ SYNCHRONIZATION COMPLETE")
    print("=" * 60)
    print("\n💡 Тестирование:")
    print(f"   curl {HEALTH_ENDPOINT}")
    print(f"   curl http://localhost:3000/analytics")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
