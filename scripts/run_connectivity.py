"""Main connectivity run plus sensitivity variants."""
import sys

from bgreen.connectivity.pipeline import run

RUNS = {
    "main": dict(scenario="main", nodes="aoi"),
    "nodes_touching": dict(scenario="main", nodes="touching_aoi"),
    "permeable": dict(scenario="permeable", nodes="aoi"),
    "strict": dict(scenario="strict", nodes="aoi"),
    "water_barrier": dict(scenario="water_barrier", nodes="aoi"),
    "min05ha": dict(scenario="main", nodes="aoi", min_area_ha=0.5),
    "city": dict(scenario="main", nodes="aoi", aoi_kind="settlement"),
    "city_min05ha": dict(scenario="main", nodes="aoi", aoi_kind="settlement", min_area_ha=0.5),
    "city_permeable": dict(scenario="permeable", nodes="aoi", aoi_kind="settlement"),
    "city_strict": dict(scenario="strict", nodes="aoi", aoi_kind="settlement"),
    "city_touching": dict(scenario="main", nodes="touching_aoi", aoi_kind="settlement"),
}

if __name__ == "__main__":
    names = sys.argv[1:] or list(RUNS)
    for name in names:
        p = run(name, **RUNS[name])
        print(name, "->", p, flush=True)
