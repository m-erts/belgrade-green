"""Download every input into data/raw (idempotent: existing files are kept).

OpenStreetMap through Overpass (mirrors in bgreen.data.overpass), boundaries through Nominatim,
ESA WorldCover and Meta/WRI canopy height from AWS, Sentinel-2 from Earth Search, GHS-POP from the
JRC FTP, Global Streetscapes from Hugging Face."""
import zipfile

import requests
from rasterio.warp import transform_bounds

from bgreen.config import CITY_REL, RAW, URBAN_MUNICIPALITIES
from bgreen.data import canopy, osm, overpass, sentinel2, streetscapes, worldcover
from bgreen.grid import CITY, URBAN

CHM = "https://dataforgood-fb-data.s3.amazonaws.com/forests/v1/alsgedi_global_v6_float/"
CHM_TILES = ["120233100", "120233101"]
GHS = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/"
       "GHS_POP_E2020_GLOBE_R2023A_54009_100/V1-0/tiles/GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0_R4_C20.zip")


def _bbox(grid):
    w, s, e, n = transform_bounds(grid.crs, "EPSG:4326", *grid.bounds, densify_pts=21)
    return f"{s:.5f},{w:.5f},{n:.5f},{e:.5f}"


def boundaries():
    if not (RAW / "city_belgrade.gpkg").exists():
        osm.by_osmid([CITY_REL]).to_file(RAW / "city_belgrade.gpkg", driver="GPKG")
    if not (RAW / "urban_municipalities.gpkg").exists():
        g = osm.by_osmid(list(URBAN_MUNICIPALITIES.values()))
        g["municipality"] = list(URBAN_MUNICIPALITIES.keys())
        g[["osm_id", "municipality", "geometry"]].to_file(RAW / "urban_municipalities.gpkg", driver="GPKG")
    if not (RAW / "osm_admin_9_10.gpkg").exists():
        d = overpass.query(f"""[out:json][timeout:300];rel({CITY_REL});map_to_area->.c;
rel(area.c)["boundary"="administrative"]["admin_level"~"9|10"];out geom;""", timeout=320)
        g = overpass.to_gdf(d, polygons_only=True)
        cols = [c for c in ["osm_id", "admin_level", "name", "name:sr-Latn", "population", "ref:RS:naselje",
                            "ref:RS:mesna_zajednica"] if c in g.columns]
        g[cols + ["geometry"]].to_file(RAW / "osm_admin_9_10.gpkg", driver="GPKG")


def osm_layers():
    bb = _bbox(URBAN)
    if not (RAW / "osm_barriers.gpkg").exists():
        d = overpass.query(f"""[out:json][timeout:500];(
way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link)$"]({bb});
way["railway"~"^(rail|light_rail|tram)$"]({bb}););out geom;""", timeout=520)
        g = overpass.to_gdf(d)
        g = g[g.geom_type == "LineString"]
        cols = [c for c in ["osm_id", "highway", "railway", "bridge", "tunnel", "layer", "lanes", "name"] if c in g]
        g[cols + ["geometry"]].to_file(RAW / "osm_barriers.gpkg", driver="GPKG")
    if not (RAW / "osm_green.gpkg").exists():
        d = overpass.query(f"""[out:json][timeout:500];(
way["leisure"~"^(park|garden|nature_reserve|recreation_ground|dog_park|playground)$"]({bb});
relation["leisure"~"^(park|garden|nature_reserve|recreation_ground)$"]({bb});
way["landuse"~"^(forest|recreation_ground|cemetery|village_green|grass|meadow|allotments|orchard)$"]({bb});
relation["landuse"~"^(forest|recreation_ground|cemetery|village_green|grass|meadow|allotments|orchard)$"]({bb});
way["natural"~"^(wood|scrub|grassland|wetland|heath)$"]({bb});
relation["natural"~"^(wood|scrub|grassland|wetland|heath)$"]({bb});
way["boundary"="protected_area"]({bb});relation["boundary"="protected_area"]({bb}););out geom;""", timeout=520)
        g = overpass.to_gdf(d, polygons_only=True)
        cols = [c for c in ["osm_type", "osm_id", "name", "name:sr-Latn", "name:en", "leisure", "landuse", "natural",
                            "boundary", "protect_class", "protection_title", "access", "garden:type", "operator"] if c in g]
        g[cols + ["geometry"]].to_file(RAW / "osm_green.gpkg", driver="GPKG")
    if not (RAW / "osm_places.gpkg").exists():
        d = overpass.query(f"""[out:json][timeout:200];(node["place"~"^(suburb|neighbourhood|quarter|village|hamlet|locality|island|islet)$"]({bb}););out;""",
                           timeout=220)
        g = overpass.to_gdf(d)
        g[[c for c in ["osm_id", "name", "name:sr-Latn", "place", "geometry"] if c in g]].to_file(
            RAW / "osm_places.gpkg", driver="GPKG")


def rasters():
    worldcover.fetch(CITY)
    (RAW / "meta_chm").mkdir(exist_ok=True)
    for q in CHM_TILES:
        p = RAW / "meta_chm" / f"{q}.tif"
        if not p.exists():
            with requests.get(f"{CHM}chm/{q}.tif", stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(p, "wb") as f:
                    for chunk in r.iter_content(1 << 22):
                        f.write(chunk)
        m = RAW / "meta_chm" / f"meta_{q}.geojson"
        if not m.exists():
            m.write_bytes(requests.get(f"{CHM}metadata/{q}.geojson", timeout=120).content)
    canopy.canopy_cover(URBAN)
    sentinel2.summer_ndvi(URBAN, bbox_ll=(20.20, 44.58, 20.68, 45.10))
    ghs = RAW / "ghs_pop" / "GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0_R4_C20.tif"
    if not ghs.exists():
        ghs.parent.mkdir(exist_ok=True)
        z = ghs.parent / "ghs.zip"
        z.write_bytes(requests.get(GHS, timeout=600).content)
        zipfile.ZipFile(z).extractall(ghs.parent)
        z.unlink()


if __name__ == "__main__":
    boundaries()
    osm_layers()
    rasters()
    streetscapes.fetch()
    print("inputs ready in", RAW)
