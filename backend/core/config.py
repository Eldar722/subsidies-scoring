import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
MODEL_PATH = os.getenv("MODEL_PATH", "model.pkl")
DATA_PATH = os.getenv("DATA_PATH", "data/subsidies.xlsx")
