"""
rate_limits.py — Shared rate limit definitions for all API endpoints.

Import the limiter from main.py via lazy import to avoid circular deps.
Usage in a router:
    from fastapi import Request
    from core.rate_limit import limiter

    @router.get("/endpoint")
    @limiter.limit("30/minute")
    def my_endpoint(request: Request):
        ...
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Single limiter instance — shared across all routers
limiter = Limiter(key_func=get_remote_address)


# ── Rate limit presets ──
# Format: slowapi compatible strings

READ_HEAVY = "60/minute"      # Producers list, metrics, stats
READ_LIGHT = "120/minute"     # Single producer, SHAP details
COMPUTE = "20/minute"         # Shortlist, simulation (triggers ML scoring)
WRITE = "10/minute"           # Pipeline run, model activation
AI = "5/minute"               # Gemini/Groq advice
PUBLIC = "30/minute"          # Public read-only endpoints
HEALTH = "10/minute"          # Health checks (generous enough for monitoring)
