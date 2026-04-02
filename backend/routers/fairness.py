from fastapi import APIRouter, HTTPException
from cachetools import TTLCache
import core.state as state
from ml.fairness import compute_fairness_report

router = APIRouter()

# Кэш на 1 час (3600 секунд)
fairness_cache = TTLCache(maxsize=1, ttl=3600)


def _adapt_fairness_response(report: dict) -> dict:
    """
    Адаптировать ответ backend под контракт, ожидаемый frontend.
    Frontend ожидает ключи:
      gini_coefficient, gini_coefficient_amounts, lorenz_curve,
      kruskal_wallis.by_region, kruskal_wallis.by_direction,
      region_zscores (list), heatmap
    """
    # --- Z-scores: dict → list для frontend ---
    region_z_list = [
        {
            "region": region,
            "avg_score": data.get("mean_score", 0),
            "z_score": data.get("z_score", 0),
            "is_outlier": data.get("outlier", False),
        }
        for region, data in (report.get("region_z_scores") or {}).items()
    ]
    region_z_list.sort(key=lambda x: x["z_score"])

    # --- Kruskal-Wallis: адаптация ключей ---
    kw_reg = report.get("kruskal_regions", {})
    kw_dir = report.get("kruskal_directions", {})

    def _adapt_kw(kw: dict) -> dict:
        return {
            "statistic": kw.get("H", 0),
            "p_value": kw.get("p_value", 1.0),
            "significant": kw.get("p_value", 1.0) < 0.05,
            "interpretation": kw.get("interpretation", ""),
        }

    # --- Region summary stats ---
    regions_raw = report.get("regions", [])
    region_stats = []
    for r in regions_raw:
        region_stats.append({
            "region": r.get("Область", r.get("region", "")),
            "total_apps": int(r.get("total_apps", 0)),
            "success_rate": round(float(r.get("success_rate", 0)), 4),
            "avg_amount": round(float(r.get("avg_amount", 0)), 2),
            "total_amount": round(float(r.get("total_amount", 0)), 2),
        })

    return {
        # Gini
        "gini_coefficient": report.get("gini_scores", 0),
        "gini_coefficient_amounts": report.get("gini_amounts", 0),
        "gini_interpretation": report.get("gini_interpretation", ""),
        # Lorenz
        "lorenz_curve": report.get("lorenz_scores", []),
        "lorenz_amounts": report.get("lorenz_amounts", []),
        # Kruskal-Wallis
        "kruskal_wallis": {
            "by_region": _adapt_kw(kw_reg),
            "by_direction": _adapt_kw(kw_dir),
        },
        # Z-scores
        "region_zscores": region_z_list,
        # Heatmap
        "heatmap": report.get("heatmap", []),
        # Regional stats
        "regional_stats": region_stats,
    }


@router.get("/fairness")
def fairness():
    if state.DF is None:
        raise HTTPException(503, "Данные не загружены")

    cache_key = "fairness_report"
    if cache_key in fairness_cache:
        return fairness_cache[cache_key]

    report = compute_fairness_report(state.DF)
    adapted = _adapt_fairness_response(report)
    fairness_cache[cache_key] = adapted
    return adapted
