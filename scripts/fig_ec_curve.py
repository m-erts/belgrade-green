"""Figure: EC as a share of habitat area across dispersal distances, two study areas with
the range across resistance scenarios."""
import sys

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FixedLocator, FuncFormatter

from bgreen.config import FIGURES, TABLES
from bgreen.viz import style as S

NBSP = " "
T = {
    "ru": {"title": "Сколько каркаса работает как единое целое",
           "sub": "Эквивалентная связная площадь (EC) в % от площади всех лесных патчей ≥ 1 га.\nПолоса — разброс по сценариям сопротивления",
           "x": "медианная дистанция расселения вида (по лесу)",
           "s_main": "10 городских общин", "s_city": "город (насеље «Београд»)",
           "none": "если бы связей не было", "km": "км", "m": "м",
           "src": "Данные: ESA WorldCover 2021, OpenStreetMap. Метод: PC/EC (Saura et al.). Расчёт: Мария Эрцеговац"},
    "en": {"title": "How much of the network works as one",
           "sub": "Equivalent connected area (EC) as % of all tree patches ≥ 1 ha.\nBand: range across resistance scenarios",
           "x": "median dispersal distance of a species (through forest)",
           "s_main": "10 urban municipalities", "s_city": "city proper (settlement Beograd)",
           "none": "if patches were not connected", "km": "km", "m": "m",
           "src": "Data: ESA WorldCover 2021, OpenStreetMap. Method: PC/EC (Saura et al.). Analysis: Marija Ercegovac"},
}
SERIES = [("main", "permeable", "strict", "s_main", 0), ("city", "city_permeable", "city_strict", "s_city", 1)]


def main(lang="ru"):
    S.setup()
    t = T[lang]
    df = pd.read_csv(TABLES / "ec_curve.csv")
    fig = plt.figure(figsize=(5.4, 6.75))
    ax = fig.add_axes([0.13, 0.15, 0.80, 0.62])
    for run, hi, lo, key, k in SERIES:
        m = df[df.run == run].sort_values("d50")
        a, b = df[df.run == lo].sort_values("d50"), df[df.run == hi].sort_values("d50")
        c = S.CAT[k]
        ax.fill_between(m.d50, 100 * a.ec_share.values, 100 * b.ec_share.values, color=c, alpha=0.12, linewidth=0)
        ax.plot(m.d50, 100 * m.ec_share, color=c, lw=2)
        p = m[m.d50 == 1000].iloc[0]
        ax.plot([1000], [100 * p.ec_share], "o", ms=7, color=c, mec=S.SURFACE, mew=2, zorder=5)
        lab = f"{t[key]}: {100 * p.ec_share:.0f}%"
        if k == 0:
            ax.annotate(lab, (1000, 100 * p.ec_share), xytext=(850, 100 * p.ec_share + 6.5), fontsize=8.5,
                        color=S.INK, fontweight="medium", va="center", ha="right")
        else:
            ax.annotate(lab, (1000, 100 * p.ec_share), xytext=(1200, 100 * p.ec_share - 6.5), fontsize=8.5,
                        color=S.INK, fontweight="medium", va="center", ha="left")
        end = m.iloc[-1]
        ax.plot([end.d50], [100 * end.ec_share], "o", ms=5, color=c, mec=S.SURFACE, mew=1.5, zorder=5)
        e0 = 100 * m.ec0_share.iloc[0]
        ax.plot([m.d50.min(), m.d50.max()], [e0, e0], color=c, lw=0.8, alpha=0.5)
    ax.text(df.d50.min() * 1.05, 100 * df[df.run == "city"].ec0_share.iloc[0] - 1.5, t["none"], fontsize=7.3,
            color=S.INK2, va="top")
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator([100, 300, 1000, 3000, 10000, 30000]))
    ax.xaxis.set_minor_locator(FixedLocator([]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x / 1000:g} {t['km']}" if x >= 1000 else f"{x:g} {t['m']}"))
    ax.set_xlim(df.d50.min(), df.d50.max())
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_locator(FixedLocator([0, 25, 50, 75, 100]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.grid(axis="y", color=S.GRID, lw=0.6)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel(t["x"], fontsize=8.5, color=S.INK2, labelpad=8)
    ax.tick_params(labelsize=8)
    fig.text(0.06, 0.95, t["title"], fontsize=13, fontweight="semibold", va="top")
    fig.text(0.06, 0.905, t["sub"], fontsize=8.3, color=S.INK2, va="top", linespacing=1.4)
    fig.text(0.06, 0.035, t["src"], fontsize=6.3, color=S.MUTED)
    out = FIGURES / f"p1_ec_curve_{lang}.png"
    fig.savefig(out)
    print(out)


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["ru"]))
