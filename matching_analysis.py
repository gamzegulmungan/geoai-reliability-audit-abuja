#!/usr/bin/env python3
"""
GeoAI Building-Footprint Reliability Audit — Abuja, Nigeria
============================================================
Reproduces the quantitative results in:
  "Quantifying the Reliability Gap: A Spatial Accuracy Assessment of
   AI-Generated Building Footprints in a Data-Scarce Urban Environment"
   (G. G. Mungan, 2026)

Pipeline:
  1. Load study-area boundary, OSM reference buildings, AI-generated buildings
  2. Clip both layers to the study area
  3. Greedy one-to-one spatial matching by descending IoU
  4. Metrics: recall, IoU distribution, centroid offset
  5. IoU-threshold sensitivity analysis
  6. Export CSVs and figures

Note on AI assistance: this pipeline was developed with AI-assisted coding;
the methodology, validation, and interpretation are the author's own.

Requirements: geopandas, shapely, numpy, matplotlib
Usage: python matching_analysis.py
"""

import os
import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.strtree import STRtree

os.environ.setdefault("SHAPE_RESTORE_SHX", "YES")

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = BASE   # flat repo layout: shapefiles sit next to this script
OUT = BASE    # results CSVs are written next to this script
FIG = BASE    # figures are written next to this script
os.makedirs(OUT, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

CONFIRM_IOU = 0.10          # working confirmed-match threshold (see report §4.2)
THRESHOLDS = [0.0, 0.1, 0.2, 0.3, 0.5]

# ----------------------------------------------------------------------
# 1–2. Load and clip
# ----------------------------------------------------------------------
study = gpd.read_file(os.path.join(DATA, "Study_Area.shp"))
osm = gpd.read_file(os.path.join(DATA, "Into_Study_Area_OSM.shp"))
ai = gpd.read_file(os.path.join(DATA, "AI_Study_Area.shp"))

# fix invalid geometries defensively
osm["geometry"] = osm.geometry.buffer(0)
ai["geometry"] = ai.geometry.buffer(0)

boundary = study.geometry.iloc[0]
osm_in = osm[osm.geometry.intersects(boundary)].reset_index(drop=True)
ai_in = ai[ai.geometry.intersects(boundary)].reset_index(drop=True)

print(f"Study area: {study.geometry.area.sum()/1e6:.2f} km^2 (CRS {study.crs})")
print(f"OSM buildings in area: {len(osm_in)}")
print(f"AI buildings in area:  {len(ai_in)}  ({len(ai_in)/len(osm_in):.1f}x OSM)")

# ----------------------------------------------------------------------
# 3. Greedy one-to-one matching by descending IoU
#    (prevents one large AI polygon counting as a match for several
#     distinct OSM buildings — see report §4.1)
# ----------------------------------------------------------------------
osm_g = list(osm_in.geometry)
ai_g = list(ai_in.geometry)
tree = STRtree(ai_g)

candidates = []
for i, og in enumerate(osm_g):
    for j in tree.query(og, predicate="intersects"):
        inter = og.intersection(ai_g[j]).area
        if inter <= 0:
            continue
        union = og.union(ai_g[j]).area
        candidates.append((i, int(j), inter / union))

candidates.sort(key=lambda t: -t[2])
used_osm, used_ai, matches = set(), set(), []
for i, j, iou in candidates:
    if i in used_osm or j in used_ai:
        continue
    used_osm.add(i)
    used_ai.add(j)
    matches.append((i, j, iou))

# ----------------------------------------------------------------------
# 4. Metrics at the working threshold
# ----------------------------------------------------------------------
conf = [(i, j, iou) for i, j, iou in matches if iou >= CONFIRM_IOU]
ious = np.array([m[2] for m in conf])
offsets = np.array([osm_g[i].centroid.distance(ai_g[j].centroid) for i, j, _ in conf])
n_osm = len(osm_in)

print(f"\nConfirmed matches (IoU >= {CONFIRM_IOU}): {len(conf)}")
print(f"Recall (vs OSM baseline): {len(conf)/n_osm*100:.1f}%")
print(f"Mean IoU: {ious.mean():.3f}  median: {np.median(ious):.3f}  SD: {ious.std(ddof=1):.3f}")
print(f"Mean centroid offset: {offsets.mean():.2f} m  (max {offsets.max():.2f} m)")
ai_only = len(ai_in) - len(used_ai)
print(f"AI-only detections: {ai_only} ({ai_only/len(ai_in)*100:.1f}% of AI total) — unverified; see report §4.3, §7")

# matched pairs CSV (derived metrics only)
import csv
with open(os.path.join(OUT, "matched_pairs.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["osm_index", "ai_index", "iou", "centroid_offset_m"])
    for (i, j, iou), off in zip(conf, offsets):
        w.writerow([i, j, f"{iou:.4f}", f"{off:.2f}"])

# ----------------------------------------------------------------------
# 5. Sensitivity of recall to the matching threshold (report §5.3)
# ----------------------------------------------------------------------
with open(os.path.join(OUT, "sensitivity.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["iou_threshold", "confirmed_matches", "recall_pct"])
    sens = []
    for t in THRESHOLDS:
        n = sum(1 for _, _, iou in matches if iou >= t)
        sens.append((t, n, n / n_osm * 100))
        w.writerow([t, n, f"{n/n_osm*100:.1f}"])
print("\nSensitivity:", ", ".join(f"IoU>={t}: {r:.1f}%" for t, _, r in sens))

# summary
with open(os.path.join(OUT, "metrics_summary.txt"), "w") as f:
    f.write(f"Study area: {study.geometry.area.sum()/1e6:.2f} km^2\n")
    f.write(f"OSM buildings: {n_osm}\nAI buildings: {len(ai_in)}\n")
    f.write(f"Confirmed matches (IoU>={CONFIRM_IOU}): {len(conf)}\n")
    f.write(f"Recall: {len(conf)/n_osm*100:.1f}%\n")
    f.write(f"Mean IoU: {ious.mean():.3f} (median {np.median(ious):.3f}, SD {ious.std(ddof=1):.3f})\n")
    f.write(f"Mean centroid offset: {offsets.mean():.2f} m\n")
    f.write(f"AI-only detections: {ai_only} ({ai_only/len(ai_in)*100:.1f}%)\n")

# ----------------------------------------------------------------------
# 6. Figures
# ----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 2.2), dpi=150)
ax.barh([0], [len(conf)], color="#2b6cb0", label=f"Confirmed match, IoU\u2265{CONFIRM_IOU} ({len(conf)})")
ax.barh([0], [n_osm - len(conf)], left=[len(conf)], color="#cfcac0",
        label=f"Not detected ({n_osm - len(conf)})")
ax.set_yticks([0]); ax.set_yticklabels([f"OSM buildings\n(n={n_osm})"])
ax.set_xlabel("Number of buildings")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.65), ncol=2, frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "recall_bar.png")); plt.close()

fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
ax.hist(ious, bins=np.arange(0.1, 1.01, 0.1), color="#2b6cb0", edgecolor="white")
ax.axvline(ious.mean(), color="#c53030", ls="--", label=f"Mean = {ious.mean():.3f}")
ax.axvline(np.median(ious), color="#dd6b20", ls=":", label=f"Median = {np.median(ious):.3f}")
ax.set_xlabel("IoU (Intersection over Union)")
ax.set_ylabel("Matched building pairs")
ax.set_title(f"Geometric agreement, confirmed matches (n={len(conf)})")
ax.legend(frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "iou_histogram.png")); plt.close()

fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
ts = [t for t, _, _ in sens]; rs = [r for _, _, r in sens]
ax.plot(ts, rs, marker="o", color="#2b6cb0", lw=2)
ax.set_xlabel('IoU threshold defining a "confirmed match"')
ax.set_ylabel("Recall (%)"); ax.set_ylim(0, 100); ax.set_xticks(ts)
ax.grid(axis="y", alpha=0.3)
ax.set_title("Sensitivity of recall to matching threshold")
plt.tight_layout(); plt.savefig(os.path.join(FIG, "sensitivity_curve.png")); plt.close()

print("\nOutputs written next to the script.")
