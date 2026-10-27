"""Quiet base map from the project's own layers: water, major roads, boundaries."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import rasterio

from bgreen.config import RAW
from bgreen.grid import CITY, URBAN, window_of
from bgreen.viz import style as S

_cache = {}


def _layers():
    if not _cache:
        r0, c0 = window_of(URBAN, CITY)
        with rasterio.open(RAW / "worldcover_2021.tif") as s:
            lc = s.read(1)[r0:r0 + URBAN.height, c0:c0 + URBAN.width]
        _cache["water"] = lc == 80
        b = gpd.read_file(RAW / "osm_barriers.gpkg").to_crs(URBAN.crs)
        from shapely.geometry import box
        frame = box(URBAN.left, URBAN.top - URBAN.height * URBAN.res, URBAN.left + URBAN.width * URBAN.res, URBAN.top)
        _cache["roads"] = b[b["highway"].isin(["motorway", "trunk", "primary"])].clip(frame)
        _cache["rail"] = b[b["railway"].isin(["rail"])].clip(frame)
        _cache["mun"] = gpd.read_file(RAW / "urban_municipalities.gpkg").to_crs(URBAN.crs)
        from bgreen.measures import units
        _cache["units"] = units.load(URBAN.crs)
    return _cache


def extent(grid=URBAN):
    return (grid.left, grid.left + grid.width * grid.res, grid.top - grid.height * grid.res, grid.top)


def base(ax, bounds=None, roads=True, mun=True, units=False, road_lw=0.35):
    L = _layers()
    ext = extent()
    water = np.where(L["water"], 1.0, np.nan)
    ax.imshow(water, extent=ext, cmap=_flat(S.WATER), vmin=0, vmax=1, interpolation="nearest", zorder=1)
    if roads:
        L["roads"].plot(ax=ax, color="#d8d6cf", linewidth=road_lw, zorder=2)
    if mun:
        L["mun"].boundary.plot(ax=ax, color="#b9b7ae", linewidth=0.5, zorder=3)
    if units:
        L["units"].boundary.plot(ax=ax, color="#9a988f", linewidth=0.5, zorder=3)
    if bounds is not None:
        ax.set_xlim(bounds[0], bounds[2])
        ax.set_ylim(bounds[1], bounds[3])
    else:
        b = L["mun"].total_bounds
        ax.set_xlim(b[0] - 800, b[2] + 800)
        ax.set_ylim(b[1] - 800, b[3] + 800)
    ax.set_aspect("equal")
    ax.set_axis_off()


def _flat(color):
    from matplotlib.colors import ListedColormap
    return ListedColormap([color])


def scalebar(ax, km=5, loc=(0.06, 0.05), color=None, lang="en"):
    color = color or S.INK2
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x = x0 + loc[0] * (x1 - x0)
    y = y0 + loc[1] * (y1 - y0)
    ax.plot([x, x + km * 1000], [y, y], color=color, lw=1.2, solid_capstyle="butt", zorder=20)
    unit = "км" if lang == "ru" else "km"
    ax.text(x + km * 500, y + 0.012 * (y1 - y0), f"{km} {unit}", ha="center", va="bottom", fontsize=7.5,
            color=color, zorder=20)
