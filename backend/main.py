"""
main.py — FastAPI бэкенд для скоринга субсидий (v2, синхронизирован с train.py v4)
Запуск: uvicorn main:app --reload
Docs:   http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime
from scipy import stats as scipy_stats

app = FastAPI(
    title="Subsidy Scoring API",
    version="2.0.0",
    description="ML-скоринг сельхозпроизводителей для справедливого распределения субсидий",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Глобальные переменные ──────────────────────────────────────────────────────
MODEL_DATA = None
DF = None

POSITIVE_STATUS = ["Исполнена"]
NEGATIVE_STATUS = ["Отклонена", "Отозвано"]
RESOLVED_STATUS = POSITIVE_STATUS + NEGATIVE_STATUS


# ── Загрузка модели и данных ───────────────────────────────────────────────────

def load_model():
    global MODEL_DATA
    if os.path.exists("model.pkl"):
        MODEL_DATA = joblib.load("model.pkl")
        print(f"✅ Модель загружена | AUC={MODEL_DATA['metrics']['roc_auc']:.4f}")
    else:
        print("⚠️  model.pkl не найден — запустите train.py")


def load_data():
    global DF
    path = "data/subsidies.xlsx"
    if not os.path.exists(path):
        print("⚠️  data/subsidies.xlsx не найден")
        return

    DF = pd.read_excel(path, skiprows=4)

    # Те же преобразования что в train.py v4
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

    print(f"✅ Данные загружены: {len(DF)} строк")


def _enrich_with_group_stats(df_to_enrich, train_df, group_col, prefix):
    """Добавить агрегаты из train по group_col."""
    stats = train_df.groupby(group_col).agg(
        success_rate=("target", "mean"),
        volume=("target", "count"),
        avg_amount=("Причитающая сумма", "mean"),
    ).reset_index()
    stats.columns = [group_col, f"{prefix}_sr", f"{prefix}_vol", f"{prefix}_avg_amt"]
    enriched = df_to_enrich.merge(stats, on=group_col, how="left")
    for c in [f"{prefix}_sr", f"{prefix}_vol", f"{prefix}_avg_amt"]:
        fill_val = train_df["target"].mean() if "_sr" in c else stats[c].median()
        enriched[c] = enriched[c].fillna(fill_val)
    return enriched


def safe_transform(encoder, series):
    known = set(encoder.classes_)
    return series.map(lambda x: encoder.transform([x])[0] if x in known else -1)


def score_dataframe(df_slice):
    """Скоринг произвольного DataFrame — возвращает df с колонкой ml_score."""
    if MODEL_DATA is None:
        raise HTTPException(503, "Модель не загружена")
    if DF is None:
        raise HTTPException(503, "Данные не загружены")

    model    = MODEL_DATA["model"]
    features = MODEL_DATA["features"]
    encoders = MODEL_DATA["encoders"]
    threshold = MODEL_DATA.get("optimal_threshold", 0.5)

    # Берём завершённые заявки из 2025 как train reference
    train_ref = DF[(DF["year"] == 2025) & DF["target"].notna()].copy()
    train_ref["target"] = train_ref["target"].astype(int)

    df = df_slice.copy()

    # Агрегаты
    df = _enrich_with_group_stats(df, train_ref, "Область", "reg")
    df = _enrich_with_group_stats(df, train_ref, "Направление водства", "dir")
    df = _enrich_with_group_stats(df, train_ref, "Наименование субсидирования", "sub")
    df = _enrich_with_group_stats(df, train_ref, "Район хозяйства", "dist")

    # Encode
    df["region_enc"]    = safe_transform(encoders["region"],    df["Область"].fillna("unk"))
    df["direction_enc"] = safe_transform(encoders["direction"], df["Направление водства"].fillna("unk"))
    df["subsidy_enc"]   = safe_transform(encoders["subsidy"],   df["Наименование субсидирования"].fillna("unk"))

    # Fill NaN
    for c in features:
        if c in df.columns:
            df[c] = df[c].fillna(0)

    valid = df.dropna(subset=features)
    if len(valid) == 0:
        return pd.DataFrame()

    valid = valid.copy()
    valid["ml_score"] = model.predict_proba(valid[features])[:, 1]
    valid["ml_decision"] = (valid["ml_score"] >= threshold).astype(int)

    return valid


@app.on_event("startup")
async def startup():
    load_model()
    load_data()


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    """Проверка состояния сервиса — Этап #1"""
    return {
        "status": "ok",
        "model": "loaded" if MODEL_DATA is not None else "not loaded",
        "data": "loaded" if DF is not None else "not loaded",
        "rows": int(len(DF)) if DF is not None else 0,
        "model_version": "v4",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/metrics")
def metrics():
    """Метрики обученной модели"""
    if MODEL_DATA is None:
        raise HTTPException(503, "Модель не загружена")

    m = MODEL_DATA["metrics"]
    return {
        "roc_auc": round(m.get("roc_auc", 0), 4),
        "avg_precision": round(m.get("avg_precision", 0), 4),
        "best_f1": round(m.get("best_f1", 0), 4),
        "optimal_threshold": round(m.get("best_threshold", 0.5), 4),
        "cv_auc_mean": round(m.get("cv_auc_mean", 0), 4),
        "cv_f1_mean": round(m.get("cv_f1_mean", 0), 4),
        "features": MODEL_DATA["features"],
        "n_features": len(MODEL_DATA["features"]),
    }


@app.get("/api/stats")
def stats():
    """Базовая статистика по датасету"""
    if DF is None:
        raise HTTPException(503, "Данные не загружены")
    return {
        "total_rows": int(len(DF)),
        "total_producers": int(DF["producer_id"].nunique()),
        "status_distribution": DF["Статус заявки"].value_counts().to_dict(),
        "year_distribution": {str(k): int(v) for k, v in DF["year"].value_counts().items()},
        "regions": DF["Область"].value_counts().to_dict(),
        "directions": DF["Направление водства"].value_counts().to_dict(),
        "avg_amount": round(float(DF["Причитающая сумма"].mean()), 2),
        "total_amount": round(float(DF["Причитающая сумма"].sum()), 2),
    }


@app.get("/api/shortlist")
def shortlist(top_n: int = 20):
    """
    Топ-N производителей по ML-скорингу.
    delta = ML-score минус нормализованный FCFS-ранк.
    hidden_talent = высокий score, но мало заявок.
    """
    if DF is None:
        raise HTTPException(503, "Данные не загружены")

    scored = score_dataframe(DF)
    if len(scored) == 0:
        raise HTTPException(500, "Нет данных для скоринга")

    # Агрегация до уровня производителя
    producer_scores = scored.groupby("producer_id").agg(
        ml_score=("ml_score", "mean"),
        total_applications=("ml_score", "count"),
        avg_amount=("Причитающая сумма", "mean"),
        region=("Область", "first"),
        direction=("Направление водства", "first"),
    ).reset_index()

    # FCFS baseline
    first_sub = scored.groupby("producer_id")["date"].min().reset_index()
    first_sub = first_sub.sort_values("date").reset_index(drop=True)
    first_sub["fcfs_rank"] = first_sub.index / max(len(first_sub) - 1, 1)

    producer_scores = producer_scores.merge(
        first_sub[["producer_id", "fcfs_rank"]], on="producer_id", how="left"
    )

    # delta: ML vs FCFS
    producer_scores["delta"] = (
        producer_scores["ml_score"] - (1 - producer_scores["fcfs_rank"])
    ).round(4)

    # hidden_talent
    score_med = producer_scores["ml_score"].median()
    apps_med  = producer_scores["total_applications"].median()
    producer_scores["hidden_talent"] = (
        (producer_scores["ml_score"] > score_med) &
        (producer_scores["total_applications"] < apps_med)
    )

    top = producer_scores.nlargest(top_n, "ml_score")

    return {
        "total_producers": int(len(producer_scores)),
        "optimal_threshold": MODEL_DATA.get("optimal_threshold", 0.5) if MODEL_DATA else 0.5,
        "shortlist": top[[
            "producer_id", "ml_score", "total_applications",
            "avg_amount", "region", "direction",
            "delta", "hidden_talent", "fcfs_rank",
        ]].round(4).to_dict(orient="records"),
    }


@app.get("/api/fairness")
def fairness():
    """
    Анализ справедливости распределения.
    - Gini-коэффициент распределения субсидий по регионам
    - Kruskal-Wallis тест: различаются ли суммы между регионами / направлениями
    - Распределение score по регионам (если модель загружена)
    """
    if DF is None:
        raise HTTPException(503, "Данные не загружены")

    resolved = DF[DF["target"].notna()].copy()

    # ── Gini по регионам ──
    region_amounts = resolved.groupby("Область")["Причитающая сумма"].sum().sort_values()
    amounts = region_amounts.values.astype(float)

    def gini(x):
        x = np.sort(x)
        n = len(x)
        if n == 0 or x.sum() == 0:
            return 0.0
        cumx = np.cumsum(x)
        return float((2 * np.sum((np.arange(1, n + 1) * x)) / (n * x.sum())) - (n + 1) / n)

    gini_value = gini(amounts)

    # Lorenz curve data
    sorted_amounts = np.sort(amounts)
    cumulative = np.cumsum(sorted_amounts) / sorted_amounts.sum()
    population = np.arange(1, len(sorted_amounts) + 1) / len(sorted_amounts)
    lorenz = [
        {"population": round(float(p), 4), "cumulative_share": round(float(c), 4)}
        for p, c in zip(population, cumulative)
    ]

    # ── Kruskal-Wallis: суммы по регионам ──
    region_groups = [
        g["Причитающая сумма"].dropna().values
        for _, g in resolved.groupby("Область")
        if len(g) > 5
    ]
    if len(region_groups) >= 2:
        kw_stat, kw_p = scipy_stats.kruskal(*region_groups)
    else:
        kw_stat, kw_p = 0, 1

    # ── Kruskal-Wallis: суммы по направлениям ──
    dir_groups = [
        g["Причитающая сумма"].dropna().values
        for _, g in resolved.groupby("Направление водства")
        if len(g) > 5
    ]
    if len(dir_groups) >= 2:
        kw_dir_stat, kw_dir_p = scipy_stats.kruskal(*dir_groups)
    else:
        kw_dir_stat, kw_dir_p = 0, 1

    # ── Распределение по регионам ──
    region_summary = resolved.groupby("Область").agg(
        total_apps=("target", "count"),
        success_rate=("target", "mean"),
        avg_amount=("Причитающая сумма", "mean"),
        total_amount=("Причитающая сумма", "sum"),
    ).reset_index().round(4)

    # ── Heatmap region × direction ──
    heatmap = resolved.groupby(["Область", "Направление водства"]).agg(
        success_rate=("target", "mean"),
        count=("target", "count"),
    ).reset_index()
    heatmap = heatmap[heatmap["count"] >= 5].round(4)

    return {
        "gini_coefficient": round(gini_value, 4),
        "gini_interpretation": (
            "Высокое неравенство" if gini_value > 0.4
            else "Умеренное неравенство" if gini_value > 0.25
            else "Низкое неравенство"
        ),
        "lorenz_curve": lorenz,
        "kruskal_wallis": {
            "by_region": {
                "statistic": round(float(kw_stat), 4),
                "p_value": round(float(kw_p), 6),
                "significant": bool(kw_p < 0.05),
                "interpretation": "Суммы значимо различаются между регионами" if kw_p < 0.05
                                  else "Значимых различий не обнаружено",
            },
            "by_direction": {
                "statistic": round(float(kw_dir_stat), 4),
                "p_value": round(float(kw_dir_p), 6),
                "significant": bool(kw_dir_p < 0.05),
                "interpretation": "Суммы значимо различаются между направлениями" if kw_dir_p < 0.05
                                  else "Значимых различий не обнаружено",
            },
        },
        "regions": region_summary.to_dict(orient="records"),
        "heatmap": heatmap.to_dict(orient="records"),
    }


@app.get("/api/producers/{producer_id}")
def producer_detail(producer_id: str):
    """Детальная информация по производителю"""
    if DF is None:
        raise HTTPException(503, "Данные не загружены")

    producer_rows = DF[DF["producer_id"] == producer_id]
    if len(producer_rows) == 0:
        raise HTTPException(404, f"Производитель {producer_id} не найден")

    # Скоринг
    scored = score_dataframe(producer_rows)

    applications = []
    for _, row in producer_rows.iterrows():
        app_data = {
            "date": row["date"].isoformat() if pd.notna(row["date"]) else None,
            "status": row["Статус заявки"],
            "region": row["Область"],
            "direction": row["Направление водства"],
            "subsidy": row["Наименование субсидирования"],
            "amount": round(float(row["Причитающая сумма"]), 2) if pd.notna(row["Причитающая сумма"]) else None,
            "norm": round(float(row["Норматив"]), 2) if pd.notna(row["Норматив"]) else None,
        }
        applications.append(app_data)

    result = {
        "producer_id": producer_id,
        "total_applications": len(producer_rows),
        "status_breakdown": producer_rows["Статус заявки"].value_counts().to_dict(),
        "total_amount": round(float(producer_rows["Причитающая сумма"].sum()), 2),
        "avg_amount": round(float(producer_rows["Причитающая сумма"].mean()), 2),
        "region": producer_rows["Область"].mode().iloc[0] if len(producer_rows) > 0 else None,
        "applications": applications,
    }

    if len(scored) > 0:
        result["ml_score"] = round(float(scored["ml_score"].mean()), 4)
    else:
        result["ml_score"] = None

    return result
