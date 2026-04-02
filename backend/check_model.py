import joblib
import os
import json
from core.config import MODEL_PATH

path = MODEL_PATH
exists = os.path.exists(path)
print(f"Model file path: {path}")
print(f"Model file exists: {exists}")

if exists:
    model_data = joblib.load(path)
    print(f"Model keys: {list(model_data.keys())}")
    
    metrics = model_data.get("metrics", {})
    print(f"\nMetrics keys: {list(metrics.keys())}")
    print(f"Full metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

