import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корня монорепо (на уровень выше backend/)
_root_env = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_root_env)
# Фолбэк: локальный backend/.env (если есть)
load_dotenv(override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
MODEL_PATH = os.getenv("MODEL_PATH", "model.pkl")
DATA_PATH = os.getenv("DATA_PATH", "data/subsidies.xlsx")
