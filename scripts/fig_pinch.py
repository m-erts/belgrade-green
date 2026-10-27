"""Figure: one pinch point up close - current through the corridor between two forest patches."""
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

from bgreen.config import FIGURES, INTERIM, RAW
from bgreen.grid import URBAN
from bgreen.viz import style as S

T = {
    "ru": {"title": "Где каркас пережат",
           "sub": "Массив Кошутняк — Топчидер — Дедине и леса Баницы почти смыкаются.\nСвязь идёт через несколько узких разрывов; самый узкий — на территории\nказармы «Баница»",
           "cur": "доля потока через клетку 10 м (теория цепей)",
           "mil": "военные территории (OSM)", "patch": "другие лесные патчи",
           "a": "Кошутняк —\nТопчидер — Дедине", "b": "леса Баницы —\nСтепин луг", "peak": "{p:.0f}% всего потока\nчерез одну клетку",
           "src": "Данные: ESA WorldCover 2021, OpenStreetMap. Метод: теория цепей (McRae et al. 2008),\nкак в Pinchpoint Mapper. Расчёт: Мария Эрцеговац"},
    "en": {"title": "Where the network is squeezed",
           "sub": "The Košutnjak — Topčider — Dedinje forests and the Banjica forests almost\ntouch. The link runs through a few narrow gaps; the narrowest one is on the\ngrounds of the Banjica barracks",
           "cur": "share of the flow through a 10 m cell (circuit theory)",
           "mil": "military land (OSM)", "patch": "other tree patches",
           "a": "Košutnjak —\nTopčider — Dedinje", "b": "Banjica —\nStepin lug forests", "peak": "{p:.0f}% of the whole flow\nthrough one cell",
           "src": "Data: ESA WorldCover 2021, OpenStreetMap. Method: circuit theory (McRae et al. 2008),\nas in Pinchpoint Mapper. Analysis: Marija Ercegovac"},
}


def main(lang="ru", key="3_6", half=420, a_xy=(457230, 4957880), b_xy=(457760, 4957330)):
    S.setup()
    t = T[lang]
    d = INTERIM / "conn_main"
    labels = np.load(d / "labels.npy")
    z = np.load(d / f"current_{key}.npz")
    r0, c0, cur = int(z["r0"]), int(z["c0"]), z["cur"]
    i, j = (int(v) for v in key.split("_"))
    k = np.unravel_index(np.argmax(cur), cur.shape)
    px, py = URBAN.left + (c0 + k[1] + 0.5) * 10, URBAN.top - (r0 + k[0] + 0.5) * 10
    bx = (px - half, px + half, py - half, py + half)
    h, w = cur.shape
    ext = (URBAN.left + c0 * 10, URBAN.left + (c0 + w) * 10, URBAN.top - (r0 + h) * 10, URBAN.top - r0 * 10)
    lab = labels[r0:r0 + h, c0:c0 + w]
    osm = gpd.read_file(RAW / f"osm_zoom_{key}.gpkg").to_crs(URBAN.crs)
    fig = plt.figure(figsize=(5.4, 6.75))
    ax = fig.add_axes([0.04, 0.16, 0.92, 0.64])
    mil = osm[osm.landuse == "military"]
    mil.plot(ax=ax, facecolor="#ecebe6", edgecolor="#c9c8c1", linewidth=0.5, hatch="////", zorder=1)
    streets = osm[osm.highway.notna() & ~osm.highway.isin(["footway", "path", "steps", "cycleway", "track"])]
    streets.plot(ax=ax, color="#d6d4cc", linewidth=0.45, zorder=2)
    ax.imshow(np.where(lab > 0, 1.0, np.nan), extent=ext, cmap=ListedColormap(["#dcecd3"]), interpolation="nearest", zorder=3)
    ax.imshow(np.where(lab == j, 1.0, np.nan), extent=ext, cmap=ListedColormap(["#3f8a36"]),
              interpolation="nearest", zorder=3)
    ax.imshow(np.where(lab == i, 1.0, np.nan), extent=ext, cmap=ListedColormap(["#9fcd8c"]),
              interpolation="nearest", zorder=3)
    m = np.where(cur >= 0.004, cur, np.nan)
    im = ax.imshow(m, extent=ext, cmap=S.SEQ_HEAT, vmin=0, vmax=max(0.15, float(np.nanmax(m))),
                   interpolation="nearest", zorder=4)
    ax.scatter([px], [py], s=120, facecolor="none", edgecolor=S.INK, linewidth=1.2, zorder=6)
    ax.annotate(t["peak"].format(p=100 * cur.max()), (px, py), xytext=(px + 90, py - 200), fontsize=8, color=S.INK,
                fontweight="medium", arrowprops=dict(arrowstyle="-", color=S.INK2, lw=0.7), zorder=7)
    for (x, y), txt in ((a_xy, t["a"]), (b_xy, t["b"])):
        ax.text(x, y, txt, fontsize=8.5, color=S.INK, fontweight="semibold", ha="center", va="center", zorder=7,
                bbox=dict(boxstyle="square,pad=0.2", facecolor=S.SURFACE, edgecolor="none", alpha=0.85))
    ax.set_xlim(bx[0], bx[1])
    ax.set_ylim(bx[2], bx[3])
    ax.set_aspect("equal")
    ax.set_axis_off()
    cax = fig.add_axes([0.06, 0.115, 0.42, 0.012])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7, length=0)
    cb.set_ticks([0, 0.05, 0.10, 0.15])
    cb.set_ticklabels(["0", "5%", "10%", "15%"])
    fig.text(0.06, 0.135, t["cur"], fontsize=7.2, color=S.INK2)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor="#ecebe6", edgecolor="#c9c8c1", hatch="////", label=t["mil"]),
                        Patch(facecolor="#dcecd3", label=t["patch"])],
               loc="lower left", bbox_to_anchor=(0.55, 0.095), fontsize=7.2, frameon=False, handlelength=1.4)
    fig.text(0.06, 0.965, t["title"], fontsize=13, fontweight="semibold", va="top")
    fig.text(0.06, 0.925, t["sub"], fontsize=8.3, color=S.INK2, va="top", linespacing=1.4)
    fig.text(0.06, 0.03, t["src"], fontsize=6, color=S.MUTED, linespacing=1.4)
    out = FIGURES / f"p1_pinch_{key}_{lang}.png"
    fig.savefig(out)
    print(out, "peak", round(float(cur.max()), 3), "at", round(px), round(py))


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["ru"]))
