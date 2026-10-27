PY := PYTHONPATH=src OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python3
VENV := PYTHONPATH=src .venv/bin/python
RUNS := main nodes_touching permeable strict water_barrier min05ha city city_min05ha city_permeable city_strict city_touching

.PHONY: all data connectivity measures gvi figures results test

all: data connectivity measures figures results

data:
	$(PY) scripts/fetch_data.py

connectivity:
	$(PY) scripts/run_connectivity.py $(RUNS)
	$(PY) scripts/run_buildover.py main 20
	$(PY) scripts/run_buildover.py nodes_touching 20
	$(PY) scripts/run_buildover.py city 15
	$(PY) scripts/run_buildover.py city_touching 15
	$(PY) scripts/run_pinchpoints.py main 25
	$(PY) scripts/run_pinchpoints.py city 10
	$(PY) scripts/ec_curve.py

measures:
	$(PY) -c "from bgreen.measures.compute import run; run()"

# needs a Mapillary client token in ~/.mapillary_token and the venv with torch (requirements.txt)
gvi:
	$(PY) scripts/run_gvi.py list
	$(PY) scripts/run_gvi.py fetch
	$(VENV) -m bgreen.measures.segment data/interim/gvi_paths.txt data/interim/gvi_seg.parquet
	$(PY) scripts/gvi_aggregate.py

figures:
	for l in ru en; do \
	  $(PY) scripts/fig_city_network.py $$l; $(PY) scripts/fig_ec_curve.py $$l; \
	  $(PY) scripts/fig_pinch.py $$l; $(PY) scripts/fig_ranks.py $$l; done

results:
	$(PY) scripts/render_results.py

test:
	$(PY) -m pytest -q tests
