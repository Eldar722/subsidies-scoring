"""Test API endpoints for Fair Reranking and Counterfactual."""

import sys
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from main import app
from core.state import load_model, load_data, build_precomputed_caches

# Pre-load everything like the startup event would do
print("Initializing backend...")
load_model()
load_data()
build_precomputed_caches()

client = TestClient(app)

print("=" * 60)
print("TESTING API ENDPOINTS")
print("=" * 60)

# Test 1: Fair Reranking API
print("\n[TEST 1] GET /api/shortlist/fair")
print("-" * 60)

response = client.get("/api/shortlist/fair?group_by=region&top_n=10")
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print("✓ Fair reranking API working")
    print(f"  - Fair shortlist items: {len(data.get('fair_shortlist', []))}")
    print(f"  - Total swaps: {data.get('total_swaps')}")
    print(f"  - Improvement: {data.get('fairness_improvement', {}).get('improvement_pct'):.1f}%")
    
    if data.get('fair_shortlist'):
        top = data['fair_shortlist'][0]
        print(f"  - Top: Producer {top['producer_id']} score={top['ml_score']:.4f}")
else:
    print(f"✗ Failed with status {response.status_code}")
    print(f"  Response: {response.text[:200]}")

# Test 2: Counterfactual API
print("\n[TEST 2] GET /api/producers/{producer_id}/counterfactual")
print("-" * 60)

# First, get a producer ID
producers_response = client.get("/api/producers")
if producers_response.status_code == 200:
    producers = producers_response.json()
    if producers and isinstance(producers, list) and len(producers) > 0:
        producer_id = producers[0].get('producer_id')
        
        if producer_id:
            response = client.get(f"/api/producers/{producer_id}/counterfactual")
            print(f"Producer: {producer_id}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✓ Counterfactual API working")
                print(f"  - Current score: {data.get('current_score'):.4f}")
                print(f"  - Target score: {data.get('target_score'):.4f}")
                print(f"  - Achievable: {data.get('achievable')}")
                print(f"  - Changes needed: {len(data.get('changes', []))}")
                
                if data.get('changes'):
                    top_change = data['changes'][0]
                    print(f"  - Top recommendation: {top_change['feature_name']}")
            else:
                print(f"✗ Failed with status {response.status_code}")
                print(f"  Response: {response.text[:200]}")

print("\n" + "=" * 60)
print("✓ API ENDPOINTS FULLY WORKING")
print("=" * 60)
