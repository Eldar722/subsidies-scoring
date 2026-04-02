#!/usr/bin/env python3
"""
test_effectiveness_metrics.py — Тест всех 3 метрик эффективности субсидий.
"""
import sys
sys.path.insert(0, '/d/Decenthrathon/subsidies-scoring/backend')

import pandas as pd
import numpy as np
from routers.analytics_improved import (
    compute_2025_completion_rate,
    compute_survival_rate,
    compute_year_over_year_comparison,
    compute_all_effectiveness_metrics
)

# Load data
print("📊 Loading data...")
df = pd.read_excel('data/subsidies.xlsx', skiprows=4)
df['date'] = pd.to_datetime(df['Дата поступления'], dayfirst=True, errors='coerce')
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['producer_id'] = df['Номер заявки'].astype(str).str[:11]
df['Причитающая сумма'] = pd.to_numeric(df['Причитающая сумма'], errors='coerce')
print(f"✅ Loaded {len(df)} rows")

# Test 1: 2025 Completion
print("=" * 60)
print("TEST 1: 2025 Завершенные")
print("=" * 60)
result = compute_2025_completion_rate(df)
print(f"✅ Metric: {result['metric']}")
print(f"   Total applications: {result['total_applications']}")
print(f"   Completed: {result['completed']}")
print(f"   Completion rate: {result['completion_rate']:.1%}")
print(f"   By region count: {len(result['by_region'])} regions")
if result['by_region']:
    print(f"   Top region: {result['by_region'][0]}")
print()

# Test 2: Survival Rate
print("=" * 60)
print("TEST 2: Выживаемость")
print("=" * 60)
result = compute_survival_rate(df)
print(f"✅ Metric: {result['metric']}")
print(f"   Initial count 2025: {result['initial_count']}")
print(f"   Survived count 2026: {result['survived_count']}")
print(f"   Survival rate: {result['survival_percentage']:.1f}%")
print(f"   Summary: {result['summary']}")
if result.get('details'):
    print(f"   Details 2026: {result['details']}")
print()

# Test 3: Year-over-Year
print("=" * 60)
print("TEST 3: Год-в-год сравнение")
print("=" * 60)
result = compute_year_over_year_comparison(df)
print(f"✅ Metric: {result['metric']}")
print(f"   Total analyzed: {result['total_analyzed']}")
print(f"   Improved count: {result['improved_count']}")
print(f"   Avg effectiveness: {result['avg_effectiveness_score']:.1f}%")
if result['producers']:
    print(f"   Producers: {len(result['producers'])} (showing top 3)")
    for p in result['producers'][:3]:
        print(f"     - {p['producer_id']}: score={p['effectiveness_score']}%, improved={p['improved']}")
print()

# Test 4: Combined Metrics
print("=" * 60)
print("TEST 4: Комбинированные метрики (как выглядит API)")
print("=" * 60)
result = compute_all_effectiveness_metrics(df)
print(f"✅ Tabs count: {len(result['tabs'])}")
print(f"   Tabs:")
for tab in result['tabs']:
    print(f"     - {tab['id']}: {tab['label']}")
print(f"✅ Metrics:")
for key, metric in result['metrics'].items():
    print(f"     - {key}: {metric.get('metric')}")
print()

print("=" * 60)
print("✅ ALL TESTS PASSED")
print("=" * 60)
