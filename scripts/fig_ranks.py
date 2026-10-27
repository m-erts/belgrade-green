"""Figure: ranks of the 10 urban units under each greenery measure (bump chart with emphasis)."""
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bgreen.config import FIGURES, TABLES
from bgreen.viz import style as S

UNIT_RU = {"Čukarica": "Чукарица", "Novi Beograd": "Новый Белград", "Palilula": "Палилула",
           "Rakovica": "Раковица", "Savski venac": "Савски-Венац", "Stari grad": "Стари-Град",
           "Voždovac": "Вождовац", "Vračar": "Врачар", "Zemun": "Земун", "Zvezdara": "Звездара"}
MEASURES = [
    ("ndvi_mean", {"ru": "NDVI\nспутник", "en": "NDVI\nsatellite"}),
    ("tree_cover_wc_pct", {"ru": "Деревья\n10 м", "en": "Trees\n10 m"}),
    ("canopy3_meta_pct", {"ru": "Кроны\n1 м", "en": "Canopy\n1 m"}),
    ("gvi_mean", {"ru": "GVI\nс улицы", "en": "GVI\nstreet"}),
    ("green_m2_per_person", {"ru": "м² на\nжителя", "en": "m² per\nresident"}),
    ("within300_1ha_pct", {"ru": "Парк\nв 300 м", "en": "Park\n≤ 300 m"}),
]
T = {"ru": {"title": "Один город — шесть рейтингов зелени",
            "sub": "Место каждого из 10 районов Белграда по каждой метрике (1 = самый зелёный)",
            "src": "Деревья — ESA WorldCover 2021 (10 м), кроны ≥ 3 м — Meta/WRI (1 м), GVI — Mapillary 2019–2026,\nм² — общественная зелень OSM и перепись 2022, парк — ≥ 1 га. Расчёт: Мария Эрцеговац"},
     "en": {"title": "One city, six greenery rankings",
            "sub": "Rank of each of Belgrade's 10 urban districts under each measure (1 = greenest)",
            "src": "Trees: ESA WorldCover 2021 (10 m); canopy ≥ 3 m: Meta/WRI (1 m); GVI: Mapillary 2019–2026;\nm²: OSM public green and Census 2022; park: ≥ 1 ha. Analysis: Marija Ercegovac"}}


def main(lang="ru", highlight=("Vračar", "Palilula", "Stari grad")):
    S.setup()
    t = T[lang]
    df = pd.read_csv(TABLES / "units_measures.csv").set_index("unit")
    ms = [(c, lab[lang]) for c, lab in MEASURES if c in df]
    R = df[[c for c, _ in ms]].rank(ascending=False, method="min")
    fig = plt.figure(figsize=(5.4, 6.75))
    ax = fig.add_axes([0.22, 0.13, 0.56, 0.66])
    xs = np.arange(len(ms))
    colors = dict(zip(highlight, S.CAT[:3]))
    order = [u for u in R.index if u not in colors] + list(highlight)
    for u in order:
        y = R.loc[u].values
        hl = u in colors
        c = colors.get(u, S.DEEMPH)
        ax.plot(xs, y, color=c, lw=2 if hl else 1.2, zorder=4 if hl else 2, solid_joinstyle="round")
        ax.scatter(xs, y, s=46 if hl else 22, color=c, edgecolor=S.SURFACE, linewidth=1.6, zorder=5 if hl else 3)
        name = UNIT_RU[u] if lang == "ru" else u
        for side, x0, ha, dx in (("l", xs[0], "right", -0.18), ("r", xs[-1], "left", 0.18)):
            ax.text(x0 + dx, y[0 if side == "l" else -1], name, ha=ha, va="center", fontsize=7.8,
                    color=S.INK if hl else S.INK2, fontweight="semibold" if hl else "normal")
    ax.set_ylim(10.6, 0.4)
    ax.set_xlim(-0.25, len(ms) - 0.75)
    ax.set_yticks([])
    ax.set_xticks(xs)
    ax.set_xticklabels([lab for _, lab in ms], fontsize=7.2, color=S.INK2, linespacing=1.3)
    ax.xaxis.tick_top()
    for s in ax.spines.values():
        s.set_visible(False)
    for x in xs:
        ax.axvline(x, color=S.GRID, lw=0.6, zorder=0)
    fig.text(0.06, 0.955, t["title"], fontsize=13, fontweight="semibold", va="top")
    fig.text(0.06, 0.912, t["sub"], fontsize=8.5, color=S.INK2, va="top")
    fig.text(0.06, 0.035, t["src"], fontsize=6.3, color=S.MUTED, linespacing=1.4)
    out = FIGURES / f"p2_ranks_{lang}.png"
    fig.savefig(out)
    print(out)


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["ru"]))
