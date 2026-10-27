"""Mapillary street-level imagery (API v4). The client token is read from ~/.mapillary_token and
never printed or written anywhere else."""
from __future__ import annotations

import concurrent.futures as cf
import math
import time
from pathlib import Path

import mercantile
import pandas as pd
import requests

from bgreen.config import CACHE, RAW

TOKEN_FILE = Path.home() / ".mapillary_token"
TILES = "https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}"
GRAPH = "https://graph.mapillary.com"
TILE_CACHE = CACHE / "mly_tiles"
THUMBS = RAW / "mly_thumbs"
for _p in (TILE_CACHE, THUMBS):
    _p.mkdir(parents=True, exist_ok=True)


def _token() -> str:
    return TOKEN_FILE.read_text().strip()


def _tile_to_lonlat(tx, ty, z, x, y, extent):
    n = 2.0 ** z
    lon = (tx + x / extent) / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + y / extent) / n))))
    return lon, lat


def _get(url, params, attempts=5, timeout=60):
    for k in range(attempts):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(5 * (k + 1))
                continue
            r.raise_for_status()
        except requests.RequestException:
            if k == attempts - 1:
                raise
            time.sleep(5 * (k + 1))
    raise RuntimeError(f"giving up on {url.split('?')[0]}")


def tile_images(t: mercantile.Tile) -> pd.DataFrame:
    import mapbox_vector_tile

    path = TILE_CACHE / f"{t.z}_{t.x}_{t.y}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    r = _get(TILES.format(z=t.z, x=t.x, y=t.y), {"access_token": _token()})
    rows = []
    if r.content:
        d = mapbox_vector_tile.decode(r.content, default_options={"y_coord_down": True})
        layer = d.get("image", {})
        ext = layer.get("extent", 4096)
        for f in layer.get("features", []):
            x, y = f["geometry"]["coordinates"]
            lon, lat = _tile_to_lonlat(t.x, t.y, t.z, x, y, ext)
            p = f["properties"]
            rows.append({"id": int(p.get("id", f.get("id"))), "lon": lon, "lat": lat,
                         "captured_at": p.get("captured_at"), "is_pano": p.get("is_pano"),
                         "compass_angle": p.get("compass_angle"), "sequence_id": p.get("sequence_id"),
                         "creator_id": p.get("creator_id"), "organization_id": p.get("organization_id")})
    df = pd.DataFrame(rows)
    df.to_parquet(path)
    return df


def coverage(bbox_ll, z=14, workers=8) -> pd.DataFrame:
    tiles = list(mercantile.tiles(*bbox_ll, zooms=z))
    with cf.ThreadPoolExecutor(workers) as ex:
        parts = list(ex.map(tile_images, tiles))
    df = pd.concat([p for p in parts if len(p)], ignore_index=True).drop_duplicates("id")
    df["captured_at"] = pd.to_datetime(df["captured_at"], unit="ms", utc=True)
    return df


FIELDS = "id,thumb_1024_url,captured_at,is_pano,camera_type,width,height,computed_compass_angle,sequence"


def entities(ids, workers=32) -> pd.DataFrame:
    tok = _token()

    def one(i):
        try:
            r = _get(f"{GRAPH}/{int(i)}", {"access_token": tok, "fields": FIELDS})
            return r.json()
        except Exception:
            return {"id": str(i), "error": True}

    with cf.ThreadPoolExecutor(workers) as ex:
        out = list(ex.map(one, ids))
    return pd.DataFrame(out)


def download(meta: pd.DataFrame, workers=32) -> pd.Series:
    def one(row):
        path = THUMBS / f"{row.id}.jpg"
        if path.exists() and path.stat().st_size > 0:
            return str(path)
        url = getattr(row, "thumb_1024_url", None)
        if not isinstance(url, str):
            return None
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and r.content:
                path.write_bytes(r.content)
                return str(path)
        except requests.RequestException:
            return None
        return None

    with cf.ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, meta.itertuples(index=False)))
    return pd.Series(res, index=meta.index)
