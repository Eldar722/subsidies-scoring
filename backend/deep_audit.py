#!/usr/bin/env python3
"""
DEEP AUDIT - IDENTIFY CRITICAL BUGS AND GAPS
"""
import sys
import os
import json
sys.path.insert(0, '.')

print("=" * 80)
print("DEEP AUDIT: CRITICAL BUGS & GAPS ANALYSIS")
print("=" * 80)

# ============================================================================
# PROBLEM 1: SUPABASE CONNECTION ERROR
# ============================================================================
print("\n[PROBLEM 1] SUPABASE SQL ERROR\n")

try:
    from core.config import SUPABASE_URL, SUPABASE_KEY
    from supabase import create_client
    
    print(f"URL configured: {bool(SUPABASE_URL)}")
    print(f"KEY configured: {bool(SUPABASE_KEY)}")
    
    if SUPABASE_URL and SUPABASE_KEY:
        # Try direct connection
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # The issue is likely in the query syntax
        try:
            # This is what fails: select("count=exact", count='exact')
            result = client.table("scores").select("*").limit(1).execute()
            print(f"Direct query result type: {type(result)}")
            print(f"Direct query data count: {len(result.data) if result.data else 0}")
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
            print(f"\nROOT CAUSE:")
            print(f"  The query syntax 'select(\"count=exact\", count=\"exact\")' is INVALID")
            print(f"  Correct syntax should be: .select('*', count='exact')")
        
except Exception as e:
    print(f"❌ Supabase setup failed: {e}")

# ============================================================================
# PROBLEM 2: FAIR RERANKING & COUNTERFACTUALS ARE STUBS
# ============================================================================
print("\n[PROBLEM 2] STUB IMPLEMENTATIONS\n")

stub_files = {
    "routers/fair_rerank.py": "Fair reranking (critical feature)",
    "routers/counterfactual.py": "Counterfactual analysis (promised in FEATURES.md)",
}

for file_path, description in stub_files.items():
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        
        lines = content.count('\n')
        # Check if it's just minimal setup
        has_logic = 'def ' in content and len(content) > 500
        
        print(f"\n{description}: {file_path}")
        print(f"  Lines: {lines}")
        print(f"  Status: {'✅ Implemented' if has_logic else '❌ STUB'}")
        
        # Show first few lines
        print(f"  Content preview:")
        for i, line in enumerate(content.split('\n')[:10]):
            if line.strip():
                print(f"    {line}")
        
        if not has_logic:
            print(f"  ⚠️  MISSING IMPLEMENTATION - only router setup, no logic")

# ============================================================================
# PROBLEM 3: HIDDEN TALENT LOGIC - POTENTIAL BUG
# ============================================================================
print("\n[PROBLEM 3] HIDDEN TALENT DETECTION LOGIC\n")

try:
    from ml.hidden_talent_detector import detect_hidden_talents_by_delta
    from core import state
    import pandas as pd
    
    state.load_model()
    
    # Check the logic
    print("Current hidden talent logic:")
    print("  delta > 10 AND ml_score > threshold")
    print(f"  Threshold: {state.MODEL_DATA['metrics'].get('optimal_threshold', 0.5):.4f}")
    
    # This is problematic because...
    print("\n❌ POTENTIAL ISSUES:")
    print("  1. Threshold 0.7308 is VERY HIGH for 'hidden talent'")
    print("  2. Many good producers may be filtered out if ml_score < 0.73")
    print("  3. The delta > 10 threshold may be too restrictive")
    
    # Test with example data
    print("\n→ Testing with example data:")
    test_data = pd.DataFrame({
        "producer_id": ["P1", "P2", "P3", "P4", "P5"],
        "ml_score": [0.95, 0.80, 0.72, 0.65, 0.55],
        "delta": [15, 12, 14, 8, 20],
    })
    
    result = detect_hidden_talents_by_delta(test_data)
    print("  Input:")
    print(test_data.to_string(index=False))
    print("\n  Hidden talents detected:")
    hidden = test_data[result].copy()
    if len(hidden) > 0:
        print(hidden.to_string(index=False))
    else:
        print("  ⚠️  NO HIDDEN TALENTS DETECTED WITH TEST DATA")
        print("  This suggests the thresholds are too strict!")
    
