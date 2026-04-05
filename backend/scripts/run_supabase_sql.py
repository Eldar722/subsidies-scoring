#!/usr/bin/env python3
"""
Выполнить SQL-файл против Postgres Supabase по DATABASE_URL (URI из Dashboard → Settings → Database).

Пример (PowerShell):
  $env:DATABASE_URL = "postgresql://postgres.xxx:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
  python backend/scripts/run_supabase_sql.py ../../docs/supabase_migrations/001_shap_unique_gemini_advice_json.sql

Требуется: pip install psycopg2-binary
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Подхват DATABASE_URL из backend/.env (без вывода секрета)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND_ROOT / ".env")
    load_dotenv(_BACKEND_ROOT.parent / ".env")
except ImportError:
    pass


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: run_supabase_sql.py <path-to.sql>")
        return 2

    sql_path = Path(sys.argv[1]).resolve()
    if not sql_path.is_file():
        print(f"File not found: {sql_path}")
        return 2

    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("Set DATABASE_URL or SUPABASE_DB_URL (Postgres connection string).")
        return 1

    try:
        import psycopg2
    except ImportError:
        print("Install: pip install psycopg2-binary")
        return 1

    sql = sql_path.read_text(encoding="utf-8")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print(f"OK: executed {sql_path.name}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
