"""
synthetic_supabase_integration.py — загрузка синтетических данных в Supabase.

Интегрирует синтетические данные с таблицей training_samples в Supabase.
Все данные хранятся в одной таблице с флагом is_synthetic.
"""

import pandas as pd
import numpy as np
import math
from supabase import create_client
from core.config import SUPABASE_URL, SUPABASE_KEY
from typing import List, Dict, Optional

BATCH_SIZE = 500


def _get_client():
    """Получить клиент Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _clean_row(row: dict) -> dict:
    """Заменить NaN/inf/None на None для JSON-сериализации."""
    cleaned = {}
    for k, v in row.items():
        if v is None:
            cleaned[k] = None
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        elif isinstance(v, (pd.Timestamp, np.datetime64)):
            cleaned[k] = pd.Timestamp(v).isoformat()
        else:
            cleaned[k] = v
    return cleaned


def _upsert_batch(table: str, records: list, batch_size: int = BATCH_SIZE) -> int:
    """Upsert записей батчами."""
    if not records:
        return 0
    
    client = _get_client()
    total = 0
    
    for i in range(0, len(records), batch_size):
        batch = [_clean_row(r) for r in records[i:i + batch_size]]
        try:
            client.table(table).upsert(batch).execute()
            total += len(batch)
            if total % 1000 == 0 or total == len(records):
                print(f"  {table}: {total}/{len(records)} записей")
        except Exception as e:
            print(f"[ERROR] Upsert batch failed: {e}")
            raise
    
    return total


def save_original_data_to_supabase(df_original: pd.DataFrame,
                                   numeric_features: List[str],
                                   verbose: bool = True) -> int:
    """Сохранить оригинальные обучающие данные в Supabase.
    
    Args:
        df_original: DataFrame с оригинальными данными
        numeric_features: список числовых признаков
        verbose: выводить прогресс
    
    Returns:
        кол-во сохраненных записей
    """
    df = df_original.copy()
    
    records = []
    for idx, row in df.iterrows():
        record = {
            # Основные данные
            "номер_заявки": row.get("Номер заявки"),
            "producer_id": row.get("producer_id"),
            "область": row.get("Область"),
            "направление_водства": row.get("Направление водства"),
            "наименование_субсидирования": row.get("Наименование субсидирования"),
            "район_хозяйства": row.get("Район хозяйства"),
            "причитавшаяся_сумма": float(row.get("Причитающая сумма")) if pd.notna(row.get("Причитающая сумма")) else None,
            "норматив": float(row.get("Норматив")) if pd.notna(row.get("Норматив")) else None,
            "дата_поступления": pd.Timestamp(row.get("date")).isoformat() if pd.notna(row.get("date")) else None,
            
            # Target
            "target": int(row.get("target")) if pd.notna(row.get("target")) else None,
            
            # Метаданные синтезmа
            "is_synthetic": False,
            "synthetic_method": None,
            "original_index": None,
            
            # Временные признаки
            "year": int(row.get("year")) if pd.notna(row.get("year")) else None,
            "month": int(row.get("month")) if pd.notna(row.get("month")) else None,
            "hour": int(row.get("hour")) if pd.notna(row.get("hour")) else None,
            "day_of_week": int(row.get("day_of_week")) if pd.notna(row.get("day_of_week")) else None,
            "day_of_year": int(row.get("day_of_year")) if pd.notna(row.get("day_of_year")) else None,
            
            # Производные финансовые
            "amount_to_norm": float(row.get("amount_to_norm")) if pd.notna(row.get("amount_to_norm")) else None,
            "log_amount": float(row.get("log_amount")) if pd.notna(row.get("log_amount")) else None,
            "log_norm": float(row.get("log_norm")) if pd.notna(row.get("log_norm")) else None,
        }
        
        records.append(record)
    
    if verbose:
        print(f"\n💾 Сохранение оригинальных данных в Supabase ({len(records)} записей)...")
    
    return _upsert_batch("training_samples", records)


def save_synthetic_data_to_supabase(df_synthetic: pd.DataFrame,
                                    synthetic_method: str,
                                    numeric_features: List[str],
                                    verbose: bool = True) -> int:
    """Сохранить синтетические данные в Supabase.
    
    Args:
        df_synthetic: DataFrame с синтетическими данными
        synthetic_method: 'borderline_smote', 'gaussian' или 'bootstrap'
        numeric_features: список числовых признаков
        verbose: выводить прогресс
    
    Returns:
        кол-во сохраненных записей
    """
    df = df_synthetic.copy()
    
    records = []
    for idx, row in df.iterrows():
        record = {
            # Основные данные
            "номер_заявки": None,  # Нет номера заявки для синтетики
            "producer_id": None,
            "область": row.get("Область"),
            "направление_водства": row.get("Направление водства"),
            "наименование_субсидирования": row.get("Наименование субсидирования"),
            "район_хозяйства": row.get("Район хозяйства"),
            "причитавшаяся_сумма": float(row.get("Причитающая сумма")) if pd.notna(row.get("Причитающая сумма")) else None,
            "норматив": float(row.get("Норматив")) if pd.notna(row.get("Норматив")) else None,
            "дата_поступления": None,  # Нет реальной даты для синтетики
            
            # Target
            "target": int(row.get("target")) if pd.notna(row.get("target")) else None,
            
            # Метаданные синтеза
            "is_synthetic": True,
            "synthetic_method": synthetic_method,
            "original_index": None,  # Можно добавить индекс оригинала, если нужно
            
            # Временные признаки (если есть)
            "year": int(row.get("year")) if pd.notna(row.get("year")) else None,
            "month": int(row.get("month")) if pd.notna(row.get("month")) else None,
            "hour": int(row.get("hour")) if pd.notna(row.get("hour")) else None,
            "day_of_week": int(row.get("day_of_week")) if pd.notna(row.get("day_of_week")) else None,
            "day_of_year": int(row.get("day_of_year")) if pd.notna(row.get("day_of_year")) else None,
            
            # Производные финансовые
            "amount_to_norm": float(row.get("amount_to_norm")) if pd.notna(row.get("amount_to_norm")) else None,
            "log_amount": float(row.get("log_amount")) if pd.notna(row.get("log_amount")) else None,
            "log_norm": float(row.get("log_norm")) if pd.notna(row.get("log_norm")) else None,
        }
        
        records.append(record)
    
    if verbose:
        print(f"💾 Сохранение {synthetic_method} синтетики в Supabase ({len(records)} записей)...")
    
    return _upsert_batch("training_samples", records)


def get_training_samples_from_supabase(is_synthetic: Optional[bool] = None,
                                       synthetic_method: Optional[str] = None) -> pd.DataFrame:
    """Загрузить training samples из Supabase.
    
    Args:
        is_synthetic: True/False/None (все)
        synthetic_method: фильтр по методу
    
    Returns:
        DataFrame с samples
    """
    client = _get_client()
    query = client.table("training_samples").select("*")
    
    if is_synthetic is not None:
        query = query.eq("is_synthetic", is_synthetic)
    
    if synthetic_method is not None:
        query = query.eq("synthetic_method", synthetic_method)
    
    result = query.execute()
    
    if result.data:
        return pd.DataFrame(result.data)
    else:
        return pd.DataFrame()


def get_supabase_stats() -> Dict:
    """Получить статистику по training_samples в Supabase."""
    client = _get_client()
    
    # Всего
    total = client.table("training_samples").select("*", count="exact").limit(0).execute()
    total_count = total.count if hasattr(total, "count") else 0
    
    # Оригинальных
    original = client.table("training_samples").select("*", count="exact").eq("is_synthetic", False).limit(0).execute()
    original_count = original.count if hasattr(original, "count") else 0
    
    # Синтетических
    synthetic = client.table("training_samples").select("*", count="exact").eq("is_synthetic", True).limit(0).execute()
    synthetic_count = synthetic.count if hasattr(synthetic, "count") else 0
    
    return {
        "total": total_count,
        "original": original_count,
        "synthetic": synthetic_count,
        "synthetic_ratio": synthetic_count / total_count if total_count > 0 else 0,
    }


if __name__ == "__main__":
    from ml.data_loader import load_xlsx
    from ml.synthetic_data_generator import generate_synthetic_training_data
    
    print("=" * 70)
    print("Testing Supabase Integration")
    print("=" * 70)
    
    # Загрузить данные
    print("\n[*] Загрузка данных...")
    df = load_xlsx()
    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(["Исполнена"]), "target"] = 1
    df.loc[df["Статус заявки"].isin(["Отклонена", "Отозвано"]), "target"] = 0
    
    train_df = df[df["year"] == 2025].dropna(subset=["target"]).copy()
    train_df["target"] = train_df["target"].astype(int)
    
    print(f"✓ Загружено {len(train_df)} оригинальных samples")
    
    # Генерировать синтетику
    numeric_features = [
        "month", "hour", "day_of_year", "day_of_week",
        "Норматив", "Причитающая сумма"
    ]
    cat_features = ["Область", "Направление водства", "Наименование субсидирования"]
    
    print("\n[*] Генерация синтетических данных...")
    df_synthetic = generate_synthetic_training_data(
        train_df, numeric_features, cat_features, verbose=True
    )
    
    # TRY: сохранить в Supabase (раскомменту если нужно)
    # print("\n[*] Сохранение в Supabase...")
    # try:
    #     n_original = save_original_data_to_supabase(train_df, numeric_features)
    #     print(f"✓ Сохранено {n_original} оригинальных samples")
    # except Exception as e:
    #     print(f"[WARN] Не удалось сохранить оригинальные данные: {e}")
    # 
    # for method in ["borderline_smote", "gaussian", "bootstrap"]:
    #     df_method = df_synthetic[df_synthetic.get("synthetic_method") == method]
    #     if len(df_method) > 0:
    #         try:
    #             n = save_synthetic_data_to_supabase(df_method, method, numeric_features)
    #             print(f"✓ Сохранено {n} {method} samples")
    #         except Exception as e:
    #             print(f"[WARN] Не удалось сохранить {method}: {e}")
    #
    # Статистика
    print("\n[✓] Testingqueries complete")