except Exception as e:
    print(f"Error testing hidden talent: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# PROBLEM 4: DATA QUALITY ISSUES
# ============================================================================
print("\n[PROBLEM 4] DATA QUALITY & PREPROCESSING\n")

try:
    from core import state
    import pandas as pd
    
    state.load_data()
    df = state.DF
    
    print(f"Total rows: {len(df)}")
    print(f"Rows with target: {df['target'].notna().sum()}")
    print(f"Missing target: {df['target'].isna().sum()} ({df['target'].isna().sum()/len(df)*100:.1f}%)")
    
    # Check status distribution
    if 'Статус заявки' in df.columns:
        status_counts = df['Статус заявки'].value_counts()
        print(f"\nStatus distribution:")
        for status, count in status_counts.items():
            if status == "Исполнена":
                coded = "1 (positive)"
            elif status in ["Отклонена", "Отозвано"]:
                coded = "0 (negative)"
            else:
                coded = "?"
            print(f"  {status:15} -> {count:6} rows  {coded}")
    
    # Missing values in features
    print(f"\nMissing values in key features:")
    feature_cols = ['Причитающая сумма', 'Норматив', 'Область', 'Направление водства']
    for col in feature_cols:
        if col in df.columns:
            missing = df[col].isna().sum()
            missing_pct = missing / len(df) * 100
            print(f"  {col:25} {missing:6} ({missing_pct:5.1f}%)")

except Exception as e:
    print(f"Error analyzing data: {e}")

# ============================================================================
# PROBLEM 5: ML OVERFITTING & DISTRIBUTION SHIFT
# ============================================================================
print("\n[PROBLEM 5] MODEL OVERFITTING & DISTRIBUTION SHIFT\n")

try:
    from core import state
    
    state.load_data()
    df = state.DF
    
    print("Distribution Shift Analysis:")
    train_2025 = df[(df['year'] == 2025) & (df['target'].notna())]
    val_2026 = df[(df['year'] == 2026) & (df['target'].notna())]
    
    if len(train_2025) > 0:
        train_pos = train_2025['target'].mean()
        train_neg = 1 - train_pos
        print(f"\n2025 (Train):")
        print(f"  Positive (Исполнена):    {train_pos*100:6.1f}% ({int(len(train_2025)*train_pos)} apps)")
        print(f"  Negative (Отклон/Отозв): {train_neg*100:6.1f}% ({int(len(train_2025)*train_neg)} apps)")
        print(f"  Total: {len(train_2025)} applications")
    
    if len(val_2026) > 0:
        val_pos = val_2026['target'].mean()
        val_neg = 1 - val_pos
        print(f"\n2026 (Validation):")
        print(f"  Positive (Исполнена):    {val_pos*100:6.1f}% ({int(len(val_2026)*val_pos)} apps)")
        print(f"  Negative (Отклон/Отозв): {val_neg*100:6.1f}% ({int(len(val_2026)*val_neg)} apps)")
        print(f"  Total: {len(val_2026)} applications")
    
    if len(train_2025) > 0 and len(val_2026) > 0:
        shift = abs(train_pos - val_pos) / train_pos * 100
        print(f"\n📊 Distribution Shift: {shift:.1f}%")
        print(f"   This is a PROBLEM because:")
        print(f"   • Model trained on 82.4% positive examples")
        print(f"   • But deployment data is 51.5% positive")
        print(f"   • Threshold optimized for 82.4% may be wrong for 51.5%")
        print(f"   • This explains 16% CV→Val AUC drop")
    
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# PROBLEM 6: FEATURE USAGE CHECK
# ============================================================================
print("\n[PROBLEM 6] FEATURES & ENCODING\n")

try:
    from ml.feature_engineering import FEATURES
    import pandas as pd
    
    print(f"Number of features: {len(FEATURES)}")
    print(f"Features list:")
    
    temporal = [f for f in FEATURES if f in ['month', 'hour', 'day_of_year', 'day_of_week']]
    financial = [f for f in FEATURES if 'amount' in f or 'norm' in f or 'log' in f]
    categorical = [f for f in FEATURES if '_enc' in f]
    aggregates = [f for f in FEATURES if '_sr' in f or '_vol' in f or '_avg' in f]
    
    print(f"\n  Temporal ({len(temporal)}): {temporal}")
    print(f"  Financial ({len(financial)}): {financial}")
    print(f"  Categorical ({len(categorical)}): {categorical}")
    print(f"  Aggregates ({len(aggregates)}): {aggregates}")
    
except Exception as e:
    print(f"Error checking features: {e}")

print("\n" + "=" * 80)
print("DEEP AUDIT COMPLETE")
print("=" * 80)
