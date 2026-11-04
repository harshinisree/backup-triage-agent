"""Detect abnormal days in backup job history using IsolationForest."""
import pandas as pd
from sklearn.ensemble import IsolationForest


def daily_stats(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("date").agg(total=("status", "size"),
                               failed=("status", lambda s: (s == "FAILED").sum()))
    g["fail_rate"] = g["failed"] / g["total"]
    return g.reset_index()


def detect(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    stats = daily_stats(df)
    model = IsolationForest(contamination=contamination, random_state=42)
    stats["anomaly"] = model.fit_predict(stats[["failed", "fail_rate"]]) == -1
    return stats[stats["anomaly"]].reset_index(drop=True)
