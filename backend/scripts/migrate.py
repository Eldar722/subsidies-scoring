#!/usr/bin/env python3
"""
migrate.py — Unified migration runner with pre-flight checks.

Runs all SQL migration files from docs/supabase_migrations/ in order.
Each migration is executed inside a transaction (BEGIN/COMMIT/ROLLBACK).

Usage:
  cd backend && python scripts/migrate.py
  cd backend && python scripts/migrate.py --file 002_stabilize_schema.sql
  cd backend && python scripts/migrate.py --skip-preflight
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Load env
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_ROOT.parent

try:
    from dotenv import load_dotenv
    load_dotenv(_BACKEND_ROOT / ".env")
    load_dotenv(_PROJECT_ROOT / ".env", override=False)
except ImportError:
    pass

MIGRATIONS_DIR = _PROJECT_ROOT / "docs" / "supabase_migrations"


def _mask_url(url: str) -> str:
    import re
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", url)


def run_preflight_checks() -> bool:
    """Run pre-flight checks. Returns True if safe to proceed."""
    import psycopg2

    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("❌ DATABASE_URL not set — cannot proceed")
        return False

    # ── Step 1: DB connectivity ──
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        print("  ✅ Database connectivity verified")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

    # ── Step 2: Run detailed preflight ──
    try:
        sys.path.insert(0, str(_BACKEND_ROOT / "scripts"))
        from preflight import run_preflight

        result = run_preflight()

        if result["status"] == "error":
            # Check if the only error is missing tables (acceptable before migration)
            non_table_errors = [
                e for e in result["errors"]
                if "Missing tables" not in e
            ]
            if non_table_errors:
                print("\n❌ Pre-flight checks FAILED. Fix errors before migrating.")
                return False
            else:
                print("\n⚠️  Tables missing — migration will create them.")
                return True

        return True
    except Exception as e:
        print(f"❌ Pre-flight check error: {e}")
        return False


def execute_migration(sql_path: Path) -> bool:
    """Execute a single migration file inside a transaction.

    Uses BEGIN/COMMIT with ROLLBACK on error.
    Returns True on success.
    """
    import psycopg2

    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("❌ DATABASE_URL not set")
        return False

    sql = sql_path.read_text(encoding="utf-8")
    filename = sql_path.name

    print(f"\n{'─' * 50}")
    print(f"  Executing: {filename}")
    print(f"  Size: {len(sql)} bytes")
    print(f"{'─' * 50}")

    conn = None
    try:
        conn = psycopg2.connect(url, connect_timeout=30)
        # autocommit=False → everything in one transaction
        conn.autocommit = False

        with conn.cursor() as cur:
            # Explicit BEGIN for clarity (psycopg2 does this automatically)
            cur.execute("BEGIN")

        with conn.cursor() as cur:
            t0 = time.perf_counter()
            cur.execute(sql)
            elapsed = time.perf_counter() - t0

        conn.commit()
        print(f"  ✅ {filename} executed successfully ({elapsed:.2f}s)")
        return True

    except Exception as e:
        print(f"  ❌ {filename} FAILED: {e}")
        if conn:
            try:
                conn.rollback()
                print(f"  🔄 {filename} rolled back successfully")
            except Exception as rb_err:
                print(f"  ⚠️  Rollback also failed: {rb_err}")
        return False

    finally:
        if conn:
            conn.close()


def get_migration_files(specific_file: str | None = None) -> list[Path]:
    """Get ordered list of migration SQL files."""
    if not MIGRATIONS_DIR.is_dir():
        print(f"❌ Migrations directory not found: {MIGRATIONS_DIR}")
        return []

    if specific_file:
        path = MIGRATIONS_DIR / specific_file
        if not path.is_file():
            print(f"❌ Migration file not found: {path}")
            return []
        return [path]

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print(f"⚠️  No migration files found in {MIGRATIONS_DIR}")
    return files


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Run Supabase migrations")
    parser.add_argument("--file", type=str, help="Run specific migration file")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip pre-flight checks")
    args = parser.parse_args()

    print("=" * 60)
    print("  SUPABASE MIGRATION RUNNER")
    print("=" * 60)

    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        print(f"  Target: {_mask_url(url)}")
    else:
        print("  ❌ DATABASE_URL not set")
        return 1

    # Pre-flight
    if not args.skip_preflight:
        print("\n📋 Running pre-flight checks...")
        if not run_preflight_checks():
            return 1
        print("  ✅ Pre-flight checks passed")
    else:
        print("  ⚠️  Pre-flight checks skipped")

    # Get migration files
    files = get_migration_files(args.file)
    if not files:
        return 1

    print(f"\n📦 Found {len(files)} migration(s):")
    for f in files:
        print(f"    - {f.name}")

    # Execute each migration
    results = []
    for sql_file in files:
        success = execute_migration(sql_file)
        results.append((sql_file.name, success))

    # Summary
    print(f"\n{'=' * 60}")
    print("  MIGRATION SUMMARY")
    print(f"{'=' * 60}")

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)

    for name, ok in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")

    print(f"\n  Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
