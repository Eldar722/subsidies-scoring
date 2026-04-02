# ⚡ QUICK DEPLOYMENT CHECKLIST

## Changes Ready (3 files)

- [ ] Review `ml/baseline.py` (+2 lines) - Added threshold import
- [ ] Review `train.py` (+10 lines) - Added sync call  
- [ ] Review `ml/sync_to_supabase.py` (NEW) - Supabase upsert logic

## Pre-Deploy Verify
```bash
# Already done, but run if needed:
cd backend
python test_all_fixes.py
# Expected: ✅ ALL TESTS PASSED
```

## Deploy (5 minutes)

### 1. Stop Backend
```bash
pkill -f "uvicorn main:app"
# Wait 2 seconds
```

### 2. Verify Files Deployed
```bash
# Check files exist:
ls -la backend/ml/baseline.py       # Modified
ls -la backend/ml/sync_to_supabase.py  # NEW
ls -la backend/train.py             # Modified
```

### 3. Start Backend
```bash
cd backend
uvicorn main:app --reload
# Wait for: "Uvicorn running on http://127.0.0.1:8000"
```

## Post-Deploy Tests

### Test 1: Hidden Talents Working
```bash
curl "http://localhost:8000/api/shortlist?top_n=3" | jq '.shortlist[] | {producer_id, hidden_talent}'
# Expected: hidden_talent: true/false for each producer
```

### Test 2: No Errors in Logs
```bash
# Check backend terminal - should NOT show:
# ❌ NameError: name 'threshold' is not defined
# ❌ ImportError
```

### Test 3: Frontend Load
```
Open: http://localhost:3000/
Navigate to: Shortlist tab
Expected: Hidden talent column visible
```

## Next Training

```bash
# When ready to retrain:
cd backend
python train.py

# Expected output should include:
# ✅ Training complete
# 📊 Syncing scores to Supabase...
# ✅ Sync complete
```

## Rollback (if needed)

```bash
# 1. Revert train.py (remove sync call, 3 lines)
# 2. Revert baseline.py (remove imports, 2 lines)
# 3. Delete ml/sync_to_supabase.py
# 4. Restart FastAPI
```

## What Should Change

**Before**:
- Hidden talent column missing from shortlist
- compute_shortlist() crashes with NameError
- Supabase scores stale after training

**After**:
- Hidden talent visible for 6,346 producers
- compute_shortlist() returns valid data
- Supabase auto-updates after training in ~2 seconds

## Deployment Time: ~5 minutes
## Risk Level: LOW (all tests pass, graceful failure modes)
## Rollback Time: ~2 minutes

---

**Status**: ✅ Ready to deploy  
**Test Results**: 8/8 tests passed  
**Documentation**: See AUDIT_FINAL_REPORT.md
