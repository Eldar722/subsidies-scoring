"""
test_ml_improvements.py — быстрые тесты для валидации ML components без полного обучения.

Проверяет:
1. Dataset analysis работает
2. Synthetic data generation работает
3. Feature engineering совместимо
4. Calibration методы работают
5. Supabase schema ready
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_dataset_analysis():
    """Test: Dataset analysis работает."""
    print("\n[TEST 1/5] Dataset Analysis...")
    try:
        from ml.dataset_analysis import full_dataset_analysis
        from ml.data_loader import load_xlsx
        
        df = load_xlsx()
        df["target"] = np.nan
        df.loc[df["Статус заявки"].isin(["Исполнена"]), "target"] = 1
        df.loc[df["Статус заявки"].isin(["Отклонена", "Отозвано"]), "target"] = 0
        
        train_mask = df["year"] == 2025
        val_mask = df["year"] == 2026
        
        numeric_features = ["month", "hour", "day_of_year", "day_of_week", 
                          "Норматив", "Причитающая сумма"]
        cat_features = ["Область", "Направление водства", "Наименование субсидирования"]
        
        analysis = full_dataset_analysis(df, train_mask, val_mask, numeric_features, cat_features)
        
        assert "dataset_info" in analysis
        assert analysis["dataset_info"]["train_rows"] > 0
        assert "class_distribution" in analysis
        
        print("✓ PASS: Dataset analysis ok")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_synthetic_generation():
    """Test: Synthetic data generation работает."""
    print("\n[TEST 2/5] Synthetic Data Generation...")
    try:
        from ml.synthetic_data_generator import SyntheticDataGenerator
        
        # Create test data
        n_samples = 100
        X_test = np.random.randn(n_samples, 4)
        y_test = np.random.randint(0, 2, n_samples)
        y_test[0:30] = 1  # Make minority class
        
        gen = SyntheticDataGenerator(random_state=42)
        
        # Test Borderline-SMOTE
        X_syn, y_syn = gen.borderline_smote(X_test, y_test, k_neighbors=3, sampling_ratio=0.2)
        assert len(X_syn) > 0
        assert len(y_syn) > 0
        print(f"  ✓ Borderline-SMOTE: {len(X_syn)} samples")
        
        # Test Gaussian
        X_syn, y_syn = gen.gaussian_augmentation(X_test, y_test, noise_std_ratio=0.05)
        assert len(X_syn) > 0
        print(f"  ✓ Gaussian: {len(X_syn)} samples")
        
        # Test Bootstrap
        X_syn, y_syn = gen.bootstrap_sampling(X_test, y_test, n_bootstrap_ratio=0.2)
        assert len(X_syn) > 0
        print(f"  ✓ Bootstrap: {len(X_syn)} samples")
        
        print("✓ PASS: Synthetic generation ok")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_feature_engineering():
    """Test: Feature engineering совместимо."""
    print("\n[TEST 3/5] Feature Engineering...")
    try:
        from ml.data_loader import load_xlsx
        from ml.feature_engineering import build_features, FEATURES
        
        df = load_xlsx()
        df["target"] = np.nan
        df.loc[df["Статус заявки"].isin(["Исполнена"]), "target"] = 1
        df.loc[df["Статус заявки"].isin(["Отклонена", "Отозвано"]), "target"] = 0
        
        train_df = df[df["year"] == 2025].dropna(subset=["target"]).head(100).copy()
        train_df["target"] = train_df["target"].astype(int)
        
        # Build features on train
        X_train = build_features(train_df, fit=True)
        assert X_train.shape[1] == len(FEATURES)
        print(f"  ✓ Features built: {X_train.shape}")
        
        # Build features on different data (test reuse)
        test_df = df[df["year"] == 2026].dropna(subset=["target"]).head(50).copy()
        test_df["target"] = test_df["target"].astype(int)
        X_test = build_features(test_df, fit=False)
        assert X_test.shape[1] == len(FEATURES)
        print(f"  ✓ Features reused: {X_test.shape}")
        
        print("✓ PASS: Feature engineering ok")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_calibration():
    """Test: Calibration методы работают."""
    print("\n[TEST 4/5] Calibration Methods...")
    try:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.calibration import CalibratedClassifierCV
        
        # Create test data
        n_samples = 200
        X = np.random.randn(n_samples, 4)
        y = np.random.randint(0, 2, n_samples)
        
        # Train base model
        base_model = GradientBoostingClassifier(n_estimators=20, random_state=42)
        base_model.fit(X, y)
        y_proba = base_model.predict_proba(X)[:, 1]
        print(f"  ✓ Base model trained")
        
        # Test Platt Scaling (called 'sigmoid' in sklearn)
        cal_platt = CalibratedClassifierCV(base_model, method="sigmoid", cv=2)
        cal_platt.fit(X, y)
        y_cal = cal_platt.predict_proba(X)[:, 1]
        assert len(y_cal) == len(y)
        print(f"  ✓ Sigmoid/Platt scaling ok")
        
        # Test Isotonic Regression
        cal_iso = CalibratedClassifierCV(base_model, method="isotonic", cv=2)
        cal_iso.fit(X, y)
        y_cal = cal_iso.predict_proba(X)[:, 1]
        assert len(y_cal) == len(y)
        print(f"  ✓ Isotonic regression ok")
        
        print("✓ PASS: Calibration methods ok")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_supabase_schema():
    """Test: Supabase schema готова."""
    print("\n[TEST 5/5] Supabase Schema...")
    try:
        migration_file = Path("scripts/create_training_samples_table.sql")
        
        if not migration_file.exists():
            print(f"✗ FAIL: Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, encoding='utf-8') as f:
            schema = f.read()
        
        # Check key components (make sure string search accounts for formatting)
        schema_no_newlines = " ".join(schema.split())  # Normalize whitespace
        checks = [
            ("CREATE TABLE", "Table definition"),
            ("training_samples", "Table name"),
            ("is_synthetic BOOLEAN", "Synthetic flag"),
            ("synthetic_method TEXT", "Method tracking"),
            ("ALTER TABLE", "RLS enabled"),
        ]
        
        for check, desc in checks:
            if check in schema_no_newlines:
                print(f"  ✓ {desc}: ok")
            else:
                print(f"  ✗ {desc}: MISSING")
                return False
        
        print("✓ PASS: Supabase schema ready")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def main():
    print("=" * 70)
    print("ML IMPROVEMENT COMPONENTS - QUICK VALIDATION")
    print("=" * 70)
    
    tests = [
        ("Dataset Analysis", test_dataset_analysis),
        ("Synthetic Generation", test_synthetic_generation),
        ("Feature Engineering", test_feature_engineering),
        ("Calibration Methods", test_calibration),
        ("Supabase Schema", test_supabase_schema),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All components ready! You can run:")
        print("   python ml/run_ml_improvement_pipeline.py")
        return 0
    else:
        print("\n✗ Some components failed. Fix errors and retry.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
