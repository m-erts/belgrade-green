# Data sources

Everything is downloaded by `scripts/fetch_data.py` (and `scripts/run_gvi.py` for street-level
images) into `data/raw/`, which is not committed. Dates are the download dates of this version.

| Dataset | Version / date | Used for | Licence | Source |
|---|---|---|---|---|
| ESA WorldCover 10 m (Zanaga et al. 2022) | 2021 v200, tiles N42E018, N45E018 | tree patches, resistance surface, tree cover share | CC BY 4.0 | `s3://esa-worldcover` via https://esa-worldcover.s3.eu-central-1.amazonaws.com |
| OpenStreetMap | extracts of 2026-10-01 (Overpass API) | roads and railways, public green, places, boundaries of municipalities and of the settlement *Beograd* | ODbL 1.0, © OpenStreetMap contributors | overpass-api.de, maps.mail.ru Overpass mirror, Nominatim |
| Meta & WRI High Resolution Canopy Height (Tolan et al. 2024) | v1, tiles 120233100, 120233101; imagery 2018-2019 | canopy cover (>= 3 m) | CC BY 4.0 | `s3://dataforgood-fb-data/forests/v1/alsgedi_global_v6_float/` |
| Copernicus Sentinel-2 L2A | 18 scenes of tile 34TDQ, June-August 2025 | summer NDVI | Copernicus open data licence | Earth Search (Element 84), collection `sentinel-2-c1-l2a` |
| GHS-POP R2023A (Schiavina et al. 2023) | epoch 2020, 100 m, tile R4_C20 | shape of the population surface inside units | CC BY 4.0 | JRC GHSL FTP |
| Census 2022, Republic Statistical Office of Serbia | table "Ukupan broj stanovnika, po naseljima" | population of the 10 urban units | open statistical data | popis2022.stat.gov.rs |
| Global Streetscapes (Hou et al. 2024) | Hugging Face `NUS-UAL/global-streetscapes`, parquet | published Green View Index for Belgrade images, validation | CC BY-SA 4.0 | huggingface.co/datasets/NUS-UAL/global-streetscapes |
| Mapillary street-level images | summer captures, 1024 px thumbnails via API v4 | Green View Index for all units | images CC BY-SA 4.0; not redistributed here | mapillary.com (needs a client token) |
| Mask2Former Swin-L, Mapillary Vistas | `facebook/mask2former-swin-large-mapillary-vistas-semantic` | vegetation share per image | see the model card | huggingface.co |

Policy and norm documents used in the texts are listed with links and quotes in `docs/research/`.
