"""
hidden_talent_detector.py — единая логика для определения скрытых талантов.

Решает проблему: different hidden_talent в baseline.py vs baseline_service.py

Используется везде:
- baseline.py (shortlist computation)
- baseline_service.py (baseline service)
- simulator_service.py (simulator weight testing)
"""

import pandas as pd
import numpy as np
from core import state
from typing import Tuple


def get_optimal_threshold() -> float:
    """Получить оптимальный threshold из MODEL_DATA.
    
    Returns:
        float: optimal_threshold из модели, или 0.5 если не доступен
    """
    if state.MODEL_DATA and "metrics" in state.MODEL_DATA and "optimal_threshold" in state.MODEL_DATA["metrics"]:
        return state.MODEL_DATA["metrics"]["optimal_threshold"]
    return 0.5


def detect_hidden_talents_by_delta(producer_scores: pd.DataFrame,
                                  delta_threshold: int = 8,
                                  score_multiplier: float = 0.85) -> pd.Series:
    """Определить скрытые таланты по DELTA логике (baseline.py).
    
    Скрытый талант = (delta > delta_threshold) AND (ml_score > threshold)
    
    Args:
        producer_scores: DataFrame с полями [ml_score, delta]
        delta_threshold: минимальное значение delta для скрытого таланта (default 8, было 10)
        score_multiplier: умножитель для threshold (default 0.85, было 1.0 - это даeт ~0.62 вместо 0.73)
    
    Returns:
        Series[bool]: скрытые таланты
    """
    threshold = get_optimal_threshold()
    # Применить умножитель для учета distribution shift
    ml_high_threshold = threshold * score_multiplier
    # Гарантировать минимум 0.55 (не ниже)
    ml_high_threshold = max(ml_high_threshold, 0.55)
    
    return (producer_scores["delta"] > delta_threshold) & (producer_scores["ml_score"] > ml_high_threshold)


def detect_hidden_talents_by_median(scores: pd.Series, 
                                    apps_count: pd.Series) -> pd.Series:
    """Определить скрытые таланты по MEDIAN логике (simulator).
    
    Скрытый талант = (score > median) AND (apps < median)
    Используется в изменяемых сценариях (simulator_service).
    
    Args:
        scores: ml_score Series
        apps_count: total_apps Series
    
    Returns:
        Series[bool]: скрытые таланты
    """
    score_med = scores.median()
    apps_med = apps_count.median()
    
    return (scores > score_med) & (apps_count < apps_med)


def enrich_hidden_talents(producer_df: pd.DataFrame,
                         method: str = "delta") -> pd.DataFrame:
    """Добавить колонку hidden_talent в DataFrame производителей.
    
    Args:
        producer_df: DataFrame с производителями
        method: 'delta' (baseline.py style) или 'median' (simulator style)
    
    Returns:
        DataFrame с добавленной колонкой hidden_talent
    """
    df = producer_df.copy()
    
    if method == "delta":
        if "delta" not in df.columns:
            raise ValueError("DataFrame must contain 'delta' column for delta method")
        df["hidden_talent"] = detect_hidden_talents_by_delta(df)
    elif method == "median":
        if "ml_score" not in df.columns or "total_apps" not in df.columns:
            raise ValueError("DataFrame must contain 'ml_score' and 'total_apps' for median method")
        df["hidden_talent"] = detect_hidden_talents_by_median(df["ml_score"], df["total_apps"])
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return df


def get_hidden_talent_info(producer_df: pd.DataFrame,
                          method: str = "delta") -> dict:
    """Получить информацию о скрытых талантах.
    
    Returns:
        dict: count, percentage, threshold usado
    """
    df = enrich_hidden_talents(producer_df, method=method)
    
    total = len(df)
    count = int(df["hidden_talent"].sum())
    percentage = 100 * count / total if total > 0 else 0
    
    info = {
        "count": count,
        "total": total,
        "percentage": percentage,
        "method": method,
        "threshold": get_optimal_threshold() if method == "delta" else None,
    }
    
    return info, df


if __name__ == "__main__":
    # Test
    import sys
    sys.path.insert(0, "/backend")
    
    print("Hidden Talent Detector - Test")
    
    # Mock model data
    class MockState:
        MODEL_DATA = {
            "metrics": {
                "optimal_threshold": 0.65,
            }
        }
    
    state.MODEL_DATA = MockState.MODEL_DATA
    
    # Test data
    test_data = pd.DataFrame({
        "producer_id": ["P1", "P2", "P3", "P4"],
        "ml_score": [0.9, 0.8, 0.6, 0.3],
        "delta": [15, 5, 20, -5],
        "total_apps": [3, 5, 2, 8],
    })
    
    # Test delta method
    result_delta = enrich_hidden_talents(test_data, method="delta")
    print("\nDelta method:")
    print(result_delta[["producer_id", "ml_score", "delta", "hidden_talent"]])
    
    # Test median method
    result_median = enrich_hidden_talents(test_data, method="median")
    print("\nMedian method:")
    print(result_median[["producer_id", "ml_score", "total_apps", "hidden_talent"]])
