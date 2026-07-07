# GeoAI Reliability Audit — Abuja, Nigeria

**An instance-level empirical reliability audit of AI-generated building footprints in a data-scarce urban environment.**

This repository accompanies the technical report *"Quantifying the Reliability Gap: A Spatial Accuracy Assessment of AI-Generated Building Footprints in a Data-Scarce Urban Environment (Abuja, Nigeria)"* (G. G. Mungan, 2026) — prepared as a technical work sample for an AI safety fellowship application. Full report: [`report/Abuja_GeoAI_Reliability_Report.pdf`](report/Abuja_GeoAI_Reliability_Report.pdf).

## The question

AI systems increasingly generate building-footprint data where OpenStreetMap coverage is incomplete, and that data feeds digital twins, disaster-risk mapping, and infrastructure planning. **How reliable is each individual AI-generated geometry — not just the aggregate volume?**

## Key findings (4.28 km² defined study area, Abuja)

| Metric | Value |
|---|---|
| OSM reference buildings | 94 |
| AI-generated buildings (Mapflow.ai) | 684 (**7.3×** the OSM count) |
| Recall vs OSM baseline (IoU ≥ 0.1) | **56.4%** — 41 known buildings undetected |
| Recall at strict COCO-style IoU ≥ 0.5 | **25.5%** |
| Mean IoU among confirmed matches | 0.458 (median 0.425) |
| Mean centroid offset | **6.03 m** (max 14.0 m) |
| AI-only detections (unverified) | 91.8% of AI output |

**Core safety-relevant finding:** a system that generates 7.3× more building polygons than the existing baseline *simultaneously* fails to detect over 40% of independently known buildings. Aggregate coverage and per-instance reliability are distinct properties — evidence of one is not evidence of the other. A ground-truthed failure case (stacked concrete pipes labeled as buildings, confirmed via street-level imagery) further shows that overhead-imagery-only verification is itself insufficient for oversight design.

## Repository structure

```
analysis/matching_analysis.py   # full pipeline: load → clip → greedy IoU matching → metrics → sensitivity → figures
data/                           # study-area boundary + OSM reference layer (see licensing below)
results/                        # metrics_summary.txt, matched_pairs.csv, sensitivity.csv
figures/                        # recall_bar.png, iou_histogram.png, sensitivity_curve.png
report/                         # full technical report (PDF)
```

## Reproduce

```bash
pip install geopandas shapely numpy matplotlib
cd analysis
python matching_analysis.py
```

The script prints all headline metrics and regenerates `results/` and `figures/` from the shapefiles in `data/`.

### Methodology in one paragraph

Every OSM building polygon is matched against AI-generated polygons using a **greedy one-to-one assignment by descending IoU** (each polygon can appear in at most one pair — preventing a single large AI polygon from "matching" several distinct OSM buildings, which would inflate recall). A confirmed match requires **IoU ≥ 0.1**, a deliberately permissive threshold chosen because footprints in this dataset are frequently offset or rotated without being wrong about a building's existence; a full sensitivity analysis across thresholds 0.0–0.5 is reported so conclusions can be evaluated against that choice. All geometries are analyzed in EPSG:32632 (UTM 32N) for metric-accurate areas and distances.

## Data & licensing

- **OSM reference layer** (`data/Into_Study_Area_OSM.*`): © OpenStreetMap contributors, extracted via QuickOSM/Overpass API (`building=*`), redistributed under the [Open Database License (ODbL)](https://www.openstreetmap.org/copyright).
- **Study-area boundary** (`data/Study_Area.*`): author's own work.
- **AI-generated layer**: produced with [Mapflow.ai](https://mapflow.ai) ("Buildings" model, Mapbox Satellite imagery, processing date 29 Apr 2026). Raw AI polygons are **not redistributed** here pending clarity on the provider's redistribution terms; **derived per-pair metrics** (`results/matched_pairs.csv`: IoU and centroid offset per matched pair) are included, and the layer is reproducible via Mapflow with the documented parameters.

## Limitations (summary — see report §7 for full discussion)

Single city; OSM is a baseline, not ground truth (recall figures are *relative to what OSM has mapped*); the false-positive rate of AI-only detections is spot-checked, not systematically measured; temporal mismatch between imagery dates may account for part of the detection gap.

## Honest note on AI assistance

The analysis pipeline in this repository was developed with AI-assisted coding. The research question, methodology, data collection, validation (including street-level ground-truthing), and interpretation are the author's own. Strengthening independent coding and ML foundations is an explicit, ongoing goal.

## Author

**Gamze Gül Mungan** — Geospatial Data Specialist · AI Reliability Researcher
[gamzegulmungan.com](https://www.gamzegulmungan.com) · [LinkedIn](https://www.linkedin.com/in/gamze-mungan/) · [YouTube](https://www.youtube.com/@GamzegulMungan)

## License

Code: MIT (see `LICENSE`). Data: per-source licenses above. Report PDF: © the author, shared for evaluation purposes.
