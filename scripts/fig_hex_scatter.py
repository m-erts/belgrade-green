"""Figure: NDVI and 1 m canopy against the street-level GVI, per H3 hexagon (res 8, ~0.7 km²)."""
import sys

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

from bgreen.config import FIGURES, INTERIM
from bgreen.viz import style as S

HL = {"Stari grad": S.CAT[0], "Vračar": S.CAT[1], "Novi Beograd": S.CAT[2]}
NAMES_RU = {"Stari grad": "Стари-Град", "Vračar": "Врачар", "Novi Beograd": "Новый Белград"}
T = {"ru": {"title": "Сверху и с улицы — разная зелень",
            "sub": "Каждая точка — шестиугольник H3 (~0,7 км²) с ≥ 10 ячейками уличной съемки",
            "x1": "NDVI, лето 2025", "x2": "кроны ≥ 3 м, % площади (Meta)", "y": "GVI с улицы",
            "other": "остальные районы",
            "src": "Данные: Sentinel-2, Meta/WRI Canopy Height, Mapillary. Расчёт: Мария Эрцеговац"},
     "en": {"title": "Green from above, green from the street",
            "sub": "Each dot is an H3 hexagon (~0.7 km²) with ≥ 10 street-level sampling cells",
            "x1": "NDVI, summer 2025", "x2": "canopy ≥ 3 m, % of area (Meta)", "y": "street-level GVI",
            "other": "other districts",
            "src": "Data: Sentinel-2, Meta/WRI Canopy Height, Mapillary. Analysis: Marija Ercegovac"}}


def main(lang="ru"):
    S.setup()
    t = T[lang]
    hx = pd.read_parquet(INTERIM / "hex8_measures.parquet").join(
        pd.read_parquet(INTERIM / "gvi_hex8.parquet").set_index("hex8"), how="inner")
    hx = hx[hx.gvi_cells >= 10]
    fig = plt.figure(figsize=(5.4, 6.75))
    axes = [fig.add_axes([0.13, 0.50, 0.80, 0.30]), fig.add_axes([0.13, 0.13, 0.80, 0.30])]
    for ax, col, lab, scale in ((axes[0], "ndvi", t["x1"], 1), (axes[1], "canopy", t["x2"], 100)):
        rest = hx[~hx.unit.isin(HL)]
        ax.scatter(rest[col] * scale, rest.gvi, s=14, color=S.DEEMPH, edgecolor=S.SURFACE, linewidth=0.8, zorder=2)
        for u, c in HL.items():
            sub = hx[hx.unit == u]
            ax.scatter(sub[col] * scale, sub.gvi, s=26, color=c, edgecolor=S.SURFACE, linewidth=1.2, zorder=3)
        ax.set_xlabel(lab, fontsize=8, color=S.INK2)
        ax.set_ylabel(t["y"], fontsize=8, color=S.INK2)
        ax.grid(color=S.GRID, lw=0.6)
        ax.tick_params(labelsize=7.5)
    handles = [Line2D([], [], marker="o", lw=0, color=c, markersize=6, label=NAMES_RU[u] if lang == "ru" else u)
               for u, c in HL.items()] + [Line2D([], [], marker="o", lw=0, color=S.DEEMPH, markersize=5, label=t["other"])]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.05, 0.875), ncol=4, fontsize=7.2, frameon=False,
               handletextpad=0.3, columnspacing=1.0)
    fig.text(0.06, 0.965, t["title"], fontsize=13, fontweight="semibold", va="top")
    fig.text(0.06, 0.925, t["sub"], fontsize=8, color=S.INK2, va="top")
    fig.text(0.06, 0.03, t["src"], fontsize=6.2, color=S.MUTED)
    out = FIGURES / f"p2_hex_scatter_{lang}.png"
    fig.savefig(out)
    print(out, len(hx), "hexes")


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["ru"]))
