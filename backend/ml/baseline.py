import pandas as pd
from ml.scoring import score_dataframe
import core.state as state


def compute_shortlist(df, top_n: int = 20):
    scored = score_dataframe(df)
    if len(scored) == 0:
        return None

    producer_scores = scored.groupby("producer_id").agg(
        ml_score=("ml_score", "mean"),
        total_applications=("ml_score", "count"),
        avg_amount=("Причитающая сумма", "mean"),
        region=("Область", "first"),
        direction=("Направление водства", "first"),
    ).reset_index()

    first_sub = scored.groupby("producer_id")["date"].min().reset_index()
    first_sub = first_sub.sort_values("date").reset_index(drop=True)
    first_sub["fcfs_rank"] = first_sub.index / max(len(first_sub) - 1, 1)

    producer_scores = producer_scores.merge(
        first_sub[["producer_id", "fcfs_rank"]], on="producer_id", how="left"
    )

    producer_scores["delta"] = (
        producer_scores["ml_score"] - (1 - producer_scores["fcfs_rank"])
    ).round(4)

    score_med = producer_scores["ml_score"].median()
    apps_med  = producer_scores["total_applications"].median()
    producer_scores["hidden_talent"] = (
        (producer_scores["ml_score"] > score_med) &
        (producer_scores["total_applications"] < apps_med)
    )

    top = producer_scores.nlargest(top_n, "ml_score")

    return {
        "total_producers": int(len(producer_scores)),
        "optimal_threshold": state.MODEL_DATA.get("optimal_threshold", 0.5) if state.MODEL_DATA else 0.5,
        "shortlist": top[[
            "producer_id", "ml_score", "total_applications",
            "avg_amount", "region", "direction",
            "delta", "hidden_talent", "fcfs_rank",
        ]].round(4).to_dict(orient="records"),
    }
