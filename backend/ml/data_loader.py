"""
data_loader.py — загрузка реального датасета субсидий subsidy.plem.kz
Источник: backend/data/subsidies.xlsx (header на строке 5)
"""

import pandas as pd
import numpy as np


def load_xlsx(path: str = "data/subsidies.xlsx") -> pd.DataFrame:
    """Загрузить xlsx датасет субсидий и подготовить базовые колонки.

    Returns:
        DataFrame с колонками: все оригинальные + date, producer_id,
        year, month, hour, day_of_week, day_of_year,
        числовые Причитающая сумма и Норматив.
    """
    df = pd.read_excel(path, header=4)

    # Парсинг даты (формат: дд.мм.гггг чч:мм:сс)
    df["date"] = pd.to_datetime(
        df["Дата поступления"], dayfirst=True, errors="coerce"
    )

    # producer_id = первые 11 цифр номера заявки
    df["producer_id"] = df["Номер заявки"].astype(str).str[:11]

    # Числовые колонки
    df["Причитающая сумма"] = pd.to_numeric(
        df["Причитающая сумма"], errors="coerce"
    )
    df["Норматив"] = pd.to_numeric(df["Норматив"], errors="coerce")

    # Временные признаки
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["hour"] = df["date"].dt.hour
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_year"] = df["date"].dt.dayofyear

    # Проверки целостности
    assert len(df) >= 36000, f"Ожидалось >= 36000 строк, получено {len(df)}"
    assert (
        df["producer_id"].nunique() >= 15000
    ), f"Ожидалось >= 15000 producer_id, получено {df['producer_id'].nunique()}"

    return df


if __name__ == "__main__":
    df = load_xlsx()
    print(f"Shape: {df.shape}")
    print(f"Уникальных producer_id: {df['producer_id'].nunique()}")
    print(f"\nКолонки:\n{list(df.columns)}")
    print(f"\nПервые 3 строки:")
    print(df[["producer_id", "Область", "Направление водства", "Статус заявки", "date"]].head(3))
    print(f"\nСтатусы:\n{df['Статус заявки'].value_counts()}")
    print(f"\nГоды:\n{df['year'].value_counts().sort_index()}")
