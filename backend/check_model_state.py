#!/usr/bin/env python3
import joblib
import os
from datetime import datetime

model_path = 'model.pkl'
if os.path.exists(model_path):
    stat = os.stat(model_path)
    print(f'✓ Model file: {model_path}')
    print(f'  Size: {stat.st_size / 1024 / 1024:.2f} MB')
    print(f'  Modified: {datetime.fromtimestamp(os.path.getmtime(model_path))}')
    
    # Load and check metrics
    model = joblib.load(model_path)
    print(f'\n✓ Model keys: {list(model.keys())}')
    if 'metrics' in model:
        print(f'\n✓ Metrics:')
        for k, v in model['metrics'].items():
            print(f'    {k}: {v}')
    if 'artifact' in model:
        print(f'\n✓ Artifact present')
else:
    print(f'✗ Model NOT FOUND at {model_path}')
