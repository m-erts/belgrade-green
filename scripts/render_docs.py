"""Render README.md from templates/README.md.j2 and reports/tables/key_numbers.json."""
import json

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from bgreen.config import ROOT, TABLES

COLS = [("ndvi_mean", "NDVI (summer 2025)", "{:.2f}"), ("tree_cover_wc_pct", "Tree cover, WorldCover", "{:.0f}%"),
        ("canopy3_meta_pct", "Canopy ≥ 3 m, Meta", "{:.0f}%"), ("gvi_mean", "Green View Index", "{:.2f}"),
        ("green_m2_per_person", "Public green, m²/resident", "{:.0f}"),
        ("within300_1ha_pct", "Residents ≤ 300 m from ≥ 1 ha park", "{:.0f}%")]


def part2():
    um = pd.read_csv(TABLES / "units_measures.csv").set_index("unit")
    cols = [c for c in COLS if c[0] in um]
    ranks = um[[c for c, _, _ in cols]].rank(ascending=False, method="min").astype(int)
    head = "| District | Residents | " + " | ".join(n for _, n, _ in cols) + " |"
    sep = "|---|---:|" + "---:|" * len(cols)
    rows = []
    for u in um.sort_values("pop_2022", ascending=False).index:
        cells = [f"{f.format(um.loc[u, c])} ({ranks.loc[u, c]})" for c, _, f in cols]
        rows.append(f"| {u} | {um.loc[u, 'pop_2022']:,} | " + " | ".join(cells) + " |")
    intro = ("The ten units are the parts of the settlement Beograd inside each urban municipality "
             "(Census 2022 population). Rank in brackets, 1 = greenest.\n\n"
             "![Ranks](reports/figures/p2_ranks_en.png)\n\n")
    return intro + "\n".join([head, sep] + rows) + "\n\n![Norms](reports/figures/p2_norms_en.png)"


def main():
    K = json.loads((TABLES / "key_numbers.json").read_text())
    c = K["connectivity"]
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), keep_trailing_newline=True)
    env.filters["int_fmt"] = lambda x: f"{float(x):,.0f}"
    env.filters["pct"] = lambda x: f"{100 * float(x):.0f}%"
    env.filters["pct1"] = lambda x: f"{float(x):.0f}%"
    env.filters["pct1raw"] = lambda x: f"{float(x):.0f}%"
    env.filters["pct_frac"] = lambda x: f"{100 * float(x):.0f}%"
    env.filters["x1"] = lambda x: f"{float(x):.1f}×"
    by_patch = lambda key: {r["patch"]: type("R", (), r) for r in c.get(key, [])}
    ctx = {"c": type("C", (), {k: (type("B", (), v) if isinstance(v, dict) else v) for k, v in c.items()}),
           "bo_city": by_patch("city_buildover"), "bo_city_t": by_patch("city_touching_buildover"),
           "city_links": [type("L", (), r) for r in c.get("city_top_links", [])],
           "pinch_city": {f"{r['i']}_{r['j']}": type("P", (), r) for r in c.get("city_pinchpoints", [])},
           "part2": part2()}
    out = env.get_template("README.md.j2").render(**ctx)
    (ROOT / "README.md").write_text(out)
    print("README.md rendered,", len(out), "chars")


if __name__ == "__main__":
    main()
