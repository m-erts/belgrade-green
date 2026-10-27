"""Export the data the project page needs into docs/data (small GeoJSON/JSON, WGS84)."""
import json

import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio.features import shapes
from shapely.geometry import shape

from bgreen.config import INTERIM, RAW, ROOT, TABLES
from bgreen.grid import URBAN, window_of, CITY
from bgreen.measures import units

OUT = ROOT / "docs" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def _write(gdf, name, precision=5):
    gdf = gdf.to_crs(4326)
    js = json.loads(gdf.to_json(drop_id=True))
    def rnd(c):
        return [rnd(x) for x in c] if isinstance(c, list) else round(c, precision)
    for f in js["features"]:
        f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
    (OUT / name).write_text(json.dumps(js, separators=(",", ":"), ensure_ascii=False))
    print(name, round((OUT / name).stat().st_size / 1e6, 2), "MB", len(gdf))


def patches():
    d = INTERIM / "conn_city"
    lab = np.load(d / "labels.npy")
    areas = np.load(d / "areas.npy")
    names = pd.read_parquet(d / "patch_names.parquet").set_index("patch")
    bo = pd.read_parquet(d / "buildover.parquet").set_index("patch")
    bt_raw = pd.read_parquet(INTERIM / "conn_city_touching" / "buildover.parquet")
    lab_t = np.load(INTERIM / "conn_city_touching" / "labels.npy")
    areas_t = np.load(INTERIM / "conn_city_touching" / "areas.npy")
    geoms = {}
    for g, v in shapes(lab.astype("int32"), mask=lab > 0, transform=URBAN.transform):
        geoms.setdefault(int(v), []).append(shape(g))
    rows = []
    for p, gs in geoms.items():
        from shapely.ops import unary_union
        geom = unary_union(gs).simplify(8, preserve_topology=True)
        r = {"id": p, "ha": round(float(areas[p - 1]), 1),
             "name": names.loc[p, "green_name"] if p in names.index and isinstance(names.loc[p, "green_name"], str) else None,
             "place": names.loc[p, "near_place"] if p in names.index else None}
        if p in bo.index:
            r["ec_loss"] = round(float(bo.loc[p, "EC_loss_1000"]))
            r["lev"] = round(float(bo.loc[p, "leverage_1000"]), 2)
            ids, cnt = np.unique(lab_t[lab == p], return_counts=True)
            ids, cnt = ids[ids > 0], cnt[ids > 0]
            if len(ids):
                k = ids[np.argmax(cnt)]
                m = bt_raw[bt_raw.patch == k]
                if len(m):
                    r["ec_loss_t"] = round(float(m.EC_loss_1000.iloc[0]))
                    r["lev_t"] = round(float(m.leverage_1000.iloc[0]), 2)
                    r["ha_t"] = round(float(areas_t[k - 1]), 1)  # the unclipped patch can be much larger
        r["bridge"] = bool(r.get("lev", 0) >= 1.15 and r.get("lev_t", 0) >= 1.15 and r["ha"] < 1000)
        rows.append({**r, "geometry": geom})
    _write(gpd.GeoDataFrame(rows, crs=URBAN.crs), "patches.geojson")


def context():
    u = units.load(URBAN.crs)
    _write(u[["unit", "pop_2022", "geometry"]].assign(geometry=u.geometry.simplify(15)), "units.geojson")
    r0, c0 = window_of(URBAN, CITY)
    import rasterio
    with rasterio.open(RAW / "worldcover_2021.tif") as s:
        lc = s.read(1)[r0:r0 + URBAN.height, c0:c0 + URBAN.width]
    w = (lc == 80).astype("uint8")
    polys = [shape(g).simplify(15) for g, v in shapes(w, mask=w == 1, transform=URBAN.transform)]
    water = gpd.GeoDataFrame(geometry=[p for p in polys if p.area > 20000], crs=URBAN.crs)
    bb = u.total_bounds
    from shapely.geometry import box
    frame = box(bb[0] - 3000, bb[1] - 3000, bb[2] + 3000, bb[3] + 3000)
    water = water[water.intersects(frame)]
    water["geometry"] = water.geometry.intersection(frame)
    _write(water, "water.geojson", 5)
    b = gpd.read_file(RAW / "osm_barriers.gpkg").to_crs(URBAN.crs)
    roads = b[b.highway.isin(["motorway", "trunk", "primary"])].copy()
    roads = roads[roads.intersects(frame)]
    roads["geometry"] = roads.geometry.intersection(frame).simplify(10)
    _write(roads[["highway", "geometry"]], "roads.geojson", 5)


