"""OpenStreetMap access through osmnx with an on-disk cache."""
from __future__ import annotations

import osmnx as ox

from bgreen.config import CACHE, USER_AGENT

ox.settings.use_cache = True
ox.settings.cache_folder = str(CACHE / "osmnx")
ox.settings.http_user_agent = USER_AGENT
ox.settings.requests_timeout = 600
ox.settings.overpass_settings = "[out:json][timeout:{timeout}]{maxsize}"
ox.settings.log_console = False


def admin_units(polygon, levels=("8", "9", "10")):
    """Administrative relations inside a polygon, as (multi)polygons with their tags."""
    gdf = ox.features_from_polygon(
        polygon, tags={"boundary": "administrative", "admin_level": list(levels)}
    )
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    return gdf.reset_index()


def by_osmid(ids):
    """Boundary polygons of OSM relations by id (via Nominatim)."""
    return ox.geocode_to_gdf([f"R{i}" for i in ids], by_osmid=True)
