"""Figure: the tree network of the city proper, with the strongest bridge and the key crossings."""
import json
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from bgreen.config import FIGURES, INTERIM
from bgreen.viz import maps
from bgreen.viz import style as S

NBSP = " "
GREEN = "#9fcd8c"
T = {
    "ru": {"title": "Лесной каркас Белграда как граф",
           "sub": "Город в пределах насеља «Београд»: {n} лесных патчей ≥ 1 га, вместе {a} га.\nДля вида с расселением 1 км по лесу они работают как один лес в {ec} га ({p}%)",
           "patch": "лесной патч ≥ 1 га", "bridge": "мост: его потеря стоит сети больше его площади",
           "gap": "переход, на котором держится больше всего связности",
           "labels": {1: "Баница — Миляковац —\nСтепин луг", 2: "Ада Циганлия", 3: "Кошутняк", 7: "Беле Воде",
                      25: "Центральное\nкладбище", 9: "Велико ратно\nострво", 10: "Звездарская\nшума", 59: "Калемегдан"},
           "src": "Данные: ESA WorldCover 2021, OpenStreetMap. Метод: PC, EC, dPC (Saura et al.), граф как в Graphab,\nсценарии застройки с пересчётом сети. Расчёт: Мария Эрцеговац"},
    "en": {"title": "Belgrade's tree network as a graph",
           "sub": "The city proper (settlement Beograd): {n} tree patches ≥ 1 ha, {a} ha in total.\nFor a species dispersing 1 km through forest they work like one forest of {ec} ha ({p}%)",
           "patch": "tree patch ≥ 1 ha", "bridge": "bridge: losing it costs the network more than its area",
           "gap": "crossing that carries the most connectivity",
           "labels": {1: "Banjica — Miljakovac —\nStepin lug", 2: "Ada Ciganlija", 3: "Košutnjak", 7: "Bele Vode",
                      25: "Central\nCemetery", 9: "Great War\nIsland", 10: "Zvezdara\nforest", 59: "Kalemegdan"},
           "src": "Data: ESA WorldCover 2021, OpenStreetMap. Method: PC, EC, dPC (Saura et al.), Graphab-style graph,\nbuild-over scenarios with the network rebuilt. Analysis: Marija Ercegovac"},
}
OFFSETS = {1: (2600, -2600), 2: (-3400, -1400), 3: (-3800, 2600), 7: (-3600, -1500), 25: (2900, 900),
           9: (-4200, 1300), 10: (2600, 1600), 59: (900, 2900)}


def robust_bridges(d, min_lev=1.15):
    """Patches whose build-over costs more EC than their area both with patches clipped to the
    city and with whole patches (the *_touching run), so the result is not a boundary artefact."""
    bo = pd.read_parquet(d / "buildover.parquet")
    a = bo[(bo.leverage_1000 >= min_lev) & (bo.area_ha < 1000)]
    t = d.parent / f"{d.name}_touching"
    if not (t / "buildover.parquet").exists():
        return a.patch.tolist()
    lab, lab_t = np.load(d / "labels.npy"), np.load(t / "labels.npy")
    bt = pd.read_parquet(t / "buildover.parquet").set_index("patch")
    keep = []
    for p in a.patch:
        ids, c = np.unique(lab_t[lab == p], return_counts=True)
        ids, c = ids[ids > 0], c[ids > 0]
        if len(ids) and ids[np.argmax(c)] in bt.index and bt.loc[ids[np.argmax(c)], "leverage_1000"] >= min_lev:
            keep.append(int(p))
    return keep


def fmt(x, lang):
    s = f"{x:,.0f}"
    return s.replace(",", NBSP) if lang == "ru" else s


def main(lang="ru", run="city"):
    S.setup()
    t = T[lang]
    d = INTERIM / f"conn_{run}"
    s = json.loads((d / "summary.json").read_text())
    labels = np.load(d / "labels.npy")
    names = pd.read_parquet(d / "patch_names.parquet").set_index("patch")
    bridges = robust_bridges(d)
    pp = pd.read_csv(d / "pinchpoints.csv").sort_values("dLink", ascending=False).head(2)
    u = maps._layers()["units"]
    b = u.total_bounds
    fig = plt.figure(figsize=(5.4, 6.75))
    ax = fig.add_axes([0.0, 0.11, 1.0, 0.72])
    maps.base(ax, bounds=(b[0] - 600, b[1] - 600, b[2] + 600, b[3] + 600), roads=True, mun=False, units=True)
    ext = maps.extent()
    ax.imshow(np.where(labels > 0, 1.0, np.nan), extent=ext, cmap=ListedColormap([GREEN]), interpolation="nearest",
              zorder=4)
    ax.imshow(np.where(np.isin(labels, bridges), 1.0, np.nan), extent=ext, cmap=ListedColormap([S.ACCENT]),
              interpolation="nearest", zorder=5)
    ax.scatter(pp.peak_x if "peak_x" in pp else [], pp.peak_y if "peak_y" in pp else [], s=1)
    for p, txt in t["labels"].items():
        if p not in names.index:
            continue
        x, y = names.loc[p, "x"], names.loc[p, "y"]
        dx, dy = OFFSETS.get(p, (2000, 2000))
        ax.annotate(txt, (x, y), xytext=(x + dx, y + dy), fontsize=7.2, color=S.INK, ha="center", va="center",
                    zorder=8, arrowprops=dict(arrowstyle="-", color=S.INK2, lw=0.5, shrinkA=0, shrinkB=2),
                    bbox=dict(boxstyle="square,pad=0.15", facecolor=S.SURFACE, edgecolor="none", alpha=0.8))
    maps.scalebar(ax, km=2, loc=(0.05, 0.03), lang=lang)
    ec, a = s["ec_ha"]["1000"], s["habitat_ha"]
    fig.text(0.06, 0.965, t["title"], fontsize=13, fontweight="semibold", va="top")
    fig.text(0.06, 0.925, t["sub"].format(n=fmt(s["n_patches"], lang), a=fmt(a, lang), ec=fmt(ec, lang),
                                          p=f"{100 * ec / a:.0f}"), fontsize=8, color=S.INK2, va="top", linespacing=1.4)
    handles = [Patch(color=GREEN, label=t["patch"]), Patch(color=S.ACCENT, label=t["bridge"]),
               Line2D([], [], marker="D", color=S.INK, lw=0, markersize=5, label=t["gap"])]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.05, 0.055), fontsize=7, frameon=False,
               handlelength=1.2, borderaxespad=0)
    fig.text(0.06, 0.018, t["src"], fontsize=6, color=S.MUTED, linespacing=1.4)
    return fig, ax, d


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "ru"
    fig, ax, d = main(lang)
    # crossings: peak cells of the two most important links
    pp = pd.read_csv(d / "pinchpoints.csv").sort_values("dLink", ascending=False).head(2)
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32634", always_xy=True)
    xs, ys = tr.transform(pp.lon.values, pp.lat.values)
    ax.scatter(xs, ys, s=40, marker="D", color=S.INK, edgecolor=S.SURFACE, linewidth=1.4, zorder=9)
    out = FIGURES / f"p1_city_network_{lang}.png"
    fig.savefig(out)
    print(out)
