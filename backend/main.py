import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from core.state import load_model, load_data, build_precomputed_caches
from middleware.auth import SupabaseAuthMiddleware
from routers import (
    health, metrics, producers, shortlist, fairness,
    simulate, drift, fair_rerank, counterfactual, pipeline, audit, analytics
)
from services import gemini

# Rate limiter (защита AI endpoints от спама)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(
    title="Subsidy Scoring API",
    version="2.1.0",
    description="AI-система скоринга сельхозпроизводителей для справедливого распределения субсидий",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(metrics.router, prefix="/api")
app.include_router(producers.router, prefix="/api")
app.include_router(shortlist.router, prefix="/api")
app.include_router(fairness.router, prefix="/api")
app.include_router(simulate.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

# Инновационные фичи
app.include_router(drift.router, prefix="/api")
app.include_router(fair_rerank.router, prefix="/api")
app.include_router(counterfactual.router, prefix="/api")

# AI endpoints — с rate limiting (5 запросов к Gemini в минуту с одного IP)
app.include_router(gemini.router, prefix="/api")


@app.on_event("startup")
async def startup():
    import asyncio

    loop = asyncio.get_event_loop()

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
