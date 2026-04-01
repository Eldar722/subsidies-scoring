from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.state import load_model, load_data
from routers import health, metrics, producers, shortlist, fairness, simulate, drift, fair_rerank, counterfactual, pipeline
from services import gemini

app = FastAPI(title="Subsidy Scoring API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(metrics.router, prefix="/api")
app.include_router(producers.router, prefix="/api")
app.include_router(shortlist.router, prefix="/api")
app.include_router(fairness.router, prefix="/api")
app.include_router(simulate.router, prefix="/api")
app.include_router(gemini.router, prefix="/api")
app.include_router(drift.router, prefix="/api")
app.include_router(fair_rerank.router, prefix="/api")
app.include_router(counterfactual.router, prefix="/api")

app.include_router(pipeline.router, prefix="/api")

@app.on_event("startup")
async def startup():
    load_model()
    load_data()
