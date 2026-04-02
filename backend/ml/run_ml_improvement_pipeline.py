#!/usr/bin/env python3
"""
run_ml_improvement_pipeline.py — мастер-скрипт для запуска полного pipeline улучшения модели.

Последовательно:
1. Анализирует текущий датасет
2. Генерирует синтетические данные
3. Обучает новую модель с calibration
4. Сравнивает метрики
5. Показывает рекомендации
"""

import sys
import os
import json
from pathlib import Path
import argparse
from datetime import datetime

# Add backend to path so imports work from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

# ═══════════════════════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def run_pipeline(use_synthetic: bool = True,
                synthetic_ratio: float = 0.3,
                save_to_supabase: bool = False,
                verbose: bool = True):
    """Запустить full pipeline."""
    
    print("\n" + "=" * 80)
    print("ML MODEL IMPROVEMENT PIPELINE")
    print("=" * 80)
    print(f"Start time: {datetime.now().isoformat()}")
    print()
    
    # ════ STEP 1: Dataset Analysis ════
    print("\n" + "─" * 80)
    print("STEP 1: Dataset Analysis")
    print("─" * 80)
    
    try:
        from ml.data_loader import load_xlsx
        from ml.dataset_analysis import full_dataset_analysis
        import numpy as np
        import pandas as pd
        
        df = load_xlsx()
        print("✓ Loaded raw dataset")
        
        # Prepare
        df["target"] = np.nan
        df.loc[df["Статус заявки"].isin(["Исполнена"]), "target"] = 1
        df.loc[df["Статус заявки"].isin(["Отклонена", "Отозвано"]), "target"] = 0
        
        train_mask = df["year"] == 2025
        val_mask = df["year"] == 2026
        
        numeric_features = [
            "month", "hour", "day_of_year", "day_of_week",
            "Норматив", "Причитающая сумма"
        ]
        cat_features = ["Область", "Направление водства", "Наименование субсидирования"]
        
        analysis = full_dataset_analysis(df, train_mask, val_mask, numeric_features, cat_features)
        
        print(f"\n📊 Dataset Stats:")
        print(f"  Total samples: {analysis['dataset_info']['total_rows']}")
        print(f"  Train (2025):  {analysis['dataset_info']['train_rows']} | pos_rate={analysis['class_distribution']['train'].get('1', 0):.1%}")
        print(f"  Val (2026):    {analysis['dataset_info']['val_rows']} | pos_rate={analysis['class_distribution']['val'].get('1', 0):.1%}")
        print(f"  Class imbalance ratio (train): {analysis['class_imbalance_ratio']['train']:.2f}x")
        
        # Save analysis
        with open("data_analysis_baseline.json", "w") as f:
            json.dump(analysis, f, indent=2)
        print("\n✓ Saved: data_analysis_baseline.json")
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ════ STEP 2: Synthetic Data Generation ════
    print("\n" + "─" * 80)
    print("STEP 2: Synthetic Data Generation")
    print("─" * 80)
    
    if use_synthetic:
        try:
            from ml.synthetic_data_generator import generate_synthetic_training_data
            
            train_df = df[train_mask].dropna(subset=["target"]).copy()
            train_df["target"] = train_df["target"].astype(int)
            
            print(f"\nGenerating synthetic data (ratio={synthetic_ratio:.1%})...")
            
            df_synthetic = generate_synthetic_training_data(
                train_df, numeric_features, cat_features,
                methods=["borderline_smote", "gaussian", "bootstrap"],
                verbose=True
            )
            
            print(f"\n✓ Synthetic data generated: {len(df_synthetic)} samples")
            
            # Save for inspection
            df_synthetic.to_csv("synthetic_samples_generated.csv", index=False)
            print("✓ Saved: synthetic_samples_generated.csv")
            
        except Exception as e:
            print(f"\n[WARN] Synthetic data generation failed: {e}")
            import traceback
            traceback.print_exc()
            use_synthetic = False
    else:
        print("Skipping synthetic data generation (use_synthetic=False)")
    
    # ════ STEP 3: Enhanced Model Training ════
    print("\n" + "─" * 80)
    print("STEP 3: Enhanced Model Training with Calibration")
    print("─" * 80)
    
    try:
        from ml.enhanced_training_pipeline import run_enhanced_pipeline
        
        print("\nRunning enhanced pipeline...")
        
        results = run_enhanced_pipeline(
            use_synthetic=use_synthetic,
            synthetic_ratio=synthetic_ratio,
            calibration_methods=["sigmoid", "isotonic"],
            verbose=verbose
        )
        
        print("\n✓ Model training completed")
        
        # Save results
        model_results = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "use_synthetic": use_synthetic,
                "synthetic_ratio": synthetic_ratio,
                "calibration_methods": ["platt", "isotonic"],
            },
            "best_model": results["best_model_key"],
            "cv_results": results["cv_results"],
            "evaluation": results["eval_results"],
        }
        
        # Simplify for JSON
        simplified_eval = {}
        for key, metrics in results["eval_results"].items():
            simplified_eval[key] = {
                "roc_auc": metrics["roc_auc"],
                "average_precision": metrics["average_precision"],
                "brier_score": metrics["brier_score"],
                "optimal_threshold": metrics["optimal_threshold"],
                "f1_at_optimal": metrics["f1_at_optimal"],
                "ece": metrics["calibration"]["ece"],
            }
        
        model_results["evaluation"] = simplified_eval
        
        with open("training_results.json", "w") as f:
            json.dump(model_results, f, indent=2)
        print("✓ Saved: training_results.json")
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ════ STEP 4: Metrics Comparison Report ════
    print("\n" + "─" * 80)
    print("STEP 4: Metrics Comparison Report")
    print("─" * 80)
    
    try:
        from ml.metrics_comparison_report import generate_comprehensive_report, export_report
        
        print("\nGenerating comparison report...")
        
        report = generate_comprehensive_report(
            before_path="data_analysis_baseline.json",
            after_path="data_analysis_enhanced.json" if not use_synthetic else "training_results.json"
        )
        
        export_report(report, "ML_IMPROVEMENT_REPORT.txt")
        print("\n✓ Report generated and saved: ML_IMPROVEMENT_REPORT.txt")
        
        # Print key metrics
        if "evaluation" in model_results:
            print("\n📊 KEY METRICS (AFTER):")
            for model_name, metrics in simplified_eval.items():
                if "calibrated" in model_name:
                    print(f"\n  {model_name}:")
                    print(f"    ROC-AUC: {metrics['roc_auc']:.4f}")
                    print(f"    Brier Score: {metrics['brier_score']:.4f}")
                    print(f"    ECE: {metrics['ece']:.4f}")
                    print(f"    F1: {metrics['f1_at_optimal']:.4f}")
        
    except Exception as e:
        print(f"\n[WARN] Report generation failed: {e}")
    
    # ════ STEP 5: Optional Supabase Integration ════
    print("\n" + "─" * 80)
    print("STEP 5: Supabase Integration")
    print("─" * 80)
    
    if save_to_supabase:
        print("\nAttempting to save synthetic data to Supabase...")
        try:
            from ml.synthetic_supabase_integration import (
                save_original_data_to_supabase,
                save_synthetic_data_to_supabase,
            )
            
            print("[WARN] Supabase integration requires valid SUPABASE_URL/KEY")
            print("       Run manually if needed:")
            print("       python ml/synthetic_supabase_integration.py")
            
        except Exception as e:
            print(f"[INFO] Supabase integration skipped: {e}")
    else:
        print("Skipping Supabase integration (save_to_supabase=False)")
        print("To save synthetic data:run manually:")
        print("  python ml/synthetic_supabase_integration.py")
    
    # ════ FINAL SUMMARY ════
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETED ✓")
    print("=" * 80)
    print(f"End time: {datetime.now().isoformat()}")
    print("""
Generated files:
  • data_analysis_baseline.json    — Current dataset analysis
  • training_results.json           — Model training results
  • synthetic_samples_generated.csv — Generated synthetic samples
  • ML_IMPROVEMENT_REPORT.txt       — Detailed comparison report
  • enhanced_model.pkl              — New trained model (in backend/)

Next steps:
  1. Review ML_IMPROVEMENT_REPORT.txt for full analysis
  2. Check training_results.json for new metrics
  3. Run tests: python tests/test_model_scoring.py
  4. Deploy: Update core/state.py to use new model
  5. Monitor: Check production metrics and calibration
    """)
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Run ML improvement pipeline")
    parser.add_argument("--no-synthetic", action="store_true", 
                       help="Skip synthetic data generation")
    parser.add_argument("--synthetic-ratio", type=float, default=0.3,
                       help="Ratio of synthetic to original data (default: 0.3)")
    parser.add_argument("--save-supabase", action="store_true",
                       help="Save synthetic data to Supabase")
    parser.add_argument("--quiet", action="store_true",
                       help="Minimize output")
    
    args = parser.parse_args()
    
    success = run_pipeline(
        use_synthetic=not args.no_synthetic,
        synthetic_ratio=args.synthetic_ratio,
        save_to_supabase=args.save_supabase,
        verbose=not args.quiet,
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
