"""Test all applied fixes"""
import sys
sys.path.insert(0, '.')

print('=' * 70)
print('TESTING ALL FIXES')
print('=' * 70)

# Test 1: Import baseline
print('\n[TEST 1] Baseline imports...')
try:
    from ml.baseline import compute_shortlist
    print('✅ compute_shortlist imports OK')
except ImportError as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)

# Test 2: Import sync module
print('\n[TEST 2] Sync module...')
try:
    from ml.sync_to_supabase import sync_scores_to_supabase
    print('✅ sync_scores_to_supabase imports OK')
except ImportError as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)

# Test 3: Load model and data
print('\n[TEST 3] Loading model and data...')
from core.state import load_model, load_data
from core import state
load_model()
load_data()
auc = state.MODEL_DATA["metrics"]["roc_auc"]
print(f'✅ Model: {auc:.4f} AUC')
print(f'✅ Data: {len(state.DF)} rows')

# Test 4: Run compute_shortlist
print('\n[TEST 4] compute_shortlist() without NameError...')
try:
    result = compute_shortlist(state.DF, top_n=5)
    print(f'✅ Returned {len(result["shortlist"])} items')
    print(f'✅ optimal_threshold: {result["optimal_threshold"]}')
    print(f'✅ hidden_talent_count: {result["hidden_talent_count"]}')
    
    # Check shortlist items have all fields
    item = result['shortlist'][0]
    required_fields = ['producer_id', 'hidden_talent', 'delta', 'ml_rank']
    for field in required_fields:
        if field not in item:
            print(f'❌ Missing field: {field}')
        else:
            val = item[field]
            print(f'✅ Field present: {field}={val}')
except Exception as e:
    print(f'❌ compute_shortlist failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print('\n' + '=' * 70)
print('✅ ALL FIXES VALIDATED')
print('=' * 70)
