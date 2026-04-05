#!/usr/bin/env python3
"""
Диагностика датасета перед обучением: годы, таргет, пропуски, сдвиг доли положительного класса.
Запуск из backend/:  python scripts/diagnose_training_data.py [path/to/subsidies.xlsx]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

POS = ["Исполнена"]
NEG = ["Отклонена", "Отозвано"]


def main() -> int:
    backend = Path(__file__).resolve().parent.parent
    data_path = Path(sys.argv[1]) if len(sys.argv) > 1 else backend / "data" / "subsidies.xlsx"
    if not data_path.is_file():
        print(f"Нет файла: {data_path}")
        return 1

    df = pd.read_excel(data_path, skiprows=4)
    print(f"Строк всего: {len(df)}")

    df["date"] = pd.to_datetime(df["Дата поступления"], dayfirst=True, errors="coerce")
    df["year"] = df["date"].dt.year
    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(POS), "target"] = 1
    df.loc[df["Статус заявки"].isin(NEG), "target"] = 0
    resolved = df.dropna(subset=["target"]).copy()
    resolved["target"] = resolved["target"].astype(int)

    print("\n=== По годам (завершённые заявки) ===")
    for y in sorted(resolved["year"].dropna().unique()):
        sub = resolved[resolved["year"] == y]
        print(f"  {int(y)}: n={len(sub):6d}  pos_rate={sub['target'].mean():.4f}")

    if len(resolved[resolved["year"] == 2025]) and len(resolved[resolved["year"] == 2026]):
        r25 = resolved[resolved["year"] == 2025]["target"].mean()
        r26 = resolved[resolved["year"] == 2026]["target"].mean()
        print(f"\nСдвиг pos_rate 2026 vs 2025: {r26 - r25:+.4f} (дрифт класса → падение AUC на hold-out)")

    key_cols = ["Причитающая сумма", "Норматив", "Область", "Направление водства"]
    print("\n=== Доля пропусков в ключевых колонках ===")
    for c in key_cols:
        if c in df.columns:
            miss = df[c].isna().mean()
            print(f"  {c}: {miss:.2%}")

    print("\n=== Статусы (сырые, top 10) ===")
    print(df["Статус заявки"].value_counts().head(10).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
