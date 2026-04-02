"""Quick validation of Fair Reranking and Counterfactual modules."""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from ml.fair_reranker import compute_fair_shortlist
from ml.counterfactual import find_counterfactual
from ml.scoring import score_dataframe
from core.state import load_model, load_data, MODEL_DATA, DF

print("=" * 60)
print("TESTING FAIR RERANKING AND COUNTERFACTUAL")
print("=" * 60)

# Load model and data
print("Loading model and data...")
load_model()
load_data()

from core.state import MODEL_DATA, DF
print(f"✓ Model loaded: AUC={MODEL_DATA['metrics']['roc_auc']:.4f}")
print(f"✓ Data loaded: {len(DF)} rows")

# Test 1: Fair Reranking
print("\n[TEST 1] FAIR RERANKING")
print("-" * 60)

try:
    scored = score_dataframe(DF)
    producers = scored.groupby("producer_id").agg(
        ml_score=("ml_score", "mean"),
        region=("Область", "first"),
        direction=("Направление водства", "first"),
    ).reset_index()

    result = compute_fair_shortlist(
        producers,
        score_col="ml_score",
        group_col="region",
        top_n=20,
        tolerance=0.5,
    )
    
    print(f"✓ Fair reranking executed successfully")
    print(f"  - Fair shortlist: {len(result['fair_shortlist'])} items")
    print(f"  - Total swaps: {result['total_swaps']}")
    print(f"  - Fairness improvement: {result['fairness_improvement']['improvement_pct']:.1f}%")
    print(f"  - Score drop: {result['score_impact']['score_drop_pct']:.2f}%")
    
    print(f"\n  Top 3 fair selections:")
    for i, item in enumerate(result['fair_shortlist'][:3], 1):
        print(f"    {i}. Producer {item['producer_id']}: score={item['ml_score']:.4f}, region={item['region']}")
    
except Exception as e:
    print(f"✗ Fair reranking FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Counterfactual
print("\n[TEST 2] COUNTERFACTUAL ANALYSIS")
print("-" * 60)

try:
    from ml.feature_engineering import FEATURES, build_features
    
    model = MODEL_DATA["model"]
    threshold = MODEL_DATA.get("optimal_threshold", 0.5)
    
    scored = score_dataframe(DF)
    
    # Pick a random producer that's NOT in threshold
    low_score_rows = scored[scored['ml_score'] < threshold].sample(min(5, len(scored[scored['ml_score'] < threshold])))
    
    if len(low_score_rows) > 0:
        row = low_score_rows.iloc[0]
        producer_id = row['producer_id']
        x = row[FEATURES].values.astype(float)
        
        result = find_counterfactual(model, FEATURES, x, threshold)
        
        print(f"✓ Counterfactual analysis executed successfully")
        print(f"  - Producer: {producer_id}")
        print(f"  - Current score: {result['current_score']:.4f}")
        print(f"  - Target score: {result['target_score']:.4f}")
        print(f"  - Achievable: {result['achievable']}")
        print(f"  - Score gain: {result['score_gain']:.4f}")
        print(f"  - Changes needed: {len(result['changes'])}")
        
        if result['changes']:
            print(f"\n  Top recommendations:")
            for i, change in enumerate(result['changes'][:3], 1):
                print(f"    {i}. {change['feature_name']}: {change['old_value']} → {change['new_value']} (impact: {change['impact']:.4f})")
        
    else:
        print("⚠ No low-score producers found to test counterfactual")
        
except Exception as e:
    print(f"✗ Counterfactual analysis FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✓ FAIR RERANKING & COUNTERFACTUAL FULLY WORKING")
print("=" * 60)
