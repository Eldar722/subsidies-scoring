#!/usr/bin/env python3
"""Quick test of critical systems"""
import sys
sys.path.insert(0, '.')

from core.state import load_model, load_data
from core import state

print('Loading...')
load_model()
load_data()

auc = state.MODEL_DATA['metrics']['roc_auc']
print(f'✅ Model: AUC={auc:.4f}')
print(f'✅ Data: {len(state.DF)} rows')

from routers.shortlist import get_shortlist_cached
result = get_shortlist_cached(10)
print(f'✅ Shortlist: {len(result["shortlist"])} items')

from routers.metrics import metrics as get_metrics
m = get_metrics()
print(f'✅ Metrics OK')

from ml.hidden_talent_detector import get_optimal_threshold
t = get_optimal_threshold()
print(f'✅ Hidden talent threshold: {t}')

print('\n=== ALL SYSTEMS GO ===')
