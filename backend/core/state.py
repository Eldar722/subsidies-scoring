import pandas as pd
import numpy as np
import joblib
import os
from core.config import MODEL_PATH, DATA_PATH

MODEL_DATA = None
DF = None

POSITIVE_STATUS = ["Исполнена"]
NEGATIVE_STATUS = ["Отклонена", "Отозвано"]
RESOLVED_STATUS = POSITIVE_STATUS + NEGATIVE_STATUS


def load_model():
    global MODEL_DATA
    if os.path.exists(MODEL_PATH):
        MODEL_DATA = joblib.load(MODEL_PATH)
        print(f"[OK] Model loaded | AUC={MODEL_DATA['metrics']['roc_auc']:.4f}")
    else:
        print(f"[WARN] {MODEL_PATH} not found - run train.py")


def load_data():
    global DF
    if not os.path.exists(DATA_PATH):
        print(f"[WARN] {DATA_PATH} not found")
        return

    DF = pd.read_excel(DATA_PATH, skiprows=4)

    DF["date"] = pd.to_datetime(DF["Дата поступления"], dayfirst=True, errors="coerce")
    DF["year"]        = DF["date"].dt.year
    DF["month"]       = DF["date"].dt.month
    DF["hour"]        = DF["date"].dt.hour
    DF["day_of_year"] = DF["date"].dt.dayofyear
    DF["day_of_week"] = DF["date"].dt.dayofweek

    DF["producer_id"] = DF["Номер заявки"].astype(str).str[:11]

    DF["Причитающая сумма"] = pd.to_numeric(DF["Причитающая сумма"], errors="coerce")
    DF["Норматив"]          = pd.to_numeric(DF["Норматив"], errors="coerce")
    DF["amount_to_norm"]    = (DF["Причитающая сумма"] / DF["Норматив"].replace(0, np.nan))
    DF["log_amount"]        = np.log1p(DF["Причитающая сумма"].fillna(0))
    DF["log_norm"]          = np.log1p(DF["Норматив"].fillna(0))

    DF["target"] = np.nan
    DF.loc[DF["Статус заявки"].isin(POSITIVE_STATUS), "target"] = 1
    DF.loc[DF["Статус заявки"].isin(NEGATIVE_STATUS), "target"] = 0

    print(f"[OK] Data loaded: {len(DF)} rows")
