"""Figure: street-level Green View Index on a 100 m grid over the city proper."""
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bgreen.config import FIGURES, INTERIM, TABLES
from bgreen.grid import URBAN
from bgreen.viz import maps
from bgreen.viz import style as S

T = {"ru": {"title": "Сколько зелени видно с улицы",
            "sub": "Green View Index: доля растительности в кадре уличной съемки.\nТочка — ячейка 100 м, последний летний снимок. {n} снимков Mapillary, разметка Mask2Former",
            "cb": "GVI, доля растительности в кадре",
            "src": "Данные: Mapillary (CC BY-SA 4.0), OpenStreetMap. Модель: Mask2Former (Mapillary Vistas).\nРасчёт: Мария Эрцеговац"},
     "en": {"title": "How much green you see from the street",
            "sub": "Green View Index: share of vegetation in street-level images. Each dot is\na 100 m cell with its newest summer image. {n} Mapillary images, Mask2Former",
            "cb": "GVI, share of vegetation in view",
            "src": "Data: Mapillary (CC BY-SA 4.0), OpenStreetMap. Model: Mask2Former (Mapillary Vistas).\nAnalysis: Marija Ercegovac"}}


def main(lang="ru"):
    S.setup()
    t = T[lang]
    cells = pd.read_parquet(INTERIM / "gvi_cells.parquet")
    g = gpd.GeoDataFrame(cells, geometry=gpd.points_from_xy(cells.lon, cells.lat), crs=4326).to_crs(URBAN.crs)
    n = int(pd.read_json(TABLES / "gvi_meta.json", typ="series")["images"])
    u = maps._layers()["units"]
    b = u.total_bounds
    fig = plt.figure(figsize=(5.4, 6.75))
    ax = fig.add_axes([0.0, 0.12, 1.0, 0.72])
    maps.base(ax, bounds=(b[0] - 600, b[1] - 600, b[2] + 600, b[3] + 600), roads=False, mun=False, units=True)
    order = np.argsort(g.gvi.values)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("gvi", S.GREENS[2:])
    sc = ax.scatter(g.geometry.x.values[order], g.geometry.y.values[order], c=g.gvi.values[order], s=2.2,
                    cmap=cmap, vmin=0, vmax=0.6, linewidths=0, zorder=5)
    maps.scalebar(ax, km=2, loc=(0.05, 0.03), lang=lang)
    cax = fig.add_axes([0.06, 0.095, 0.42, 0.012])
    cb = fig.colorbar(sc, cax=cax, orientation="horizontal")
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7, length=0)
    cb.set_ticks([0, 0.2, 0.4, 0.6])
    cb.set_ticklabels(["0", "20%", "40%", "≥ 60%"])
    fig.text(0.06, 0.115, t["cb"], fontsize=7.2, color=S.INK2)
    fig.text(0.06, 0.965, t["title"], fontsize=13, fontweight="semibold", va="top")
    fig.text(0.06, 0.925, t["sub"].format(n=f"{n:,}".replace(",", " " if lang == "ru" else ",")), fontsize=8,
             color=S.INK2, va="top", linespacing=1.4)
    fig.text(0.06, 0.022, t["src"], fontsize=6, color=S.MUTED, linespacing=1.4)
    out = FIGURES / f"p2_gvi_map_{lang}.png"
    fig.savefig(out)
    print(out)


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["ru"]))
