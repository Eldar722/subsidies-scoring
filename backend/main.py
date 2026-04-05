# UTF-8 encoding fix for Windows console
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from core.config import SUPABASE_URL
from core.state import load_model, load_data, build_precomputed_caches
from middleware.auth import SupabaseAuthMiddleware
from routers import (
    health, metrics, producers, shortlist, fairness,
    simulate, drift, fair_rerank, counterfactual, pipeline, audit, analytics, validation, public,
    model_management,
)
from services import gemini

# ══════════════════════════════════════════════════════════════
# RATE LIMITING — all endpoints protected (shared limiter from core)
# ══════════════════════════════════════════════════════════════
from core.rate_limits import limiter

# ── CORS whitelist from env ──
_CORS_ORIGINS_ENV = (
    os.environ.get("CORS_ALLOWED_ORIGINS", "")
    or os.environ.get("FRONTEND_URL", "http://localhost:5173")
)
CORS_ORIGINS = [o.strip() for o in _CORS_ORIGINS_ENV.split(",") if o.strip()]

app = FastAPI(
    title="SubsidyLens API",
    version="2.2.0",
    description="SubsidyLens — скоринг и объяснимость распределения поддержки АПК (ML, SHAP, AI-советник)",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(SupabaseAuthMiddleware)


@app.middleware("http")
async def log_slow_requests(request: Request, call_next):
    t0 = time.perf_counter()
    response: Response = await call_next(request)
    elapsed = time.perf_counter() - t0
    if elapsed > 0.5:
        print(f"[SLOW] {request.method} {request.url.path} — {elapsed*1000:.0f}ms")
    return response


# Основные роутеры
app.include_router(health.router)
app.include_router(public.router)  # Public read-only endpoints (no auth required)
app.include_router(metrics.router, prefix="/api")
app.include_router(producers.router, prefix="/api")
app.include_router(shortlist.router, prefix="/api")
app.include_router(fairness.router, prefix="/api")
app.include_router(simulate.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(validation.router, prefix="/api")  # 3-Gate compliance validation

# Инновационные фичи
app.include_router(drift.router, prefix="/api")
app.include_router(fair_rerank.router, prefix="/api")
app.include_router(counterfactual.router, prefix="/api")

# Model management (version registry, activate, rollback)
app.include_router(gemini.router, prefix="/api")
app.include_router(model_management.router, prefix="/api")


@app.on_event("startup")
async def startup():
    import asyncio

    loop = asyncio.get_event_loop()

    # ── DB connectivity check at startup ──
    _check_db_connectivity()

    # ── Ensure model registry table exists ──
    try:
        from services.model_registry import ensure_registry_table
        ensure_registry_table()
    except Exception as e:
        print(f"[WARN] Model registry table check failed: {e}")

    # Load model and data synchronously (required before cache build)
    load_model()
    load_data()

    # Precompute group stats + SHAP explainer in a thread (CPU-bound, ~1-2s)
    await loop.run_in_executor(None, build_precomputed_caches)

    # Warm up shortlist cache so first real request is fast
    try:
        await loop.run_in_executor(None, producers._get_full_shortlist)
        print("[OK] Shortlist cache warmed up")
    except Exception as e:
        print(f"[WARN] Shortlist warmup failed: {e}")


def _check_db_connectivity():
    """Ping Postgres at startup. Log warning but don't crash if unavailable."""
    try:
        import psycopg2
        from core.config import DATABASE_URL
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        print("[OK] Database connectivity verified at startup")
    except ImportError:
        print("[WARN] psycopg2 not installed — skipping DB startup check")
    except Exception as e:
        print(f"[WARN] Database connectivity check failed: {e}")
        print("[WARN] API will start, but DB-dependent endpoints may fail")
