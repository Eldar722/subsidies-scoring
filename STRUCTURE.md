# 📁 Project Structure & Architecture

## Root Directory

```
subsidies-scoring/
├── .env                          # Environment config (NEVER commit)
├── .env.example                  # Template for .env
├── .gitignore                    # Git ignore rules
│
├── backend/                      # FastAPI Python backend
│   ├── main.py                   # FastAPI app entry point
│   ├── train.py                  # ML model training pipeline
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile                # Docker configuration
│   │
│   ├── core/                     # Core application logic
│   │   ├── __init__.py
│   │   ├── config.py             # Load .env variables
│   │   └── state.py              # Global app state (model, data cache)
│   │
│   ├── routers/                  # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── health.py             # GET /health
│   │   ├── metrics.py            # GET /api/metrics (model performance)
│   │   ├── producers.py          # GET /api/producers
│   │   ├── shortlist.py          # GET /api/shortlist (top-N ranking)
│   │   ├── fairness.py           # GET /api/fairness (Gini, Kruskal-Wallis)
│   │   ├── fair_rerank.py        # GET /api/shortlist/fair (fairness-aware)
│   │   ├── counterfactual.py     # GET /api/producers/{id}/counterfactual
│   │   ├── simulate.py           # POST /api/simulate (what-if analysis)
│   │   ├── drift.py              # GET /api/drift (data drift monitoring)
│   │   ├── analytics.py          # GET /api/analytics
│   │   ├── audit.py              # GET /api/audit
│   │   └── ...
│   │
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── supabase_service.py   # Supabase client wrapper
│   │   ├── gemini_advisor.py     # Gemini 2.0 Flash API integration
│   │   └── gemini.py
│   │
│   ├── middleware/               # Express-like middleware
│   │   ├── __init__.py
│   │   └── auth.py               # JWT validation
│   │
│   ├── ml/                       # Machine learning models
│   │   ├── __init__.py
│   │   ├── data_loader.py        # Load data from Excel
│   │   ├── feature_engineering.py # Extract 24 features
│   │   ├── pipeline.py           # ML training loop
│   │   ├── scoring.py            # Score new data
│   │   ├── baseline_service.py   # FCFS baseline
│   │   ├── hidden_talent_detector.py # Detect underrated producers
│   │   ├── fair_reranker.py      # Fairness-aware reranking algorithm
│   │   ├── counterfactual.py     # What-if analysis (recommendations)
│   │   ├── fairness.py           # Fairness metrics (Gini, Kruskal-Wallis)
│   │   ├── drift_monitor.py      # Detect data/model drift
│   │   ├── shap_service.py       # SHAP explainability
│   │   └── simulator_service.py  # Simulate score changes
│   │
│   ├── scripts/                  # Database utilities
│   │   ├── schema.sql            # Supabase table definitions
│   │   └── create_tables.py
│   │
│   ├── data/                     # Input data (in .gitignore)
│   │   └── subsidies.xlsx        # Source data file
│   │
│   ├── logs/                     # Application logs
│   └── model.pkl                 # Trained model (in .gitignore)
│
├── frontend/                     # React + Vite frontend
│   ├── index.html               # HTML entry point
│   ├── package.json             # Node dependencies
│   ├── vite.config.js           # Vite build config
│   ├── tailwind.config.js       # Tailwind CSS config
│   ├── .gitignore               # Frontend-specific git rules
│   │
│   ├── src/
│   │   ├── main.jsx             # React app entry
│   │   ├── App.jsx              # Root component
│   │   ├── index.css            # Global styles
│   │   │
│   │   ├── pages/               # Full page components
│   │   │   ├── DashboardPage.jsx        # Main producer ranking table
│   │   │   ├── ProducerPage.jsx         # Single producer details + SHAP
│   │   │   ├── FairnessPage.jsx         # Fairness metrics & analysis
│   │   │   ├── SimulatorPage.jsx        # What-if scenarios
│   │   │   ├── MapPage.jsx              # Regional map heatmap
│   │   │   ├── AnalyticsPage.jsx        # KPI dashboard
│   │   │   └── LoginPage.jsx            # Authentication
│   │   │
│   │   ├── components/          # Reusable UI components
│   │   │   ├── layout/          # Layout wrappers
│   │   │   │   ├── Header.jsx
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   └── ...
│   │   │   │
│   │   │   ├── charts/          # Recharts visualizations
│   │   │   │   ├── SHAPBarChart.jsx     # Feature importance
│   │   │   │   ├── LorenzChart.jsx      # Fairness curve
│   │   │   │   ├── HeatMap.jsx          # Region×Direction matrix
│   │   │   │   └── ...
│   │   │   │
│   │   │   ├── features/        # Feature-specific components
│   │   │   │   ├── ProducerTable.jsx
│   │   │   │   ├── ProducerSidePanel.jsx
│   │   │   │   ├── WeightSliders.jsx    # Simulator controls
│   │   │   │   └── GeminiAdvice.jsx     # AI recommendations
│   │   │   │
│   │   │   ├── ui/              # Generic UI components
│   │   │   │   ├── Button.jsx
│   │   │   │   ├── Card.jsx
│   │   │   │   └── ...
│   │   │   │
│   │   │   └── auth/
│   │   │       └── ProtectedRoute.jsx
│   │   │
│   │   ├── hooks/               # React custom hooks
│   │   │   ├── useProducers.js      # Fetch & cache producers
│   │   │   ├── useProducerDetail.js # Single producer details
│   │   │   ├── useShortlist.js      # Top-N ranking
│   │   │   ├── useFairness.js       # Fairness metrics
│   │   │   ├── useSimulator.js      # Simulation state
│   │   │   └── useMapRegions.js     # Geo data
│   │   │
│   │   ├── services/            # API & external services
│   │   │   ├── api.js           # Fetch wrapper for /api/*
│   │   │   └── mockApi.js       # Mock data for development
│   │   │
│   │   ├── contexts/            # React Context
│   │   │   └── AuthContext.jsx  # Authentication state
│   │   │
│   │   ├── lib/                 # Utilities
│   │   │   └── supabase.js      # Supabase client
│   │   │
│   │   ├── types/               # Type definitions
│   │   │   └── api.js           # API response types
│   │   │
│   │   ├── styles/              # CSS modules
│   │   │   └── globals.css
│   │   │
│   │   ├── assets/              # Static assets
│   │   └── public/
│   │       └── kz-regions.geojson  # Map geometry
│   │
│   └── public/
│       └── kz-regions.geojson
│
├── docs/                         # Documentation
│   ├── api-performance.md
│   ├── check_api.sh
│   └── supabase_rls.sql
│
├── ARCHITECTURE.md              # System architecture diagram
├── README.md                     # Project documentation
├── FEATURES.md                   # Feature list
└── railway.toml                 # Railway.app deployment config
```

