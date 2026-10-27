"""Plain Overpass client with mirrors and an on-disk cache (osmnx is used only for networks)."""
from __future__ import annotations

import hashlib
import json
import time

import requests

from bgreen.config import CACHE, USER_AGENT

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
_DIR = CACHE / "overpass"
_DIR.mkdir(parents=True, exist_ok=True)


def query(q: str, timeout: int = 600) -> dict:
    key = hashlib.sha1(q.encode()).hexdigest()
    path = _DIR / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    last = None
    for attempt in range(3):
        for url in MIRRORS:
            try:
                r = requests.post(url, data={"data": q}, timeout=timeout,
                                  headers={"User-Agent": USER_AGENT})
                if r.status_code == 200 and r.text.lstrip().startswith("{"):
                    d = r.json()
                    if not d.get("elements") and d.get("remark"):
                        last = f"{url}: {d['remark'][:200]}"
                        continue
                    d["_mirror"] = url
                    path.write_text(json.dumps(d))
                    return d
                last = f"{url}: HTTP {r.status_code} {r.text[:200]!r}"
            except requests.RequestException as e:  # try the next mirror
                last = f"{url}: {e}"
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"Overpass failed on all mirrors: {last}")


def to_gdf(d: dict, polygons_only: bool = False):
    """Overpass JSON (`out geom`) to a GeoDataFrame: ways as lines or polygons, relations as
    (multi)polygons assembled from their outer and inner member ways."""
    import geopandas as gpd
    from shapely.geometry import LineString, MultiPolygon, Point, Polygon
    from shapely.ops import polygonize, unary_union

    rows = []
    for e in d["elements"]:
        tags = e.get("tags", {})
        geom = None
        if e["type"] == "node" and "lat" in e:
            geom = Point(e["lon"], e["lat"])
        elif e["type"] == "way" and e.get("geometry"):
            pts = [(p["lon"], p["lat"]) for p in e["geometry"]]
            closed = len(pts) > 3 and pts[0] == pts[-1]
            if closed and (polygons_only or _is_area(tags)):
                geom = Polygon(pts)
            elif not polygons_only and len(pts) >= 2:
                geom = LineString(pts)
        elif e["type"] == "relation":
            outer, inner = [], []
            for m in e.get("members", []):
                if m.get("type") != "way" or not m.get("geometry"):
                    continue
                line = LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
                (inner if m.get("role") == "inner" else outer).append(line)
            if outer:
                polys = list(polygonize(unary_union(outer)))
                if polys:
                    geom = unary_union(polys)
                    if inner:
                        holes = list(polygonize(unary_union(inner)))
                        if holes:
                            geom = geom.difference(unary_union(holes))
                    if isinstance(geom, Polygon):
                        geom = MultiPolygon([geom])
        if geom is None or geom.is_empty:
            continue
        rows.append({"osm_type": e["type"], "osm_id": e["id"], **tags, "geometry": geom})
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    if polygons_only and len(gdf):
        gdf = gdf[gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
    return gdf


def _is_area(tags: dict) -> bool:
    if tags.get("area") == "no":
        return False
    keys = ("building", "landuse", "leisure", "natural", "amenity", "boundary", "place", "water")
    return tags.get("area") == "yes" or any(k in tags for k in keys)
