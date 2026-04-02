#!/usr/bin/env python3
"""
FULL PROJECT AUDIT — Проверка реального состояния системы
"""
import sys
import os
sys.path.insert(0, '.')

print("=" * 70)
print("COMPREHENSIVE PROJECT AUDIT")
print("=" * 70)

# ============================================================================
# PHASE 1: CORE SYSTEM CHECK
# ============================================================================
print("\n[PHASE 1] Core System Initialization\n")

try:
    from core.state import load_model, load_data, build_precomputed_caches
    from core import state
    from ml.hidden_talent_detector import get_optimal_threshold
    from ml.baseline import compute_shortlist
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Load model
print("\n→ Loading model...")
load_model()
if state.MODEL_DATA:
    metrics = state.MODEL_DATA.get("metrics", {})
    print(f"  ✅ Model AUC: {metrics.get('roc_auc', 'N/A'):.4f}")
    print(f"     F1 Score: {metrics.get('best_f1', 'N/A'):.4f}")
    print(f"     Threshold: {metrics.get('optimal_threshold', 'N/A'):.4f}")
    print(f"     Train size: {metrics.get('train_size', 'N/A')}")
    print(f"     Val size: {metrics.get('val_size', 'N/A')}")
else:
    print("  ❌ Model is None")

# Load data
print("\n→ Loading data...")
load_data()
if state.DF is not None:
    total_rows = len(state.DF)
    years = state.DF['year'].unique() if 'year' in state.DF.columns else []
    print(f"  ✅ Data loaded: {total_rows} rows")
    print(f"     Years in data: {sorted(years)}")
    if 'target' in state.DF.columns:
        resolved = state.DF[state.DF['target'].notna()]
        print(f"     Resolved applications: {len(resolved)}")
        print(f"     Positive ratio: {resolved['target'].mean():.1%}")
else:
    print("  ❌ Data is None")

# Check precomputed caches
print("\n→ Building precomputed caches...")
try:
    build_precomputed_caches()
    if state.GROUP_STATS:
        print(f"  ✅ GROUP_STATS: {len(state.GROUP_STATS)} groups precomputed")
    if state.SHAP_EXPLAINER:
        print(f"  ✅ SHAP_EXPLAINER: Ready")
except Exception as e:
    print(f"  ⚠️  Cache build: {e}")

# ============================================================================
# PHASE 2: FEATURE COMPLETENESS
# ============================================================================
print("\n\n[PHASE 2] Feature Implementation Check\n")

features_checklist = {
    "ROC-AUC Metrics": "routers/metrics.py",
    "Hidden Talent Detection": "ml/hidden_talent_detector.py",
    "Fairness Module (Gini/Lorenz/KW)": "ml/fairness.py",
    "Drift Monitor": "routers/drift.py",
    "Fair Reranking": "routers/fair_rerank.py",
    "Counterfactuals": "routers/counterfactual.py",
    "SHAP Explanations": "ml/shap_service.py",
    "Gemini AI Advisor": "services/gemini_advisor.py",
    "Supabase Sync": "ml/sync_to_supabase.py",
}

for feature, file_path in features_checklist.items():
    full_path = os.path.join(".", file_path)
    if os.path.exists(full_path):
        # Check file size
        size = os.path.getsize(full_path)
        if size > 1000:
            print(f"  ✅ {feature}: {file_path} ({size} bytes)")
        else:
            print(f"  ⚠️  {feature}: {file_path} (stub, {size} bytes)")
    else:
        print(f"  ❌ {feature}: {file_path} MISSING")

# ============================================================================
# PHASE 3: API ENDPOINTS
# ============================================================================
print("\n\n[PHASE 3] API Endpoints Availability\n")

endpoints = {
    "GET /health": "health check",
    "POST /api/health/reload-model": "model reload",
    "GET /api/metrics": "model metrics vs FCFS",
    "GET /api/shortlist": "top producers",
    "GET /api/fairness": "fairness metrics",
    "GET /api/producers": "producer list",
    "GET /api/producers/{producer_id}": "producer detail",
    "GET /api/simulate": "simulator",
    "GET /api/drift": "drift monitor",
    "GET /api/fair-rerank": "fair reranking",
    "GET /api/counterfactual": "counterfactuals",
    "GET /api/analytics": "effectiveness metrics",
    "POST /api/pipeline/train": "background training",
    "GET /api/audit": "audit logs",
}

try:
    # Try to import routers to check if they exist and are syntactically OK
    from routers import health, metrics, producers, shortlist, fairness
    from routers import simulate, drift, fair_rerank, counterfactual, pipeline, audit, analytics
    print("  ✅ All router modules import successfully")
    print("\n  Available endpoints:")
    for endpoint, desc in endpoints.items():
        print(f"    • {endpoint:45} - {desc}")
except ImportError as e:
    print(f"  ❌ Router import failed: {e}")

# ============================================================================
# PHASE 4: SUPABASE INTEGRATION
# ============================================================================
print("\n\n[PHASE 4] Supabase Integration Check\n")