## Data Flow

```
Excel (subsidies.xlsx)
    ↓
[train.py] → Feature Engineering (24 features)
    ↓
[GradientBoosting] → Model Training (300 trees)
    ↓
[model.pkl] Serialized
    ↓
[main.py] Startup
    ├─→ load_model() → state.py
    └─→ load_data() → state.py
    ↓
[FastAPI Routers]
    ├─→ /api/shortlist → score_dataframe() → top-N producers
    ├─→ /api/fairness → fairness metrics
    ├─→ /api/producers/{id}/counterfactual → what-if recommendations
    └─→ [All other endpoints]
    ↓
[Frontend React]
    ├─→ Fetch from /api/*
    ├─→ Render pages (Dashboard, Producer, Fairness, Simulator)
    └─→ Supabase anon key for direct DB queries (if needed)
    ↓
[User Browser]
```

## Key Components

### Backend

**state.py** - Global application state
- `MODEL_DATA`: Trained model, features, metrics
- `DF`: Loaded producer dataset (36,653 rows)
- `GROUP_STATS`: Precomputed group aggregates
- `SHAP_EXPLAINER`: Precomputed SHAP values

**scoring.py** - ML scoring logic
```python
score_dataframe(df) → Returns df with ml_score column
```

**fairness.py** - Fairness metrics
```python
compute_fairness_metrics(df) → Gini, Kruskal-Wallis, Lorenz curve
```

**fair_reranker.py** - Fairness-aware reranking
```python
compute_fair_shortlist(producers_df, group_col='region') 
  → Fair shortlist with 71% fairness improvement
```

**counterfactual.py** - What-if analysis
```python
find_counterfactual(model, x, threshold)
  → What changes could improve score?
```

### Frontend

**hooks/useProducers.js** - Data fetching & caching
- Fetches from `/api/producers`
- Caches results (5min)

**pages/DashboardPage.jsx** - Main UI
- Displays top-N producers
- Shows delta (ML rank vs FCFS rank)
- Marks hidden talents

**pages/FairnessPage.jsx** - Fairness analysis
- Gini coefficient
- Lorenz curve
- Heatmap (region × direction)

## Environment Variables

### Backend (server-side)
```
SUPABASE_URL        # PostgreSQL connection
SUPABASE_KEY        # Service role (⚠️ secret)
GEMINI_API_KEY      # Google Gemini API
GROQ_API_KEY        # Groq API for AI
MODEL_PATH          # Path to model.pkl
DATA_PATH           # Path to data file
FRONTEND_URL        # For CORS
```

### Frontend (client-side)
```
VITE_SUPABASE_URL        # Public Supabase URL
VITE_SUPABASE_ANON_KEY   # Public anon key
VITE_API_URL             # Backend API URL
```

⚠️ **Frontend NEVER gets SUPABASE_KEY** (service role)

## Deployment Targets

- **Backend**: Railway.app (Docker)
- **Frontend**: Vercel (Static hosting)
- **Database**: Supabase (PostgreSQL + Auth)
