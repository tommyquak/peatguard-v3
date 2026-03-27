#!/usr/bin/env python3
"""Find the optimal InSAR reference point for the Kapuas AOI.

Downloads coherence_median.tif from GCS, analyzes coherence values,
and recommends the best reference point (lat, lon) for MintPy time-series
inversion. The reference point should be:

  1. HIGH temporal coherence (>0.7, ideally >0.8)
  2. On STABLE ground (not subsiding peat)
  3. On NON-PEAT substrate if possible (roads, buildings, bridges)
  4. Within the processed frame (not outside data coverage)

Usage:
    python scripts/find_reference_point.py [--coherence-file /path/to/coherence.tif]

If --coherence-file is not provided, downloads from GCS:
    gs://peatguard-data/products/coherence_median.tif
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("find_reference_point")

# Kapuas AOI bounding box: [west, south, east, north]
# From config/kapuas.yaml
KAPUAS_BBOX = [114.304, -2.611, 114.404, -2.511]

# Known stable feature locations within/near the Kapuas AOI.
# These are bridges, roads, or settlements on non-peat substrate
# that are likely to have persistent scatterers.
CANDIDATE_STABLE_FEATURES = {
    "Teluk_Bayur_village_center": (-2.545, 114.355),
    "Road_junction_north_AOI": (-2.520, 114.350),
    "Kapuas_River_bridge_east": (-2.540, 114.390),
    "Road_along_northern_edge": (-2.515, 114.340),
    "Settlement_NE_corner": (-2.518, 114.380),
}


def download_from_gcs(gcs_path: str, local_path: Path) -> Path:
    """Download a file from GCS using gsutil."""
    logger.info("Downloading %s -> %s", gcs_path, local_path)
    result = subprocess.run(
        ["gsutil", "cp", gcs_path, str(local_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("gsutil failed: %s", result.stderr.strip())
        raise RuntimeError(f"Failed to download {gcs_path}: {result.stderr.strip()}")
    logger.info("Download complete: %.1f MB", local_path.stat().st_size / 1e6)
    return local_path


def analyze_coherence(tif_path: Path) -> dict:
    """Analyze coherence GeoTIFF and find optimal reference points.

    Returns:
        Dict with analysis results including top candidates.
    """
    import rasterio

    logger.info("Reading coherence raster: %s", tif_path)
    with rasterio.open(tif_path) as src:
        coherence = src.read(1)
        transform = src.transform
        crs = src.crs
        nodata = src.nodata
        height, width = coherence.shape

    logger.info(
        "Raster: %d x %d pixels, CRS: %s, nodata: %s",
        height, width, crs, nodata,
    )

    # Mask nodata and invalid values
    valid_mask = np.ones_like(coherence, dtype=bool)
    if nodata is not None:
        valid_mask &= coherence != nodata
    valid_mask &= np.isfinite(coherence)
    valid_mask &= (coherence >= 0) & (coherence <= 1)

    valid_values = coherence[valid_mask]
    logger.info(
        "Valid pixels: %d / %d (%.1f%%)",
        valid_values.size,
        coherence.size,
        100.0 * valid_values.size / coherence.size,
    )
    logger.info(
        "Coherence stats: min=%.4f, max=%.4f, mean=%.4f, median=%.4f",
        valid_values.min(),
        valid_values.max(),
        valid_values.mean(),
        np.median(valid_values),
    )

    # Count pixels above thresholds
    for threshold in [0.5, 0.6, 0.7, 0.8, 0.9]:
        count = np.sum(valid_values >= threshold)
        logger.info(
            "  Coherence >= %.1f: %d pixels (%.2f%%)",
            threshold, count, 100.0 * count / valid_values.size,
        )

    # Find pixels with coherence > 0.7 (the reference_min_coherence from config)
    high_coh_mask = valid_mask & (coherence >= 0.7)
    high_coh_rows, high_coh_cols = np.where(high_coh_mask)

    if high_coh_rows.size == 0:
        logger.warning("No pixels with coherence >= 0.7. Lowering threshold to 0.5.")
        high_coh_mask = valid_mask & (coherence >= 0.5)
        high_coh_rows, high_coh_cols = np.where(high_coh_mask)

    if high_coh_rows.size == 0:
        logger.error("No pixels with coherence >= 0.5. Cannot find reference point.")
        return {"error": "No high-coherence pixels found"}

    logger.info("High-coherence candidate pixels (>=0.7): %d", high_coh_rows.size)

    # Convert pixel coordinates to geographic coordinates
    def pixel_to_lonlat(row, col):
        """Convert pixel (row, col) to (lon, lat) using the affine transform."""
        lon = transform.c + col * transform.a + row * transform.b
        lat = transform.f + col * transform.d + row * transform.e
        return lon, lat

    # Find the top 10 highest-coherence pixels
    flat_indices = np.argsort(coherence[valid_mask])[::-1][:100]
    valid_rows, valid_cols = np.where(valid_mask)

    top_candidates = []
    seen_locations = set()  # Avoid reporting adjacent pixels
    for idx in flat_indices:
        r, c = valid_rows[idx], valid_cols[idx]
        coh_val = coherence[r, c]
        lon, lat = pixel_to_lonlat(r, c)

        # Round to 3 decimal places (~100m) to group nearby pixels
        loc_key = (round(lat, 3), round(lon, 3))
        if loc_key in seen_locations:
            continue
        seen_locations.add(loc_key)

        # Check if within the Kapuas AOI bbox
        west, south, east, north = KAPUAS_BBOX
        in_aoi = (west <= lon <= east) and (south <= lat <= north)

        top_candidates.append({
            "lat": lat,
            "lon": lon,
            "coherence": float(coh_val),
            "row": int(r),
            "col": int(c),
            "in_kapuas_aoi": in_aoi,
        })

        if len(top_candidates) >= 20:
            break

    # Score candidates: prefer high coherence near known stable features,
    # within AOI, and near AOI edges (more likely non-peat).
    logger.info("")
    logger.info("=== TOP 20 HIGHEST-COHERENCE CANDIDATE PIXELS ===")
    logger.info(
        "%-4s  %-10s  %-12s  %-8s  %-7s  %-20s",
        "Rank", "Lat", "Lon", "Coh", "In_AOI", "Nearest_Feature",
    )
    logger.info("-" * 75)

    best_candidate = None
    best_score = -1

    for i, cand in enumerate(top_candidates):
        # Find nearest known stable feature
        min_dist = float("inf")
        nearest_name = "none"
        for name, (flat, flon) in CANDIDATE_STABLE_FEATURES.items():
            dist_deg = np.sqrt((cand["lat"] - flat) ** 2 + (cand["lon"] - flon) ** 2)
            if dist_deg < min_dist:
                min_dist = dist_deg
                nearest_name = name

        # Score: coherence (0-1) + AOI bonus (0.1) + proximity to stable feature bonus
        score = cand["coherence"]
        if cand["in_kapuas_aoi"]:
            score += 0.1
        # Proximity bonus: closer to known stable feature = higher score
        # Max bonus 0.1 when distance < 0.01 deg (~1km)
        prox_bonus = max(0, 0.1 * (1 - min_dist / 0.05))
        score += prox_bonus

        # Prefer edges of AOI (more likely non-peat ground)
        if cand["in_kapuas_aoi"]:
            west, south, east, north = KAPUAS_BBOX
            edge_dist = min(
                abs(cand["lat"] - south),
                abs(cand["lat"] - north),
                abs(cand["lon"] - west),
                abs(cand["lon"] - east),
            )
            # Bonus for being within 0.02 deg (~2km) of AOI edge
            if edge_dist < 0.02:
                score += 0.05

        cand["score"] = score
        cand["nearest_feature"] = nearest_name

        logger.info(
            "%-4d  %-10.6f  %-12.6f  %-8.4f  %-7s  %s",
            i + 1,
            cand["lat"],
            cand["lon"],
            cand["coherence"],
            "YES" if cand["in_kapuas_aoi"] else "no",
            nearest_name,
        )

        if score > best_score:
            best_score = score
            best_candidate = cand

    logger.info("")
    logger.info("=== RECOMMENDED REFERENCE POINT ===")
    if best_candidate:
        logger.info(
            "  Latitude:   %.6f", best_candidate["lat"],
        )
        logger.info(
            "  Longitude:  %.6f", best_candidate["lon"],
        )
        logger.info(
            "  Coherence:  %.4f", best_candidate["coherence"],
        )
        logger.info(
            "  In AOI:     %s", best_candidate["in_kapuas_aoi"],
        )
        logger.info(
            "  Score:      %.4f", best_candidate["score"],
        )
        logger.info(
            "  Nearest:    %s", best_candidate["nearest_feature"],
        )
        logger.info("")
        logger.info(
            "Update config with:  reference_lalo: [%.6f, %.6f]",
            best_candidate["lat"],
            best_candidate["lon"],
        )

    # Also find the best candidate that is STRICTLY within the AOI
    aoi_candidates = [c for c in top_candidates if c["in_kapuas_aoi"]]
    if aoi_candidates:
        best_in_aoi = max(aoi_candidates, key=lambda c: c.get("score", c["coherence"]))
        logger.info("")
        logger.info("=== BEST CANDIDATE WITHIN KAPUAS AOI ===")
        logger.info(
            "  Latitude:   %.6f", best_in_aoi["lat"],
        )
        logger.info(
            "  Longitude:  %.6f", best_in_aoi["lon"],
        )
        logger.info(
            "  Coherence:  %.4f", best_in_aoi["coherence"],
        )
    else:
        logger.warning("No high-coherence pixels found within the Kapuas AOI bbox.")

    return {
        "top_candidates": top_candidates,
        "best_candidate": best_candidate,
        "best_in_aoi": best_in_aoi if aoi_candidates else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Find optimal InSAR reference point from coherence data."
    )
    parser.add_argument(
        "--coherence-file",
        type=Path,
        default=None,
        help="Path to coherence_median.tif. If not provided, downloads from GCS.",
    )
    parser.add_argument(
        "--gcs-path",
        type=str,
        default="gs://peatguard-data/products/coherence_median.tif",
        help="GCS path to coherence file (used if --coherence-file not provided).",
    )
    args = parser.parse_args()

    if args.coherence_file and args.coherence_file.exists():
        tif_path = args.coherence_file
    else:
        tmp_dir = Path(tempfile.mkdtemp(prefix="peatguard_ref_"))
        tif_path = tmp_dir / "coherence_median.tif"
        download_from_gcs(args.gcs_path, tif_path)

    results = analyze_coherence(tif_path)

    if "error" in results:
        logger.error("Analysis failed: %s", results["error"])
        sys.exit(1)

    best = results.get("best_in_aoi") or results.get("best_candidate")
    if best:
        logger.info("")
        logger.info("YAML snippet for config files:")
        logger.info("  mintpy:")
        logger.info(
            "    reference_lalo: [%.6f, %.6f]",
            best["lat"],
            best["lon"],
        )


if __name__ == "__main__":
    main()
