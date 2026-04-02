# 🌾 Subsidy Scoring System

> **Decentrathon 5.0 · AI for Government**  
> ML-ranking system for fair distribution of government subsidies to livestock producers in Kazakhstan.

## ⚡ Status: ✅ Production Ready (9/10)

- ✅ Model: AUC=0.7605 (+23% vs FCFS baseline)
- ✅ 13 API endpoints working
- ✅ Fair reranking: 71.3% fairness improvement
- ✅ Counterfactual: What-if recommendations
- ✅ Zero crashes, full error handling

## 🎯 Quick Summary

**Problem**: FCFS (First-Come-First-Served) wastes ~7 billion ₸ annually  
**Solution**: ML-ranking on 24 engineered features  
**Result**: Data-driven, transparent, fair subsidy distribution

## 🚀 Quick Start (5 minutes)

### Backend

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env  # Edit with your credentials
python train.py              # Train model
uvicorn main:app --reload    # Start API
# API: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# UI: http://localhost:5173
```

### First Checks

```bash
# Backend
curl http://localhost:8000/health

# API Docs
open http://localhost:8000/docs

# Frontend
open http://localhost:5173
```

## 📊 Features

| Feature | Status |
|---------|--------|
| ML Ranking | ✅ AUC=0.7605 |
| SHAP Explainability | ✅ Feature importance breakdown |
| Fairness Metrics | ✅ Gini, Kruskal-Wallis, Lorenz |
| Fair Reranking | ✅ 71% representation improvement |
| Counterfactual Analysis | ✅ What-if recommendations |
| Hidden Talent Detection | ✅ Find underrated producers |
| AI Advisor | ✅ Gemini 2.0 Flash (Russian) |
| Simulator | ✅ Live what-if scenarios |

## 📁 Project Structure

```
backend/
  ├── main.py                 # FastAPI server
  ├── train.py                # ML pipeline
  ├── core/config.py          # Load .env
  ├── core/state.py           # Global state (model, data cache)
  ├── routers/                # API endpoints (13 total)
  ├── ml/                      # ML algorithms
  │   ├── scoring.py          # Score producers
  │   ├── fairness.py         # Fairness metrics
  │   ├── fair_reranker.py    # Fair reranking
  │   └── counterfactual.py   # What-if analysis
  └── data/subsidies.xlsx     # Input dataset

frontend/
  ├── src/pages/              # Dashboard, Producer, Fairness, etc.
  ├── src/hooks/              # useProducers, useFairness, etc.
  ├── src/components/         # UI components
  └── package.json

.env                          # Secrets (DO NOT COMMIT)
.env.example                  # Template
```

See [STRUCTURE.md](./STRUCTURE.md) for full layout.

## 🔐 Environment Variables

### Backend Server

```env
# Database
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJh...                      # Service role (⚠️ SECRET)

# AI Providers
AI_PROVIDER=groq                           
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...

# Config
FRONTEND_URL=http://localhost:5173
MODEL_PATH=model.pkl
DATA_PATH=data/subsidies.xlsx
```

### Frontend Client

```env
# Public (safe to expose)
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJh...
VITE_API_URL=http://localhost:8000
```

⚠️ **Security**: `SUPABASE_KEY` (service role) NEVER goes to frontend!

See [.env.example](./.env.example) for complete template.

## 📡 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Server status |
| `/api/metrics` | GET | Model performance (AUC, F1) |
| `/api/shortlist?top_n=20` | GET | Top-N producers + delta |
| `/api/fairness` | GET | Fairness metrics & heatmap |
| `/api/shortlist/fair?group_by=region` | GET | Fair-balanced ranking |
| `/api/producers/{id}/counterfactual` | GET | What-if recommendations |
| `/api/producers/{id}` | GET | Single producer profile |
| `/docs` | GET | Swagger API documentation |

## 🧠 ML Model

**Algorithm**: GradientBoosting (300 trees)  
**Features**: 24 engineered (temporal, financial, geographic, aggregates)  
**Training**: 24,653 apps (2025)  
**Validation**: 1,332 apps (2026)  
**Calibration**: Isotonic regression  
**Performance**: 
- 5-Fold CV AUC: 0.8499 ± 0.0024
- Hold-out AUC: 0.7605 (+23% vs FCFS baseline)

## 🎨 UI Pages

1. **Dashboard** - Top-N producers table with delta & hidden talents
2. **Producer** - SHAP breakdown + AI advice + history
3. **Fairness** - Gini + Lorenz curve + heatmap (region×direction)
4. **Simulator** - Sliders to test "what-if" scenarios
5. **Map** - Regional choropleth of Kazakhstan

## 🚀 Deployment

### Backend → Railway

```bash
# Set env vars in Railway dashboard:
SUPABASE_URL
SUPABASE_KEY
GEMINI_API_KEY
# Deploy: git push origin main
```

### Frontend → Vercel

```bash
# Set env vars in Vercel project:
VITE_SUPABASE_URL
VITE_SUPABASE_ANON_KEY
VITE_API_URL
# Deploy: git push origin main
```

## ❓ Troubleshooting

**Backend won't start**
```bash
python backend/check_model_state.py
curl http://localhost:8000/health
```

**Frontend can't connect API**
```bash
# Check VITE_API_URL in .env
# Backend must be running on port 8000
curl http://localhost:8000/health
```

**Model/data not loading**
```bash
python backend/validate_critical.py
```

## 📚 More Info

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [STRUCTURE.md](./STRUCTURE.md) - Project layout  
- [FEATURES.md](./FEATURES.md) - Feature specs
- [backend/README.md](./backend/README.md) - Backend guide
- [frontend/README.md](./frontend/README.md) - Frontend guide

## 🤝 Use Cases

### Ministry of Agriculture
Receive ranked list of top-20 producers with fairness metrics for subsidy commission.

### Regional Akimat
Review individual producer: SHAP breakdown + AI recommendation + ML vs FCFS comparison.

### Policy Analyst
Check fairness: Gini coefficient, Kruskal-Wallis test, region×direction heatmap for bias.

### Budget Director
Simulate scenarios: "What if we prioritize small farms? Young farmers? Specific regions?"

## 📊 Data

| Stat | Value |
|------|-------|
| Applications | 36,653 |
| Unique Producers | 15,009 |
| Regions | 18 |
| Livestock Types | 9 |
| Date Range | Jan 2025 — Mar 2026 |

## 🔒 Security & Privacy

- ✅ Data processed locally (not sent to external services except Gemini)
- ✅ Producer IDs anonymized (first 11 digits of application number)
- ✅ Designed for human-in-the-loop (final decision stays with ministry)
- ✅ Ready for deployment in protected government environment

## ⚠️ Limitations

1. **Cold-start**: New producers default to regional/directional benchmarks
2. **Distribution shift**: 2026 data more competitive (82%→51% success rate)
3. **Domain-specific**: Tuned for livestock farming only

---

**Ready to deploy!** 🚀  
Questions? Check [STRUCTURE.md](./STRUCTURE.md) or [.env.example](./.env.example)
