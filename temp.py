import pandas as pd

jobs = pd.read_csv("results/jobs_scored.csv")
borderline = jobs[jobs["score"] >= 4].sort_values("score", ascending=False)
print(borderline[["score", "title", "company", "reason", "job_url"]].to_string())