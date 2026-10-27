# Methodology

Two small studies of Belgrade's urban greenery, built only from open data. Every number quoted in
the README, the posts and the figures is produced by the scripts in `scripts/` and collected in
`docs/RESULTS.md`; nothing is typed in by hand.

## Study areas

* **Part 1, connectivity.** The 10 urban municipalities (*gradske opštine*) of the City of Belgrade:
  Čukarica, Novi Beograd, Palilula, Rakovica, Savski venac, Stari grad, Voždovac, Vračar, Zemun,
  Zvezdara (OpenStreetMap admin_level 8, about 1,030 km², including their rural parts). Movement is
  modelled inside this area plus a 2 km buffer, so that paths can leave the boundary and come back.
  A second set of runs uses only the settlement *Beograd*, i.e. the city proper (389 km²); the posts
  report this one, because it is the scale of the city's own green system.
* **Part 2, five measures.** The part of the settlement *Beograd* inside each of the 10
  municipalities (OSM admin_level 9, codes of the Republic Statistical Office). These ten units
  are the city proper (389 km²) and have official Census 2022 populations (1,197,714 residents in
  total; table "Ukupan broj stanovnika, po naseljima", popis2022.stat.gov.rs).

All rasters share one 10 m grid in UTM 34N (EPSG:32634) whose edges are aligned with Sentinel-2.

## Part 1. The tree network as a graph

**Habitat.** Tree cover (class 10) of ESA WorldCover 2021 v200, 10 m. Patches are 8-connected
components of at least 1 ha (0.5 ha in a sensitivity run). Patches are clipped to the study area;
a variant (`*_touching`) keeps whole patches that touch it, up to the 2 km buffer. Clipping matters:
a forest cut by the boundary can look like a bridge only because its other half is outside. A
patch is reported as a bridge only if it passes the build-over test in both variants.

**Resistance.** A generalist woodland species: cost multipliers per 10 m step, expert-based.

| Land cover (WorldCover) | main | permeable | strict |
|---|---:|---:|---:|
| Tree cover | 1 | 1 | 1 |
| Shrubland | 2 | 1.5 | 3 |
| Grassland, herbaceous wetland | 4 | 2 | 8 |
| Cropland, bare | 15 | 8 | 30 |
| Water | 50 | 25 | 100 |
| Built-up | 60 | 30 | 120 |

OSM roads and railways are burnt in on top (bridges and tunnels excluded): motorway 1000 (30 m
wide), trunk 500 (25 m), primary 300 (20 m), secondary 150 (15 m), tertiary 100 (12 m), links
80-300 (10 m), railway 100 (10 m). The permeable and strict runs halve and double these. A further
run makes water a near barrier (500).

**Graph.** One multi-source least-cost run (scikit-image MCP, 8 neighbours) from all patches splits
the landscape into cost zones; two patches are linked when their zones touch and the link cost is
the cheapest path across that border. This is the planar graph used by Graphab
(Foltête et al. 2012). Link costs are in "metres through forest".

**Connectivity.** Probability of Connectivity (Saura & Pascual-Hortal 2007) with
`p_ij = exp(-k d_ij)`, `k = ln 2 / d50`, where `d50` is the median dispersal distance through
forest (100 m to 30 km; 1 km is the reference). The best path between two patches is the
maximum-product path, i.e. the least-cost path in the graph. EC, the equivalent connected area
(Saura et al. 2011), is `sqrt(sum_i sum_j a_i a_j p*_ij)` in hectares: the area of a single
compact patch that would offer the same amount of reachable habitat.

**Importance of a patch.** dPC is the percentage drop of `sum a_i a_j p*_ij` when the patch is
removed, split into intra (its own area), flux (flows that start or end in it) and connector (its
role as a stepping stone between others; Saura & Rubio 2010). Removal in the graph keeps the old
links, so it can overstate a connector. The strongest candidates are therefore re-tested with a
**build-over scenario**: the patch becomes built-up land on the raster and the whole graph is
rebuilt, so neighbours can re-link around the gap. Reported "EC loss" figures come from these
rebuilt networks.

