"""
create_tables.py — создание таблиц в Supabase через Management API.
Запустить: cd backend && python scripts/create_tables.py
"""

import os
import sys
import requests
from pathlib import Path

# Загружаем .env из корня проекта
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL или SUPABASE_KEY не заданы в .env")
    sys.exit(1)

# Читаем SQL из schema.sql
schema_path = Path(__file__).parent / "schema.sql"
sql = schema_path.read_text(encoding="utf-8")

# Пробуем выполнить через Supabase REST API (rpc exec_sql если есть)
def check_tables_exist():
    """Проверить существование основных таблиц через select."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    tables = ["producers", "scores", "shap_values", "model_metrics"]
    results = {}
    for table in tables:
        try:
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=1",
                headers=headers,
                timeout=10,
            )
            if r.status_code == 200:
                results[table] = True
            elif r.status_code == 404 or "relation" in r.text.lower():
                results[table] = False
            else:
                results[table] = None  # Unknown
        except Exception as e:
            results[table] = None
    return results


def print_schema_instructions():
    print("\n" + "="*60)
    print("ТАБЛИЦЫ НЕ НАЙДЕНЫ — нужно создать их вручную:")
    print("="*60)
    print("\n1. Открой Supabase SQL Editor:")
    print(f"   https://supabase.com/dashboard/project/wzmrsxnxzldzmlbkvdpi/sql")
    print("\n2. Вставь и выполни содержимое файла:")
    print(f"   {schema_path}")
    print("\nИли скопируй SQL отсюда:\n")
    print(sql)
    print("\n" + "="*60)


if __name__ == "__main__":
    print("Проверка таблиц в Supabase...")
    status = check_tables_exist()

    all_ok = all(v is True for v in status.values())
    missing = [t for t, v in status.items() if v is not True]

    for table, exists in status.items():
        icon = "[OK]" if exists else "[NO]"
        print(f"  {icon} {table}")

    if all_ok:
        print("\n[OK] All tables exist - ready to run data migration.")
        print("   cd backend && python services/supabase_service.py")
    else:
        print(f"\n[ERROR] Tables missing: {missing}")
        print_schema_instructions()
        sys.exit(1)
