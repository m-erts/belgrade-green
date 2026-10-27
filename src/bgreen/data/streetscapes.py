"""Global Streetscapes (NUS Urban Analytics Lab, CC BY-SA 4.0): street-level images with a
precomputed Green View Index. Only the Belgrade rows are pulled, straight from Hugging Face."""
from __future__ import annotations

import duckdb

from bgreen.config import RAW

BASE = "https://huggingface.co/datasets/NUS-UAL/global-streetscapes/resolve/main/data/parquet/"
OUT = RAW / "streetscapes_belgrade.parquet"


def fetch(cities=("Belgrade", "Zemun"), country="Serbia", out=OUT):
    if out.exists():
        return out
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    names = ", ".join(f"'{c}'" for c in cities)
    con.execute(f"""
        CREATE TEMP TABLE ids AS
        SELECT uuid, city_ascii AS city FROM read_parquet('{BASE}simplemaps.parquet')
        WHERE country = '{country}' AND city_ascii IN ({names});
    """)
    con.execute(f"""
        COPY (
          SELECT i.uuid, i.city, m.source, m.orig_id, m.lat, m.lon, m.datetime_local, m.year, m.month,
                 m.hour, m.heading, m.projection_type, m.sequence_id,
                 s.green_view_index, s.sky_view_index, s.Vegetation, s.Terrain,
                 c.glare, c.lighting_condition, c.pano_status, c.platform, c.quality,
                 c.reflection, c.view_direction, c.weather, se.season
          FROM ids i
          JOIN read_parquet('{BASE}metadata_common_attributes.parquet') m USING (uuid)
          LEFT JOIN read_parquet('{BASE}segmentation.parquet') s USING (uuid)
          LEFT JOIN read_parquet('{BASE}contextual.parquet') c USING (uuid)
          LEFT JOIN read_parquet('{BASE}season.parquet') se USING (uuid)
        ) TO '{out}' (FORMAT parquet);
    """)
    return out
