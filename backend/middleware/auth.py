"""
auth.py — Supabase JWT verification middleware.
Проверяет Bearer токен на каждом защищённом запросе.
"""

import os
import jwt
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Пути, доступные без авторизации
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/pipeline/ws",
}

PUBLIC_PREFIXES = ("/docs", "/redoc", "/openapi")

# Supabase JWT secret — берётся из SUPABASE_KEY (service_role содержит JWT_SECRET в sub)
# Для верификации пользовательских токенов используем JWT_SECRET из Supabase settings.
# Supabase подписывает токены через HS256 с JWT_SECRET.
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")


class SupabaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Пропускать публичные пути
        if path in PUBLIC_PATHS:
            return await call_next(request)
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Если JWT_SECRET не настроен — пропускаем проверку (dev mode)
        if not SUPABASE_JWT_SECRET:
            return await call_next(request)

        # Проверяем Authorization header
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
            # Добавляем user info в state запроса
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