try:
    from core.config import SUPABASE_URL, SUPABASE_KEY
    from services.supabase_service import _get_client
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  ⚠️  SUPABASE_URL or SUPABASE_KEY not configured in .env")
    else:
        print(f"  ✅ Supabase credentials configured")
        print(f"     URL: {SUPABASE_URL[:40]}...")
        
        # Try to connect
        try:
            client = _get_client()
            # Test simple query
            result = client.table("scores").select("*", count='exact').limit(1).execute()
            if hasattr(result, 'count'):
                print(f"  ✅ Supabase connection OK, scores table has {result.count} rows")
            else:
                print(f"  ⚠️  Supabase connected but could not query scores table")
        except Exception as e:
            print(f"  ⚠️  Supabase connection failed: {str(e)[:80]}")
except Exception as e:
    print(f"  ⚠️  Supabase import failed: {e}")

# ============================================================================
# PHASE 5: ML QUALITY ASSESSMENT
# ============================================================================
print("\n\n[PHASE 5] ML Model Quality Assessment\n")

if state.MODEL_DATA and state.DF is not None:
    metrics = state.MODEL_DATA.get("metrics", {})
    
    # Distribution shift
    print("→ Distribution Shift Analysis:")
    if 'year' in state.DF.columns and 'target' in state.DF.columns:
        train_2025 = state.DF[(state.DF['year'] == 2025) & (state.DF['target'].notna())]
        val_2026 = state.DF[(state.DF['year'] == 2026) & (state.DF['target'].notna())]
        
        if len(train_2025) > 0:
            train_pos = train_2025['target'].mean()
            print(f"  Train 2025 positive ratio: {train_pos:.1%}")
        if len(val_2026) > 0:
            val_pos = val_2026['target'].mean()
            print(f"  Val 2026 positive ratio: {val_pos:.1%}")
            
            if len(train_2025) > 0 and len(val_2026) > 0:
                shift = abs(train_pos - val_pos) / train_pos if train_pos > 0 else 0
                print(f"  Distribution shift: {shift:.1%}")
                if shift > 0.2:
                    print(f"  ⚠️  LARGE SHIFT detected - model may suffer from poor generalization")
    
    # Metrics quality
    print("\n→ Model Performance Metrics:")
    auc = metrics.get('roc_auc', 0)
    f1 = metrics.get('best_f1', 0)
    threshold = metrics.get('optimal_threshold', 0.5)
    
    print(f"  ROC-AUC: {auc:.4f}" + (" ✅" if auc > 0.7 else " ⚠️ " if auc > 0.6 else " ❌"))
    print(f"  F1 Score: {f1:.4f}" + (" ✅" if f1 > 0.7 else " ⚠️ " if f1 > 0.6 else " ❌"))
    print(f"  Optimal Threshold: {threshold:.4f}")
    
    # CV vs val drop
    cv_auc = metrics.get('cv_auc_mean', 0)
    if cv_auc > 0:
        drop = (cv_auc - auc) / cv_auc * 100
        print(f"  CV AUC: {cv_auc:.4f} → Val AUC: {auc:.4f} ({drop:.1f}% drop)")
        if drop > 10:
            print(f"  ⚠️  Large validation drop - model may overfit or data distribution shifted")

# ============================================================================
# PHASE 6: DATA INTEGRITY
# ============================================================================
print("\n\n[PHASE 6] Data Integrity Check\n")

if state.DF is not None:
    df = state.DF
    
    # Check key columns
    required_cols = ['target', 'year', 'producer_id', 'Область', 'Направление водства']
    for col in required_cols:
        if col in df.columns:
            missing_pct = df[col].isna().sum() / len(df) * 100
            if missing_pct > 10:
                print(f"  ⚠️  {col}: {missing_pct:.1f}% missing")
            else:
                print(f"  ✅ {col}: {missing_pct:.1f}% missing")
        else:
            print(f"  ❌ {col}: MISSING")
    
    # Unique values
    print(f"\n→ Data Coverage:")
    print(f"  Unique producers: {df['producer_id'].nunique()}")
    print(f"  Unique regions: {df['Область'].nunique()}")
    print(f"  Unique directions: {df['Направление водства'].nunique()}")

# ============================================================================
# PHASE 7: ERROR HANDLING & FALLBACKS
# ============================================================================
print("\n\n[PHASE 7] Resilience & Fallback Logic\n")

# Check for fallback patterns in code
import subprocess
import re

files_to_check = [
    "routers/shortlist.py",
    "routers/producers.py", 
    "ml/scoring.py",
]

fallback_patterns = {
    "Supabase fallback": r"except.*:.*fallback|try.*Supabase",
    "In-memory fallback": r"state\.DF|fallback_.*\(\)",
    "Cache TTL": r"TTLCache|ttl=",
}

print("Checking error handling patterns:")
for file in files_to_check:
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_fallback = "except" in content and "fallback" in content
        has_cache = "TTLCache" in content or "cached" in content.lower()
        
        status = "✅" if (has_fallback or has_cache) else "⚠️"
        print(f"  {status} {file}: fallback={has_fallback}, caching={has_cache}")

print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
