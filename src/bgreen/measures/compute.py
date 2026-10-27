"""Per-unit greenery measures for the 10 urban parts of Belgrade."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import rasterio

from bgreen.config import INTERIM, RAW, TABLES
from bgreen.grid import CITY, URBAN, Grid, window_of
from bgreen.measures import access, green, units


def _block_sum(a: np.ndarray, f: int) -> np.ndarray:
    H, W = a.shape
    h, w = int(np.ceil(H / f)), int(np.ceil(W / f))
    pad = np.zeros((h * f, w * f), dtype=a.dtype)
    pad[:H, :W] = a
    return pad.reshape(h, f, w, f).sum(axis=(1, 3))


def layers():
    r0, c0 = window_of(URBAN, CITY)
    with rasterio.open(RAW / "worldcover_2021.tif") as s:
        lc = s.read(1)[r0:r0 + URBAN.height, c0:c0 + URBAN.width]
    with rasterio.open(RAW / "canopy_cover_meta.tif") as s:
        can = {t: s.read(i + 1) for i, t in enumerate((2, 3, 5))}
    nd = None
    p = RAW / "ndvi_summer2025.tif"
    if p.exists():
        with rasterio.open(p) as s:
            nd = s.read(1)
    return lc, can, nd


def run(radius=300.0, fine=50.0):
    u = units.load(URBAN.crs)
    ur = units.raster(u, URBAN)
    lc, can, nd = layers()
    land = (lc != 80) & (lc != 0)
    parts = green.dissolved(URBAN.crs)
    gmask = green.mask(parts, URBAN) & (lc != 80)  # a lake inside a protected area is not green space
    rows = []
    for _, r in u.iterrows():
        m = (ur == r.uid) & land
        area_ha = m.sum() * 0.01
        row = {"unit": r.unit, "pop_2022": int(r.pop_2022), "land_km2": area_ha / 100,
               "density_per_km2": r.pop_2022 / (area_ha / 100),
               "tree_cover_wc_pct": 100 * (lc[m] == 10).mean(),
               "canopy3_meta_pct": 100 * np.nanmean(can[3][m]),
               "canopy2_meta_pct": 100 * np.nanmean(can[2][m]),
               "canopy5_meta_pct": 100 * np.nanmean(can[5][m]),
               "public_green_ha": gmask[ur == r.uid].sum() * 0.01}
        row["green_m2_per_person"] = row["public_green_ha"] * 1e4 / r.pop_2022
        if nd is not None:
            row["ndvi_mean"] = float(np.nanmean(nd[m]))
            row["ndvi_gt05_pct"] = 100 * float(np.nanmean(nd[m] > 0.5))
        rows.append(row)
    df = pd.DataFrame(rows)

    # access on a 50 m grid: population from the 100 m grid split evenly, green as m² per cell
    f = int(fine / URBAN.res)
    gfine = URBAN.coarsen(f)
    green_m2 = _block_sum(gmask.astype("float64"), f) * URBAN.res ** 2
    pop100 = np.load(INTERIM / "pop100_2022.npy").astype("float64")
    rep = int(100 / fine)
    pop = np.kron(pop100, np.ones((rep, rep))) / rep ** 2
    pop = pop[:gfine.height, :gfine.width]
    ur_f = units.raster(u, gfine)
    A = access.two_step_fca(green_m2, pop, radius, fine)
    big1 = green.mask(parts[parts.area_ha >= 1.0], gfine)
    big05 = green.mask(parts[parts.area_ha >= 0.5], gfine)
    near1 = access.within(big1, radius, fine)
    near05 = access.within(big05, radius, fine)
    can_f = _block_sum(np.nan_to_num(can[3]), f) / (f * f)
    can_nb = access._conv(can_f, access.disk(radius, fine)) / access.disk(radius, fine).sum()
    acc = []
    for _, r in u.iterrows():
        m = ur_f == r.uid
        p = pop[m]
        P = p.sum()
        acc.append({"unit": r.unit,
                    "access_m2_per_person_2sfca": float((A[m] * p).sum() / P),
                    "below_7m2_pct": 100 * float(p[A[m] < 7].sum() / P),
                    "below_10m2_pct": 100 * float(p[A[m] < 10].sum() / P),
                    "below_23m2_pct": 100 * float(p[A[m] < 23].sum() / P),
                    "within300_1ha_pct": 100 * float(p[near1[m]].sum() / P),
                    "within300_05ha_pct": 100 * float(p[near05[m]].sum() / P),
                    "canopy30_neighbourhood_pct": 100 * float(p[can_nb[m] >= 0.30].sum() / P)})
    df = df.merge(pd.DataFrame(acc), on="unit")
    tot_pop = pop.sum()
    city = {"pop": float(tot_pop),
            "access_m2_per_person_2sfca": float((A * pop).sum() / tot_pop),
            "below_7m2_pct": 100 * float(pop[A < 7].sum() / tot_pop),
            "below_10m2_pct": 100 * float(pop[A < 10].sum() / tot_pop),
            "below_23m2_pct": 100 * float(pop[A < 23].sum() / tot_pop),
            "within300_1ha_pct": 100 * float(pop[near1].sum() / tot_pop),
            "canopy30_neighbourhood_pct": 100 * float(pop[can_nb >= 0.30].sum() / tot_pop),
            "public_green_ha_in_units": float(df.public_green_ha.sum()),
            "green_m2_per_person_all_units": float(df.public_green_ha.sum() * 1e4 / df.pop_2022.sum())}
    np.save(INTERIM / "access_2sfca_50m.npy", A.astype("float32"))
    np.save(INTERIM / "pop50.npy", pop.astype("float32"))
    df.to_csv(TABLES / "units_measures.csv", index=False)
    (TABLES / "city_access.json").write_text(json.dumps(city, indent=1))
    return df, city
