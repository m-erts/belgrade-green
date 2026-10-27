"""Units of comparison: the part of the settlement "Beograd" inside each of the 10 urban
municipalities (OSM admin_level 9, codes from the RZS register), with Census 2022 population."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
from rasterio.features import rasterize

from bgreen.config import RAW
from bgreen.grid import Grid

# Popis 2022, RZS table "Ukupan broj stanovnika, po naseljima" (popis2022.stat.gov.rs/media/31319)
CENSUS_2022 = {
    "Voždovac": 155909, "Vračar": 55406, "Zvezdara": 172625, "Zemun": 166049,
    "Novi Beograd": 209763, "Palilula": 113883, "Rakovica": 104456, "Savski venac": 36699,
    "Stari grad": 44737, "Čukarica": 138187,
}


def load(crs) -> gpd.GeoDataFrame:
    g = gpd.read_file(RAW / "osm_admin_9_10.gpkg")
    u = g[g["name:sr-Latn"].fillna("").str.startswith("Beograd (")].copy()
    u["unit"] = u["name:sr-Latn"].str.extract(r"Beograd \((.*)\)", expand=False)
    u["pop_2022"] = u["unit"].map(CENSUS_2022)
    assert u["pop_2022"].notna().all() and len(u) == 10
    assert int(u["population"].astype(int).sum()) == sum(CENSUS_2022.values())  # OSM tag = census
    u = u.to_crs(crs)[["unit", "pop_2022", "ref:RS:naselje", "geometry"]].sort_values("unit")
    u["uid"] = np.arange(1, len(u) + 1)
    return u.reset_index(drop=True)


def raster(units: gpd.GeoDataFrame, grid: Grid) -> np.ndarray:
    return rasterize(list(zip(units.geometry, units.uid)), out_shape=grid.shape, transform=grid.transform,
                     fill=0, dtype="int16")