def points():
    """Two markers: the costliest graph link (placed on the road cell its least-cost path crosses) and the
    narrowest circuit-theory gap (placed on its peak-current cell)."""
    from pyproj import Transformer
    from rasterio.transform import xy
    pp = pd.read_csv(INTERIM / "conn_city" / "pinchpoints.csv").sort_values("dLink", ascending=False).head(2)
    R = np.load(INTERIM / "conn_city" / "resistance.npy", mmap_mode="r")
    ec = json.loads((TABLES / "key_numbers.json").read_text())["connectivity"]["city"]["ec_ha"]["1000"]
    to_ll = Transformer.from_crs(URBAN.crs, 4326, always_xy=True)
    rows = []
    labels = {("1", "7"): ("link", "Видиковачки венац", "Vidikovački venac"),
              ("1", "3"): ("pinch", "Казарма «Баница»", "Banjica barracks")}
    for r in pp.itertuples():
        kind, ru, en = labels[(str(r.i), str(r.j))]
        lon, lat = r.lon, r.lat
        if kind == "link":
            path = np.load(INTERIM / "conn_city" / f"path_{r.i}_{r.j}.npy")
            cells = [(int(k) // R.shape[1], int(k) % R.shape[1]) for k in path]
            row, col = max(cells, key=lambda rc: R[rc])
            lon, lat = to_ll.transform(*xy(URBAN.transform, row, col))
        drop = 1 - np.sqrt(1 - r.dLink / 100)  # dLink is the drop of I = EC^2
        rows.append({"kind": kind, "dlink": round(float(r.dLink), 1), "ec_drop_pct": round(100 * float(drop), 1),
                     "ec_drop_ha": round(float(drop * ec)), "peak": round(float(r.peak_current), 3),
                     "ru": ru, "en": en, "lon": round(float(lon), 5), "lat": round(float(lat), 5)})
    (OUT / "crossings.json").write_text(json.dumps(rows, ensure_ascii=False))
    cells = pd.read_parquet(INTERIM / "gvi_cells.parquet")
    c = pd.read_parquet(INTERIM / "gvi_candidates.parquet")[["cx", "cy", "id", "captured_at"]]
    seg = pd.concat([pd.read_parquet(f) for f in sorted(INTERIM.glob("gvi_seg*.parquet"))]).drop_duplicates("path")
    meta = pd.read_parquet(INTERIM / "gvi_meta.parquet")[["id", "path", "camera_type"]]
    meta["id"] = meta.id.astype(str)
    c["id"] = c.id.astype(str)
    c = c.merge(meta[meta.camera_type == "perspective"], on="id").merge(seg[seg.ok][["path", "Vegetation"]], on="path")
    c = c.sort_values("captured_at", ascending=False).drop_duplicates(["cx", "cy"])  # as in gvi_aggregate
    c = c.merge(cells[["cx", "cy", "unit"]], on=["cx", "cy"])
    from pyproj import Transformer
    tr = Transformer.from_crs(URBAN.crs, 4326, always_xy=True)
    x = (c.cx + 0.5) * 100
    y = (c.cy + 0.5) * 100
    lon, lat = tr.transform(x.values, y.values)
    arr = [[round(a, 5), round(b, 5), round(float(g), 3), str(i), str(t)[:10]]
           for a, b, g, i, t in zip(lon, lat, c.Vegetation, c.id, c.captured_at)]
    (OUT / "gvi.json").write_text(json.dumps({"fields": ["lon", "lat", "gvi", "mapillary_id", "date"], "rows": arr},
                                             separators=(",", ":")))
    print("gvi.json", round((OUT / "gvi.json").stat().st_size / 1e6, 2), "MB", len(arr))


def tables():
    um = pd.read_csv(TABLES / "units_measures.csv")
    keep = ["unit", "pop_2022", "ndvi_mean", "tree_cover_wc_pct", "canopy3_meta_pct", "gvi_mean",
            "green_m2_per_person", "within300_1ha_pct"]
    (OUT / "units.json").write_text(um[keep].round(4).to_json(orient="records", force_ascii=False))
    ec = pd.read_csv(TABLES / "ec_curve.csv")
    ec = ec[ec.run.isin(["main", "permeable", "strict", "city", "city_permeable", "city_strict"])]
    (OUT / "ec_curve.json").write_text(ec[["run", "d50", "ec_ha", "habitat_ha", "ec_share", "ec0_share"]].round(4)
                                       .to_json(orient="records"))
    K = json.loads((TABLES / "key_numbers.json").read_text())
    (OUT / "key_numbers.json").write_text(json.dumps(K, ensure_ascii=False))
    print("tables written")


if __name__ == "__main__":
    patches()
    context()
    points()
    tables()
