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

    # FCFS: ранг по дате первой подачи (1 = самый ранний = лучший в FCFS)
    first_sub = scored.groupby("producer_id")["date"].min().reset_index()
    first_sub = first_sub.sort_values("date").reset_index(drop=True)
    first_sub["fcfs_rank_pos"] = range(1, len(first_sub) + 1)

    producer_scores = producer_scores.merge(
        first_sub[["producer_id", "fcfs_rank_pos"]], on="producer_id", how="left"
    )

    # ML ранг: 1 = лучший по ml_score
    producer_scores = producer_scores.sort_values("ml_score", ascending=False).reset_index(drop=True)
    producer_scores["ml_rank"] = range(1, len(producer_scores) + 1)

    # delta = fcfs_rank - ml_rank: положительное → ML оценивает выше FCFS (недооценён FCFS)
    producer_scores["delta"] = (
        producer_scores["fcfs_rank_pos"] - producer_scores["ml_rank"]
    ).astype(int)

    # hidden_talent: delta > 10 И ml_score > 0.7 (как в ТЗ)
    threshold = state.MODEL_DATA.get("optimal_threshold", 0.5) if state.MODEL_DATA else 0.5
    ml_high_threshold = max(threshold, 0.7)
    producer_scores["hidden_talent"] = (
        (producer_scores["delta"] > 10) &
        (producer_scores["ml_score"] > ml_high_threshold)
    )

    hidden_talent_total = int(producer_scores["hidden_talent"].sum())
    top = producer_scores.nlargest(top_n, "ml_score")

    return {
        "total_producers": int(len(producer_scores)),
        "hidden_talent_count": hidden_talent_total,
        "optimal_threshold": threshold,
        "shortlist": top[[
            "producer_id", "ml_score", "total_applications",
            "avg_amount", "region", "direction",
            "delta", "hidden_talent", "ml_rank", "fcfs_rank_pos",
        ]].rename(columns={"fcfs_rank_pos": "fcfs_rank"}).round(4).to_dict(orient="records"),
    }
