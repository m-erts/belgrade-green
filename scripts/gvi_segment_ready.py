"""Write the list of downloaded thumbnails that are not segmented yet (for running segmentation
in rounds while downloads continue)."""
import pandas as pd

from bgreen.config import INTERIM

if __name__ == "__main__":
    m = pd.read_parquet(INTERIM / "gvi_meta.parquet")
    m = m[m["path"].notna() & (m["camera_type"] == "perspective")]
    done = set()
    for f in INTERIM.glob("gvi_seg*.parquet"):
        done |= set(pd.read_parquet(f)["path"])
    todo = [p for p in m["path"].astype(str) if p not in done]
    (INTERIM / "gvi_paths_round.txt").write_text("\n".join(todo))
    print(len(todo), "to segment;", len(done), "already done")
