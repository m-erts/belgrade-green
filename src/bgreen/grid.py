"""One 10 m analysis grid (UTM 34N) shared by every raster in the project.

Edges sit on multiples of 10 m, so the grid is aligned with Sentinel-2 tile 34TDQ and
Sentinel-2 bands can be read without resampling."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from affine import Affine

from bgreen.config import CRS_M


@dataclass(frozen=True)
class Grid:
    left: float
    top: float
    width: int
    height: int
    res: float = 10.0
    crs: str = CRS_M

    @property
    def transform(self) -> Affine:
        return Affine(self.res, 0, self.left, 0, -self.res, self.top)

    @property
    def shape(self):
        return (self.height, self.width)

    @property
    def bounds(self):
        return (self.left, self.top - self.height * self.res, self.left + self.width * self.res, self.top)

    def profile(self, dtype="uint8", nodata=0, count=1):
        return dict(driver="GTiff", height=self.height, width=self.width, count=count, dtype=dtype,
                    crs=self.crs, transform=self.transform, nodata=nodata, compress="deflate",
                    tiled=True, blockxsize=512, blockysize=512, BIGTIFF="IF_SAFER")

    def coarsen(self, factor: int) -> "Grid":
        return Grid(self.left, self.top, int(np.ceil(self.width / factor)), int(np.ceil(self.height / factor)),
                    self.res * factor, self.crs)


def from_bounds(xmin, ymin, xmax, ymax, res=10.0, margin=0.0) -> Grid:
    left = np.floor((xmin - margin) / res) * res
    bottom = np.floor((ymin - margin) / res) * res
    right = np.ceil((xmax + margin) / res) * res
    top = np.ceil((ymax + margin) / res) * res
    return Grid(float(left), float(top), int(round((right - left) / res)), int(round((top - bottom) / res)), res)


# The City of Belgrade (all 17 municipalities) plus a 1 km margin.
CITY = from_bounds(416157.135, 4898527.242, 490567.135, 4996817.242, margin=0.0)

# The 10 urban municipalities (bbox from OSM boundaries) plus a 2 km margin; a sub-window of CITY.
URBAN = from_bounds(432185.05, 4935901.12, 470747.58, 4993904.43, margin=2000.0)


def window_of(sub: Grid, parent: Grid):
    """Row/column offsets of an aligned sub-grid inside a parent grid."""
    col = int(round((sub.left - parent.left) / parent.res))
    row = int(round((parent.top - sub.top) / parent.res))
    return row, col
