"""
config.py — единая конфигурация backend.

Жёсткие правила:
  - DATABASE_URL обязателен для SQL-операций
  - SUPABASE_URL + SUPABASE_KEY обязательны
  - Отсутствие любой критической переменной = FATAL ERROR (не silent fallback)
  - Пароли маскируются в логах

SUPABASE_JWT_SECRET:
  - Production: ОБЯЗАТЕЛЕН (fatal crash если нет)
  - Development: можно использовать DEV_JWT_SECRET=dev-secret для локального запуска
    (все API endpoints работают, но токены не проверяются — только для dev!)

Как получить SUPABASE_JWT_SECRET из Supabase Dashboard:
  1. Откройте https://supabase.com/dashboard
  2. Выберите проект
  3. Settings (шестерёнка внизу слева) → API
  4. Прокрутите до секции "JWT Settings"
  5. Скопируйте значение "JWT Secret" (начинается с "your-super-secret-jwt-token-...")
  6. Добавьте в backend/.env: SUPABASE_JWT_SECRET=<скопированное_значение>
"""

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

# ══════════════════════════════════════════════════════════════
# ENV LOADING
# ══════════════════════════════════════════════════════════════
# Приоритет: backend/.env → project root/.env
_backend_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_backend_env)
_root_env = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_root_env, override=False)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def _mask_url(url: str) -> str:
    """Mask password in connection string for safe logging."""
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", url)


def _require_env(name: str, *, allow_empty: bool = False) -> str:
    """Get env var or raise ValueError (FATAL — no silent fallback)."""
    val = os.getenv(name, "").strip()
    if not val and not allow_empty:
        raise ValueError(
            f"[FATAL] Environment variable '{name}' is required but not set. "
            f"Check backend/.env or project root .env."
        )
    return val


# ══════════════════════════════════════════════════════════════
# DATABASE (REQUIRED for migrations, SHAP writes, ML sync)
# ══════════════════════════════════════════════════════════════
DATABASE_URL: str = _require_env("DATABASE_URL")
print(f"[CONFIG] DATABASE = {_mask_url(DATABASE_URL)}")

# ══════════════════════════════════════════════════════════════
# SUPABASE CONFIGURATION (REQUIRED)
# ══════════════════════════════════════════════════════════════
SUPABASE_URL: str = _require_env("SUPABASE_URL")
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "").strip() or os.getenv("VITE_SUPABASE_ANON_KEY", "").strip()
# Service role key — REQUIRED for backend writes (bypasses RLS)
SUPABASE_KEY: str = _require_env("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE: str = SUPABASE_KEY  # Alias for clarity

# Fallback: anon key from SUPABASE_KEY is acceptable only for reads
if not SUPABASE_ANON_KEY:
    SUPABASE_ANON_KEY = SUPABASE_KEY
    print("[CONFIG] SUPABASE_ANON_KEY not set — using SUPABASE_KEY for reads")

print(f"[CONFIG] SUPABASE = {SUPABASE_URL}")

# ══════════════════════════════════════════════════════════════
# AI PROVIDERS (optional — graceful degradation allowed)
# ══════════════════════════════════════════════════════════════
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")

# ══════════════════════════════════════════════════════════════
# AUTH — SUPABASE_JWT_SECRET (REQUIRED in production)
# ══════════════════════════════════════════════════════════════
# Strategy:
#   1. If SUPABASE_JWT_SECRET is set → use it (production)
#   2. If DEV_JWT_SECRET is set → use it + warn (development)
#   3. If neither is set → FATAL crash with instructions
# ══════════════════════════════════════════════════════════════

_JWT_INSTRUCTIONS = """
═══════════════════════════════════════════════════════════════
 SUPABASE_JWT_SECRET — как получить:

  1. Откройте https://supabase.com/dashboard
  2. Выберите ваш проект
  3. Settings (⚙️ внизу слева) → API
  4. Прокрутите до "JWT Settings"
  5. Скопируйте "JWT Secret"
  6. Добавьте в backend/.env:

     SUPABASE_JWT_SECRET=ваш_секрет_из_dashboard

  ИЛИ для локальной разработки (НЕ production!):

     DEV_JWT_SECRET=dev-secret
═══════════════════════════════════════════════════════════════
"""


_jwt_from_env = os.getenv("SUPABASE_JWT_SECRET", "").strip()
_dev_jwt = os.getenv("DEV_JWT_SECRET", "").strip()

if _jwt_from_env:
    # Production: реальный секрет из Supabase
    SUPABASE_JWT_SECRET: str = _jwt_from_env
    print(f"[CONFIG] SUPABASE_JWT_SECRET = {'*' * 8}**** (production)")
elif _dev_jwt:
    # Development: явный dev-секрет с предупреждением
    SUPABASE_JWT_SECRET = _dev_jwt
    print("[CONFIG] [WARN] DEV_JWT_SECRET is set — auth runs in DEV mode (no JWT verification)")
    print("         For production: set SUPABASE_JWT_SECRET from Supabase Dashboard")
else:
    # FATAL — нет ни реального секрета, ни dev-флага
    print(_JWT_INSTRUCTIONS, file=sys.stderr)
    raise ValueError(
        "[FATAL] SUPABASE_JWT_SECRET не установлен. "
        "Это обязательная переменная для production. "
        "Для локальной разработки добавьте DEV_JWT_SECRET=dev-secret в backend/.env "
        "См. инструкцию выше."
    )

# ══════════════════════════════════════════════════════════════
# PATHS & MISC
# ══════════════════════════════════════════════════════════════
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
MODEL_PATH = os.getenv("MODEL_PATH", "model.pkl")
DATA_PATH = os.getenv("DATA_PATH", "data/subsidies.xlsx")
