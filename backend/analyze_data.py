import pandas as pd
import numpy as np
from ml.data_loader import load_xlsx
import os
import json

# Load data
print("Loading dataset...")
df = load_xlsx("data/subsidies.xlsx")
print(f"Dataset shape: {df.shape}")

# Prepare target
POSITIVE = ["Исполнена"]
NEGATIVE = ["Отклонена", "Отозвано"]
df["target"] = np.nan
df.loc[df["Статус заявки"].isin(POSITIVE), "target"] = 1
df.loc[df["Статус заявки"].isin(NEGATIVE), "target"] = 0

resolved = df.dropna(subset=["target"]).copy()
resolved["target"] = resolved["target"].astype(int)

print(f"\nTarget distribution:")
print(resolved["target"].value_counts())
print(f"Class balance: {resolved['target'].mean():.2%} positive")

# Split by year
train = resolved[resolved["year"] == 2025].copy()
val = resolved[resolved["year"] == 2026].copy()
print(f"\nTrain (2025): {len(train)} samples")
print(f"Val (2026): {len(val)} samples")
print(f"Train positive rate: {train['target'].mean():.2%}")
print(f"Val positive rate: {val['target'].mean():.2%}")

# Check for missing values
print(f"\nMissing values in key columns:")
key_cols = ["Причитающая сумма", "Норматив", "Область", "Направление водства", "Наименование субсидирования", "Район хозяйства"]
for col in key_cols:
    missing = df[col].isna().sum()
    print(f"  {col}: {missing} ({missing/len(df)*100:.1f}%)")

# Feature correlation with target (numeric only)
from ml.feature_engineering import build_features, FEATURES
print("\nBuilding features for correlation analysis...")
X_train = build_features(train, fit=True)
y_train = train["target"]

# Calculate correlations
correlations = {}
for col in FEATURES:
    if col in X_train.columns:
        corr = np.corrcoef(X_train[col], y_train)[0,1]
        correlations[col] = abs(corr) if not np.isnan(corr) else 0

# Sort by correlation
sorted_corr = sorted(correlations.items(), key=lambda x: x[1], reverse=True)
print("\nTop 10 features by correlation with target:")
for feat, corr in sorted_corr[:10]:
    print(f"  {feat}: {corr:.4f}")

print("\nBottom 10 features by correlation with target:")
for feat, corr in sorted_corr[-10:]:
    print(f"  {feat}: {corr:.4f}")

# Check for leakage: features that might directly indicate target
print("\nChecking for potential leakage features...")
# Look at original columns that might be too predictive
suspicious_cols = ["Статус заявки", "Дата поступления", "Номер заявки"]
for col in suspicious_cols:
    if col in df.columns:
        print(f"  {col}: present in raw data")

# Save analysis results
analysis_results = {
    "dataset_shape": df.shape,
    "target_distribution": resolved["target"].value_counts().to_dict(),
    "train_size": len(train),
    "val_size": len(val),
    "train_positive_rate": train["target"].mean(),
    "val_positive_rate": val["target"].mean(),
    "missing_values": {col: int(df[col].isna().sum()) for col in key_cols},
    "feature_correlations": dict(sorted_corr[:15]),
}

# Ensure we're in the right directory
output_path = os.path.join(os.getcwd(), "data_analysis.json")
with open(output_path, "w") as f:
    json.dump(analysis_results, f, indent=2)
print(f"\nAnalysis saved to {output_path}")