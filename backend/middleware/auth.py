"""
auth.py — Supabase JWT verification middleware.
Проверяет Bearer токен на каждом защищённом запросе.

SUPABASE_JWT_SECRET is required at startup (config.py raises ValueError if missing).

DEV MODE: If DEV_JWT_SECRET was used (detected via dev-secret value),
all protected routes pass through WITHOUT JWT verification.
This is intentional for local development — NEVER use in production!
"""

import os
import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import SUPABASE_JWT_SECRET

# Detect dev mode: if the secret is a known dev value
DEV_MODE = os.getenv("DEV_JWT_SECRET", "").strip() == SUPABASE_JWT_SECRET

# Пути, доступные без авторизации
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/pipeline/ws",
    "/api/pipeline/status",
    "/api/pipeline/run",
    # Model management — can be accessed without auth for monitoring
    "/api/models",
    "/api/models/active",
    "/api/models/auto-rollback",
}

PUBLIC_PREFIXES = ("/docs", "/redoc", "/openapi", "/public")


class SupabaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Пропускать публичные пути
        if path in PUBLIC_PATHS:
            return await call_next(request)
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # DEV MODE bypass: skip JWT verification for local development
        if DEV_MODE:
            request.state.user_id = "dev-user"
            request.state.user_email = "dev@localhost"
            return await call_next(request)

        # Production: verify JWT token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Требуется авторизация. Войдите в систему."},
            )

        token = auth_header[len("Bearer "):]
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            request.state.user_id = payload.get("sub")
            request.state.user_email = payload.get("email", "")
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Сессия истекла. Войдите снова."},
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Недействительный токен. Войдите снова."},
            )

        return await call_next(request)
