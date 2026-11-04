"""Generate SYNTHETIC backup job history (no real data). Includes one injected failure spike."""
import random

import pandas as pd

random.seed(7)
rows = []
for day in pd.date_range("2026-09-01", periods=45):
    for host in [f"srv-{i:02d}" for i in range(1, 9)]:
        rate = 0.5 if str(day.date()) == "2026-09-30" else 0.03
        rows.append({"date": str(day.date()), "host": host,
                     "status": "FAILED" if random.random() < rate else "SUCCEEDED"})
pd.DataFrame(rows).to_csv("data/sample_jobs.csv", index=False)
print("wrote data/sample_jobs.csv")
