import pandas as pd
from pathlib import Path
from datetime import datetime

today = datetime.today().strftime("%Y-%m-%d")
cache_dir = Path(__file__).resolve().parents[1] / "data" / "cache"
count = 0
for f in cache_dir.glob("*.parquet"):
    df = pd.read_parquet(f)
    old = len(df)
    df = df[df["date"].astype(str).str[:10] != today]
    if len(df) < old:
        df.to_parquet(f, index=False)
        count += 1
print(f"cleared {count} files")
