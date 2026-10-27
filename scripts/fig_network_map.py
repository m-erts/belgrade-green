"""Figure: Belgrade's tree network, with the patches and gaps whose loss costs the most."""
import json
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from bgreen.config import FIGURES, INTERIM
from bgreen.grid import URBAN
from bgreen.viz import maps
from bgreen.viz import style as S

NBSP = " "
T = {
    "ru": {"title": "Лесной каркас Белграда как граф",
           "sub": "{n} лесных патчей ≥ 1 га в 10 городских общинах. Вместе это {a} га,\nа работают они как один лес в {ec} га ({p}%)",
           "patch": "лесной патч ≥ 1 га", "bridge": "«мост»: потеря бьёт по сети сильнее своей площади",
           "gap": "разрыв, через который идёт больше всего связности",
           "src": "Данные: ESA WorldCover 2021, OpenStreetMap. Метод: PC, EC, dPC (Saura et al.), граф как в Graphab.\nДистанция расселения 1 км. Расчёт: Мария Эрцеговац"},
    "en": {"title": "Belgrade's tree network as a graph",
           "sub": "{n} tree patches ≥ 1 ha in 10 urban municipalities. Together {a} ha;\nthey work like a single forest of {ec} ha ({p}%)",
           "patch": "tree patch ≥ 1 ha", "bridge": "bridge: losing it costs the network more than its own area",
           "gap": "gap that carries the most connectivity",
           "src": "Data: ESA WorldCover 2021, OpenStreetMap. Method: PC, EC, dPC (Saura et al.), Graphab-style graph.\nDispersal distance 1 km. Analysis: Marija Ercegovac"},
}


def fmt(x, lang):
    s = f"{x:,.0f}"
    return s.replace(",", NBSP) if lang == "ru" else s


def main(lang="ru", run="main", callouts=None):
    S.setup()
    t = T[lang]
    d = INTERIM / f"conn_{run}"
    s = json.loads((d / "summary.json").read_text())
    labels = np.load(d / "labels.npy")
    ec, a = s["ec_ha"]["1000"], s["habitat_ha"]
    fig = plt.figure(figsize=(5.4, 6.75))
    ax = fig.add_axes([0.0, 0.10, 1.0, 0.74])
    maps.base(ax, roads=True, mun=True)
    ext = maps.extent()
    ax.imshow(np.where(labels > 0, 1.0, np.nan), extent=ext, cmap=ListedColormap(["#9fcd8c"]),
              interpolation="nearest", zorder=4)
    bridges = []
    if (d / "buildover.parquet").exists():
        bo = pd.read_parquet(d / "buildover.parquet")
        bo = bo[(bo.connector_1000 / bo.dPC_1000 >= 0.5) & (bo.leverage_1000 >= 1.5)]
        bridges = bo.sort_values("EC_loss_1000", ascending=False).patch.tolist()[:6]
    if bridges:
        ax.imshow(np.where(np.isin(labels, bridges), 1.0, np.nan), extent=ext, cmap=ListedColormap([S.ACCENT]),
                  interpolation="nearest", zorder=5)
        names = pd.read_parquet(d / "patch_names.parquet").set_index("patch")
        for p in bridges:
            x, y = names.loc[p, "x"], names.loc[p, "y"]
            ax.scatter([x], [y], s=60, facecolor="none", edgecolor=S.ACCENT, linewidth=1.4, zorder=6)
    pp = pd.read_csv(d / "pinchpoints.csv") if (d / "pinchpoints.csv").exists() else None
    if pp is not None:
        top = pp.sort_values("dLink_1000", ascending=False).head(3)
        ax.scatter(top.peak_x, top.peak_y, s=34, marker="D", color=S.INK, edgecolor=S.SURFACE, linewidth=1.4,
                   zorder=7)
    for (x, y, text, dx, dy) in (callouts or []):
        ax.annotate(text, (x, y), xytext=(x + dx, y + dy), fontsize=7.2, color=S.INK, zorder=8,
                    arrowprops=dict(arrowstyle="-", color=S.INK2, lw=0.6), va="center")
    maps.scalebar(ax, km=5, loc=(0.05, 0.03), lang=lang)
    fig.text(0.06, 0.965, t["title"], fontsize=13, fontweight="semibold", va="top")
    fig.text(0.06, 0.925, t["sub"].format(n=fmt(s["n_patches"], lang), a=fmt(a, lang), ec=fmt(ec, lang),
                                          p=f"{100 * ec / a:.0f}"), fontsize=8.3, color=S.INK2, va="top",
             linespacing=1.4)
    handles = [Patch(color="#9fcd8c", label=t["patch"]), Patch(color=S.ACCENT, label=t["bridge"]),
               Line2D([], [], marker="D", color=S.INK, lw=0, markersize=5, label=t["gap"])]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.05, 0.055), fontsize=7, frameon=False,
               handlelength=1.2, borderaxespad=0)
    fig.text(0.06, 0.018, t["src"], fontsize=6, color=S.MUTED, linespacing=1.4)
    out = FIGURES / f"p1_network_{lang}.png"
    fig.savefig(out)
    print(out)


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["ru"]))
