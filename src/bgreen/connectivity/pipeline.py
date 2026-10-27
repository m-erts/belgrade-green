"""End-to-end connectivity run for one scenario: resistance -> patches -> planar graph -> EC, dPC."""
from __future__ import annotations

import json
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

from bgreen.config import INTERIM, RAW
from bgreen.connectivity import graph, patches, pc, resistance
from bgreen.grid import CITY, URBAN, window_of

D50S = [100, 300, 1000, 3000, 10000]
D50_MAIN = 1000


def aoi_geometry(kind: str, crs):
    """'municipalities': the 10 urban municipalities (1,030 km², incl. their rural parts);
    'settlement': the settlement Beograd only, i.e. the city proper (389 km²)."""
    if kind == "municipalities":
        return gpd.read_file(RAW / "urban_municipalities.gpkg").to_crs(crs).union_all()
    from bgreen.measures import units
    return units.load(crs).union_all()


def base_layers(grid=URBAN, buffer_m=2000, aoi_kind="municipalities"):
    r0, c0 = window_of(grid, CITY)
    with rasterio.open(RAW / "worldcover_2021.tif") as src:
        lc = src.read(1)[r0:r0 + grid.height, c0:c0 + grid.width]
    aoi = aoi_geometry(aoi_kind, grid.crs)
    burn = lambda geom: rasterize([(geom, 1)], out_shape=grid.shape, transform=grid.transform,
                                  fill=0, dtype="uint8").astype(bool)
    return lc, burn(aoi), burn(aoi.buffer(buffer_m))


def run(name: str, scenario: str = "main", nodes: str = "aoi", min_area_ha: float = 1.0,
        d50s=D50S, workers: int = 9, importance: bool = True, grid=URBAN,
        aoi_kind: str = "municipalities") -> Path:
    out = INTERIM / f"conn_{name}"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    lc, aoi, ext = base_layers(grid, aoi_kind=aoi_kind)
    R = resistance.build(lc, grid, gpd.read_file(RAW / "osm_barriers.gpkg"), scenario)
    hab = (lc == 10) & (aoi if nodes == "aoi" else ext)
    labels, areas = patches.label_patches(hab, grid, min_area_ha)
    if nodes == "touching_aoi":  # patches inside the 2 km buffer that touch the AOI, unclipped
        keep = np.unique(labels[aoi & (labels > 0)])
        remap = np.zeros(len(areas) + 1, dtype=np.int32)
        remap[keep] = np.arange(1, len(keep) + 1)
        labels, areas = remap[labels], areas[keep - 1]
    alloc = graph.allocate(R, labels, ext, grid.res)
    links = graph.zone_links(alloc, R)
    n = len(areas)
    A = pc.adjacency(n, links)
    D = pc.apsp(A)
    np.save(out / "aoi_mask.npy", aoi)
    np.save(out / "ext_mask.npy", ext)
    summary = {"name": name, "scenario": scenario, "nodes": nodes, "min_area_ha": min_area_ha,
               "aoi": aoi_kind,
               "n_patches": int(n), "habitat_ha": float(areas.sum()), "n_links": int(len(links)),
               "tree_cover_aoi_ha": float(((lc == 10) & aoi).sum() * grid.res ** 2 / 1e4),
               "ec_no_links_ha": float(np.sqrt((areas ** 2).sum())),
               "ec_ha": {str(d): pc.ec(D, areas, d) for d in d50s}}
    np.save(out / "labels.npy", labels)
    np.save(out / "areas.npy", areas)
    np.save(out / "resistance.npy", R.astype("float32"))
    np.save(out / "alloc_cost.npy", alloc.cost.astype("float32"))
    np.save(out / "alloc_zone.npy", alloc.zone)
    np.save(out / "alloc_pred.npy", alloc.pred)
    links.to_parquet(out / "links.parquet")
    if importance:
        inter, used = pc.on_some_best_path(A)
        imp = pc.node_importance(A, areas, [300, 1000, 3000], candidates=inter, workers=workers)
        imp["patch"] = imp["node"] + 1
        imp["area_ha"] = areas
        imp.to_parquet(out / "node_importance.parquet")
        limp = pc.link_importance(A, areas, [300, 1000, 3000], used, workers=workers)
        limp["i"], limp["j"] = limp["u"] + 1, limp["v"] + 1
        limp.to_parquet(out / "link_importance.parquet")
    summary["seconds"] = round(time.time() - t0, 1)
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    return out
