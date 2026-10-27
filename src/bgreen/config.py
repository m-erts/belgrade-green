"""Paths and shared constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
CACHE = ROOT / "data" / "cache"
FIGURES = ROOT / "reports" / "figures"
TABLES = ROOT / "reports" / "tables"

for _p in (RAW, INTERIM, CACHE, FIGURES, TABLES):
    _p.mkdir(parents=True, exist_ok=True)

# Metric CRS for Serbia: UTM zone 34N (Belgrade sits at ~20.46 E).
CRS_M = "EPSG:32634"
CRS_LL = "EPSG:4326"

# OSM relation of the City of Belgrade (admin_level 6) and its 10 urban municipalities.
CITY_REL = 1677007
URBAN_MUNICIPALITIES = {
    "Čukarica": 7727516,
    "Novi Beograd": 3085749,
    "Palilula": 7737269,
    "Rakovica": 7728561,
    "Savski venac": 5892891,
    "Stari grad": 2027114,
    "Voždovac": 7737268,
    "Vračar": 5731335,
    "Zemun": 3085750,
    "Zvezdara": 6930224,
}

USER_AGENT = "belgrade-green/0.1 (open-data research; github.com/m-erts)"