**Importance of a link.** dLink is the percentage drop of the same sum when one link is removed
from the graph (the patches stay); it is computed for every link used by at least one best path.

**Pinch points.** Circuit theory (McRae et al. 2008), as in Linkage Mapper's Pinchpoint Mapper
(McRae 2012). For each of the most important links (25 in the 10 municipalities, 10 in the city
proper), 1 A is injected into one patch and the
other is grounded, inside a corridor of cells whose two cost distances add up to less than the
least-cost distance + 2 km. The current through a cell is the share of the whole flow that passes
there; values near 1 mean the corridor is squeezed into a single 10 m cell.

**Landscape metrics.** Classic class-level metrics with FRAGSTATS names (McGarigal & Marks):
PLAND, NP, PD, AREA_MN, AREA_MD, LPI, ED, ENN (edge-to-edge, Euclidean) and the effective mesh size
MESH (Jaeger 2000). MESH is what EC becomes when patches are not connected at all, scaled by the
landscape area.

## Part 2. Five ways to measure greenery

| Measure | Source | Definition per unit |
|---|---|---|
| NDVI | Sentinel-2 L2A (Earth Search, collection 1), 18 scenes June-August 2025 | per-pixel median of clear observations (SCL classes 4-6), mean over land |
| Tree cover | ESA WorldCover 2021 v200, 10 m | share of land classified as tree cover |
| Canopy | Meta & WRI High Resolution Canopy Height (Tolan et al. 2024), ~1 m | share of land with predicted height >= 3 m (2 m and 5 m reported too) |
| Green View Index | Mapillary street-level images, May-September 2019-2026, segmented with Mask2Former (Swin-L, Mapillary Vistas) | share of image pixels labelled Vegetation, as in Global Streetscapes (Hou et al. 2024); mean over 100 m sampling cells |
| Green per resident | OSM public green (parks, gardens, nature reserves, forests and woods, recreation grounds; private access excluded; water surfaces removed with WorldCover) / Census 2022 | m² per resident |

"Land" excludes WorldCover permanent water, so rivers do not pull the averages down.

**Street-level sampling.** Image positions come from Mapillary's vector tiles (zoom 14). Kept:
perspective images (no panoramas, no fisheye) taken in May-September from 2019 on, inside the ten
units. On a 100 m grid each cell keeps its newest image, so busy streets with long dashcam
sequences do not dominate. 1024 px thumbnails are segmented with Mask2Former
(Swin-L) trained on Mapillary Vistas; GVI is the share of pixels labelled Vegetation. The pipeline
was checked on 300 summer images from Global Streetscapes that come from Mapillary: our GVI against the
published one has Pearson r = 0.999 and a mean absolute difference of 0.005.

**Access measures.** Residents on a 100 m grid come from GHS-POP R2023A (epoch 2020) rescaled to
Census 2022 totals per unit. On a 50 m grid:

* share of residents within 300 m (straight line) of a public green area of at least 1 ha
  (WHO Europe 2017 rule of thumb; the "300" in 3-30-300);
* m² of public green within 300 m per resident, with every green cell shared among all residents
  within 300 m of it (two-step floating catchment area), compared with the Belgrade green-system
  plan (2019) minimums of 7, 10 and 23 m² per resident within 300 m;
* share of residents whose 300 m neighbourhood has at least 30% canopy (the "30" in 3-30-300).

## Known limitations

* WorldCover is from 2021, the Meta canopy imagery from 2018-2019 (parts of Novi Beograd,
  Rakovica, Savski venac and Čukarica come from February 2019 leaf-off images; inside WorldCover tree
  pixels Meta detects canopy on 48% of the area in February images vs 59% in July images).
  NDVI is summer 2025. Street images span several years.
* Resistance values are assumptions; the conclusions reported are the ones that hold across the
  sensitivity runs.
* OSM public green is a proxy for the official register of public green spaces.
* GHS-POP gives the shape of the population surface inside units; the totals are the census.
