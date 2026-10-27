"""Pick summer Global Streetscapes images in Belgrade that came from Mapillary, fetch the same images
and list them for segmentation, so our GVI can be compared with the published one."""
import pandas as pd

from bgreen.config import INTERIM, RAW
from bgreen.data import mapillary as mly

N = 300

if __name__ == "__main__":
    gs = pd.read_parquet(RAW / "streetscapes_belgrade.parquet")
    gs = gs[(gs.source == "Mapillary") & gs.month.between(5, 9) & (gs.lighting_condition == "day")
            & (gs.projection_type == "perspective") & (gs.quality == "good")]
    gs = gs.sample(n=min(N, len(gs)), random_state=7)
    meta = mly.entities(gs.orig_id.astype("int64").tolist())
    meta["path"] = mly.download(meta)
    meta["id"] = meta["id"].astype(str)
    gs["id"] = gs.orig_id.astype("int64").astype(str)
    out = gs[["id", "green_view_index"]].merge(meta[["id", "path"]], on="id")
    out = out[out.path.notna()]
    out.to_parquet(INTERIM / "gvi_validation_list.parquet")
    (INTERIM / "gvi_validation_paths.txt").write_text("\n".join(out.path))
    print(len(out), "validation images ready")
