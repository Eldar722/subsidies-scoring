#!/usr/bin/env python3
"""
preflight.py — Pre-flight database checks before any migration or ML sync.

Checks:
  1. DATABASE_URL exists and is valid format
  2. Postgres connection succeeds
  3. Required tables exist
  4. Schema integrity (critical columns present)
  5. Row count warnings for empty critical tables

Usage:
  python scripts/preflight.py
  
Returns exit code 0 on success, 1 on failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Load env
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_BACKEND_ROOT / ".env")
    load_dotenv(_BACKEND_ROOT.parent / ".env", override=False)
except ImportError:
    pass


# ══════════════════════════════════════════════════════════════
# EXPECTED SCHEMA
# ══════════════════════════════════════════════════════════════
REQUIRED_TABLES = {
    "producers": ["producer_id", "region", "direction"],
    "scores": ["producer_id", "ml_score", "ml_rank", "fcfs_rank", "delta", "hidden_talent"],
    "shap_values": ["producer_id", "feature", "shap_value"],
    "model_metrics": ["run_id", "roc_auc"],
}

# Tables that should have data (warning only, not fatal)
EXPECTED_POPULATED = ["producers", "scores"]


def _mask_url(url: str) -> str:
    import re
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", url)


def check_database_url() -> tuple[bool, str]:
    """Check DATABASE_URL exists and has valid format."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return False, "DATABASE_URL is not set"
    if not url.startswith("postgresql://"):
        return False, f"DATABASE_URL has invalid format (expected postgresql://...)"
    return True, f"DATABASE_URL = {_mask_url(url)}"


def check_postgres_connection() -> tuple[bool, str]:
    """Test actual Postgres connectivity."""
    url = os.environ.get("DATABASE_URL", "").strip()
    try:
        import psycopg2
    except ImportError:
        return False, "psycopg2 not installed (pip install psycopg2-binary)"

    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        # Truncate version string
        short_version = version.split(",")[0] if "," in version else version[:60]
        return True, f"Connected: {short_version}"
    except Exception as e:
        return False, f"Connection failed: {e}"


def check_tables_exist() -> tuple[bool, str, list[str]]:
    """Verify required tables exist."""
    url = os.environ.get("DATABASE_URL", "").strip()
    import psycopg2

    conn = psycopg2.connect(url, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    existing = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()

    missing = [t for t in REQUIRED_TABLES if t not in existing]
    if missing:
        return False, f"Missing tables: {missing}", missing
    return True, f"All {len(REQUIRED_TABLES)} required tables exist", []


def check_schema_integrity() -> tuple[bool, str, list[str]]:
    """Verify critical columns exist in each table."""
    url = os.environ.get("DATABASE_URL", "").strip()
    import psycopg2

    conn = psycopg2.connect(url, connect_timeout=10)
    cur = conn.cursor()

    issues = []
    for table, expected_cols in REQUIRED_TABLES.items():
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = %s
        """, (table,))
        actual_cols = {row[0] for row in cur.fetchall()}

        for col in expected_cols:
            if col not in actual_cols:
                issues.append(f"{table}.{col} missing")

    cur.close()
    conn.close()

    if issues:
        return False, f"Schema issues: {issues}", issues
    return True, "Schema integrity OK", []


def check_row_counts() -> tuple[bool, str, dict]:
    """Check row counts for critical tables (warning only)."""
    url = os.environ.get("DATABASE_URL", "").strip()
    import psycopg2

    conn = psycopg2.connect(url, connect_timeout=10)
    cur = conn.cursor()

    counts = {}
    warnings = []
    for table in REQUIRED_TABLES:
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cur.fetchone()[0]
            counts[table] = count
            if table in EXPECTED_POPULATED and count == 0:
                warnings.append(f"{table} is empty (0 rows)")
        except Exception as e:
            counts[table] = -1
            warnings.append(f"{table}: {e}")

    cur.close()
    conn.close()

    ok = len(warnings) == 0
    msg = ", ".join(f"{t}={c}" for t, c in counts.items())
    return ok, f"Row counts: {msg}", counts


def run_preflight() -> dict:
    """Run all pre-flight checks.
    
    Returns:
        {
            "status": "ok" | "error",
            "checks": [{"name": str, "passed": bool, "message": str}],
            "errors": [str],
            "warnings": [str],
        }
    """
    checks = []
    errors = []
    warnings = []

    # 1. DATABASE_URL format
    ok, msg = check_database_url()
    checks.append({"name": "database_url", "passed": ok, "message": msg})
    if not ok:
        errors.append(msg)
        # Can't continue without DATABASE_URL
        return {"status": "error", "checks": checks, "errors": errors, "warnings": warnings}

    # 2. Postgres connection
    ok, msg = check_postgres_connection()
    checks.append({"name": "postgres_connection", "passed": ok, "message": msg})
    if not ok:
        errors.append(msg)
        return {"status": "error", "checks": checks, "errors": errors, "warnings": warnings}

    # 3. Required tables
    ok, msg, missing = check_tables_exist()
    checks.append({"name": "tables_exist", "passed": ok, "message": msg})
    if not ok:
        errors.append(msg)
        # Tables missing = schema not initialized. Not fatal if we're about to migrate.
        warnings.append(f"Missing tables will be created by migration: {missing}")

    # 4. Schema integrity (only if tables exist)
    if ok:
        schema_ok, schema_msg, issues = check_schema_integrity()
        checks.append({"name": "schema_integrity", "passed": schema_ok, "message": schema_msg})
        if not schema_ok:
            warnings.append(schema_msg)

    # 5. Row counts
    try:
        rows_ok, rows_msg, counts = check_row_counts()
        checks.append({"name": "row_counts", "passed": rows_ok, "message": rows_msg})
        if not rows_ok:
            warnings.append(rows_msg)
    except Exception as e:
        checks.append({"name": "row_counts", "passed": False, "message": str(e)})

    status = "error" if errors else "ok"
    return {"status": status, "checks": checks, "errors": errors, "warnings": warnings}


def main() -> int:
    print("=" * 60)
    print("  PRE-FLIGHT DATABASE CHECKS")
    print("=" * 60)

    result = run_preflight()

    for check in result["checks"]:
        icon = "✅" if check["passed"] else "❌"
        print(f"  {icon} {check['name']}: {check['message']}")

    if result["warnings"]:
        print(f"\n  ⚠️  Warnings:")
        for w in result["warnings"]:
            print(f"    - {w}")

    if result["errors"]:
        print(f"\n  ❌ ERRORS (blocking):")
        for e in result["errors"]:
            print(f"    - {e}")

    print(f"\n  Status: {result['status'].upper()}")
    print("=" * 60)

    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
