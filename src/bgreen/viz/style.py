"""Figure style: Geist (OFL, converted from the woff2 shipped in chargescape-london), the
reference data-viz palette (light surface), thin marks and hairline chrome."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap

from bgreen.config import CACHE

FONT_DIR = CACHE / "fonts"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
WATER = "#dfe7ee"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ACCENT = CAT[1]          # orange: the one thing the figure is about
DEEMPH = "#c9c8c1"       # de-emphasis gray for context marks

# single-hue green ramp for "how much vegetation" (light -> dark)
GREENS = ["#eef5e9", "#d3e7c8", "#b2d6a1", "#8cc178", "#63a752", "#3f8a36", "#246c24", "#124d17"]
SEQ_GREEN = LinearSegmentedColormap.from_list("bg_greens", GREENS)
# ordinal classes (discrete ordered fills): light end clears 2:1 on the surface (validated)
GREENS_ORD = ["#8cc178", "#63a752", "#3f8a36", "#246c24", "#124d17"]
# single-hue warm ramp for current density (pinch points)
HEAT = ["#fdeee6", "#f9cdb7", "#f4a582", "#ec7a4f", "#d9542a", "#b03a17", "#7f2809"]
SEQ_HEAT = LinearSegmentedColormap.from_list("bg_heat", HEAT)


def setup():
    for f in sorted(Path(FONT_DIR).glob("Geist*-*.ttf")):
        if "Variable" not in f.name:
            fm.fontManager.addfont(str(f))
    mpl.rcParams.update({
        "font.family": "Geist",
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK2,
        "axes.edgecolor": BASE,
        "axes.linewidth": 0.6,
        "axes.facecolor": SURFACE,
        "figure.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.grid": False,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "savefig.dpi": 200,
        "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
    })
