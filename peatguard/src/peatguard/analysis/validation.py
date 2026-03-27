"""Cross-validation of InSAR subsidence using independent datasets.

Provides independent evidence that the InSAR velocity signal is real by
computing spatial correlations between subsidence velocity and:

1. VV backscatter (SAR-derived vegetation proxy)
   - Cleared/degraded land has higher VV backscatter than intact forest
   - Expect: negative correlation (more subsidence = higher backscatter)

2. InSAR coherence (land cover proxy)
   - High coherence = cleared land, low coherence = forest
   - Expect: negative correlation (more subsidence = higher coherence)

3. Canal distance (hydrological driver)
   - Subsidence is driven by drainage via canals (Hooijer et al. 2012)
   - Expect: positive correlation (more subsidence closer to canals)

4. Sentinel-2 NDVI (optical vegetation index, optional)
   - Low NDVI indicates degraded or cleared vegetation
   - Expect: positive correlation (more subsidence = lower NDVI)
   - Requires external download from Planetary Computer STAC API

All correlations use existing pipeline products except NDVI, which
is attempted as a bonus download. Results are written to a JSON file.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from peatguard.export.cog import read_raster, write_cog

logger = logging.getLogger(__name__)


def _extract_valid_pairs(
    arr_a: np.ndarray,
    arr_b: np.ndarray,
    nodata_a: float = -9999.0,
    nodata_b: float = -9999.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract co-located valid pixel pairs from two aligned arrays.

    Returns 1D arrays of valid values from both inputs, excluding pixels
    where either array has nodata or non-finite values.
    """
    valid = (
        (arr_a != nodata_a)
        & (arr_b != nodata_b)
        & np.isfinite(arr_a)
        & np.isfinite(arr_b)
    )
    return arr_a[valid], arr_b[valid]


def _compute_correlation(
    values_a: np.ndarray,
    values_b: np.ndarray,
    label: str,
    min_pixels: int = 100,
) -> dict:
    """Compute Pearson correlation between two 1D arrays.

    Args:
        values_a: First variable (1D, already filtered for validity).
        values_b: Second variable (1D, same length as values_a).
        label: Human-readable label for logging.
        min_pixels: Minimum number of valid pixels required.

    Returns:
        Dict with correlation_r, p_value, n_valid_pixels, and label.
        If insufficient data, returns r=NaN.
    """
    n = len(values_a)
    if n < min_pixels:
        logger.warning(
            "Insufficient valid pixels for %s correlation: %d < %d",
            label, n, min_pixels,
        )
        return {
            "label": label,
            "correlation_r": float("nan"),
            "p_value": float("nan"),
            "n_valid_pixels": n,
            "status": "insufficient_data",
        }

    r, p = stats.pearsonr(values_a, values_b)
    logger.info(
        "%s correlation: r=%.4f, p=%.2e, n=%d pixels",
        label, r, p, n,
    )
    return {
        "label": label,
        "correlation_r": float(r),
        "p_value": float(p),
        "n_valid_pixels": int(n),
        "status": "significant" if p < 0.05 else "not_significant",
    }


def _reproject_to_match(
    source_path: Path,
    reference_path: Path,
    output_path: Path,
    resampling: str = "bilinear",
) -> Path:
    """Reproject source raster to match reference raster grid.

    Ensures both rasters share the same CRS, extent, and pixel grid
    before correlation analysis.

    Args:
        source_path: Raster to reproject.
        reference_path: Target grid definition.
        output_path: Path for the reprojected output.
        resampling: Resampling method (bilinear for continuous, nearest for categorical).

    Returns:
        Path to the reprojected raster.
    """
    import rasterio
    from rasterio.warp import Resampling, reproject

    resampling_map = {
        "bilinear": Resampling.bilinear,
        "nearest": Resampling.nearest,
        "cubic": Resampling.cubic,
    }
    resamp = resampling_map.get(resampling, Resampling.bilinear)

    with rasterio.open(reference_path) as ref:
        ref_crs = ref.crs
        ref_transform = ref.transform
        ref_width = ref.width
        ref_height = ref.height

    with rasterio.open(source_path) as src:
        # Check if reprojection is actually needed
        if (
            src.crs == ref_crs
            and src.width == ref_width
            and src.height == ref_height
            and src.transform == ref_transform
        ):
            logger.info("Source already matches reference grid, no reprojection needed")
            return source_path

        output_path.parent.mkdir(parents=True, exist_ok=True)
        dst_data = np.zeros((ref_height, ref_width), dtype=np.float32)

        reproject(
            source=rasterio.band(src, 1),
            destination=dst_data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=resamp,
        )

    write_cog(
        data=dst_data,
        output_path=output_path,
        crs=ref_crs,
        transform=ref_transform,
        nodata=-9999.0,
        band_names=["reprojected"],
        dtype="float32",
    )
    logger.info(
        "Reprojected %s to match %s (%dx%d, %s)",
        source_path.name, reference_path.name, ref_width, ref_height, ref_crs,
    )
    return output_path


def _compute_zonal_stats(
    velocity: np.ndarray,
    mask: np.ndarray,
    vel_nodata: float = -9999.0,
    label_true: str = "cleared",
    label_false: str = "forested",
) -> dict:
    """Compute velocity statistics for two zones defined by a binary mask.

    Used to test whether subsidence rates differ between cleared and
    forested areas (high vs low coherence zones).

    Args:
        velocity: 2D velocity array (mm/yr, negative = subsidence).
        mask: Boolean 2D array (True = first zone, False = second zone).
        vel_nodata: Velocity nodata value.
        label_true: Name for pixels where mask is True.
        label_false: Name for pixels where mask is False.

    Returns:
        Dict with mean, median, std for each zone, plus t-test results.
    """
    valid = (velocity != vel_nodata) & np.isfinite(velocity)

    zone_true = velocity[valid & mask]
    zone_false = velocity[valid & ~mask]

    result = {
        f"{label_true}_n": int(len(zone_true)),
        f"{label_true}_mean_mm_yr": float(np.mean(zone_true)) if len(zone_true) > 0 else None,
        f"{label_true}_median_mm_yr": float(np.median(zone_true)) if len(zone_true) > 0 else None,
        f"{label_true}_std_mm_yr": float(np.std(zone_true)) if len(zone_true) > 0 else None,
        f"{label_false}_n": int(len(zone_false)),
        f"{label_false}_mean_mm_yr": float(np.mean(zone_false)) if len(zone_false) > 0 else None,
        f"{label_false}_median_mm_yr": float(np.median(zone_false)) if len(zone_false) > 0 else None,
        f"{label_false}_std_mm_yr": float(np.std(zone_false)) if len(zone_false) > 0 else None,
    }

    # Welch's t-test for difference in means
    if len(zone_true) >= 30 and len(zone_false) >= 30:
        t_stat, t_p = stats.ttest_ind(zone_true, zone_false, equal_var=False)
        result["t_statistic"] = float(t_stat)
        result["t_p_value"] = float(t_p)
        result["difference_significant"] = bool(t_p < 0.05)
        logger.info(
            "Zonal t-test (%s vs %s): t=%.3f, p=%.2e, significant=%s",
            label_true, label_false, t_stat, t_p, t_p < 0.05,
        )
    else:
        result["t_statistic"] = None
        result["t_p_value"] = None
        result["difference_significant"] = None
        logger.warning(
            "Insufficient data for t-test: %s=%d, %s=%d (need >= 30 each)",
            label_true, len(zone_true), label_false, len(zone_false),
        )

    return result


# ---------------------------------------------------------------------------
# Core validation functions
# ---------------------------------------------------------------------------

def validate_velocity_vs_backscatter(
    velocity_path: Path,
    vv_path: Path,
    output_dir: Path,
) -> dict:
    """Correlate subsidence velocity with VV backscatter.

    On cleared/degraded peatland, VV backscatter is typically higher than
    under intact forest canopy (C-band reflects from bare soil/crops rather
    than being attenuated by canopy). If subsidence is real and driven by
    land clearing, we expect negative correlation: more subsidence (more
    negative velocity) in areas with higher backscatter.

    Args:
        velocity_path: Path to subsidence velocity GeoTIFF (mm/yr).
        vv_path: Path to VV backscatter composite GeoTIFF (linear scale).
        output_dir: Directory for output files.

    Returns:
        Correlation statistics dict.
    """
    logger.info("Validating velocity vs VV backscatter")

    vel_data, vel_meta = read_raster(velocity_path)
    velocity = vel_data[0]
    vel_nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    vv_data, vv_meta = read_raster(vv_path)
    vv = vv_data[0]
    vv_nodata = vv_meta["nodata"] if vv_meta["nodata"] is not None else -9999.0

    # Reproject if grids differ
    if velocity.shape != vv.shape:
        logger.info(
            "Grid mismatch: velocity %s vs VV %s, reprojecting velocity",
            velocity.shape, vv.shape,
        )
        reproj_path = output_dir / "validation_velocity_reproj.tif"
        _reproject_to_match(velocity_path, vv_path, reproj_path)
        vel_data, vel_meta = read_raster(reproj_path)
        velocity = vel_data[0]
        vel_nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    vel_vals, vv_vals = _extract_valid_pairs(velocity, vv, vel_nodata, vv_nodata)
    result = _compute_correlation(vel_vals, vv_vals, "velocity_vs_vv_backscatter")

    # Also compute with dB scale for interpretability
    vv_db = 10.0 * np.log10(np.clip(vv_vals, 1e-10, None))
    result_db = _compute_correlation(vel_vals, vv_db, "velocity_vs_vv_backscatter_dB")
    result["correlation_r_dB"] = result_db["correlation_r"]
    result["p_value_dB"] = result_db["p_value"]

    return result


def validate_velocity_vs_coherence(
    velocity_path: Path,
    coherence_path: Path,
    output_dir: Path,
    coherence_threshold: float = 0.5,
) -> dict:
    """Correlate subsidence velocity with InSAR coherence.

    High temporal coherence indicates cleared/stable land surfaces
    (bare soil, plantations), while low coherence indicates forest.
    On tropical peatland, clearing precedes drainage, so subsidence
    should be stronger on cleared (high-coherence) land.

    Also performs a zonal analysis: splits pixels into "cleared"
    (coherence > threshold) and "forested" (coherence <= threshold)
    zones and tests whether mean subsidence differs significantly.

    Args:
        velocity_path: Path to subsidence velocity GeoTIFF (mm/yr).
        coherence_path: Path to temporal coherence GeoTIFF (0-1).
        output_dir: Directory for output files.
        coherence_threshold: Threshold separating cleared from forested.

    Returns:
        Dict with correlation stats and zonal analysis.
    """
    logger.info("Validating velocity vs coherence")

    vel_data, vel_meta = read_raster(velocity_path)
    velocity = vel_data[0]
    vel_nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    coh_data, coh_meta = read_raster(coherence_path)
    coherence = coh_data[0]
    coh_nodata = coh_meta["nodata"] if coh_meta["nodata"] is not None else -9999.0

    # Reproject if grids differ
    if velocity.shape != coherence.shape:
        logger.info(
            "Grid mismatch: velocity %s vs coherence %s, reprojecting velocity",
            velocity.shape, coherence.shape,
        )
        reproj_path = output_dir / "validation_velocity_coh_reproj.tif"
        _reproject_to_match(velocity_path, coherence_path, reproj_path)
        vel_data, vel_meta = read_raster(reproj_path)
        velocity = vel_data[0]
        vel_nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    vel_vals, coh_vals = _extract_valid_pairs(velocity, coherence, vel_nodata, coh_nodata)
    result = _compute_correlation(vel_vals, coh_vals, "velocity_vs_coherence")

    # Zonal analysis: cleared vs forested
    valid = (
        (velocity != vel_nodata)
        & (coherence != coh_nodata)
        & np.isfinite(velocity)
        & np.isfinite(coherence)
    )
    cleared_mask = valid & (coherence > coherence_threshold)
    zonal = _compute_zonal_stats(
        velocity, cleared_mask, vel_nodata,
        label_true="cleared_high_coherence",
        label_false="forested_low_coherence",
    )
    result["zonal_analysis"] = zonal
    result["coherence_threshold"] = coherence_threshold

    return result


def validate_velocity_vs_canal_distance(
    velocity_path: Path,
    canal_distance_path: Path,
    output_dir: Path,
) -> dict:
    """Correlate subsidence velocity with distance to nearest canal.

    The Hooijer et al. (2012) model predicts that subsidence increases
    (velocity becomes more negative) closer to drainage canals. This
    validation checks whether the InSAR velocity field is consistent
    with that hydrological expectation.

    Expect: positive correlation (distance increases, velocity increases
    toward zero -- less subsidence far from canals).

    Args:
        velocity_path: Path to subsidence velocity GeoTIFF (mm/yr).
        canal_distance_path: Path to canal distance GeoTIFF (meters).
        output_dir: Directory for output files.

    Returns:
        Correlation statistics dict.
    """
    logger.info("Validating velocity vs canal distance")

    vel_data, vel_meta = read_raster(velocity_path)
    velocity = vel_data[0]
    vel_nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    dist_data, dist_meta = read_raster(canal_distance_path)
    distance = dist_data[0]
    dist_nodata = dist_meta["nodata"] if dist_meta["nodata"] is not None else -9999.0

    # Reproject if grids differ
    if velocity.shape != distance.shape:
        logger.info(
            "Grid mismatch: velocity %s vs canal distance %s, reprojecting velocity",
            velocity.shape, distance.shape,
        )
        reproj_path = output_dir / "validation_velocity_dist_reproj.tif"
        _reproject_to_match(velocity_path, canal_distance_path, reproj_path)
        vel_data, vel_meta = read_raster(reproj_path)
        velocity = vel_data[0]
        vel_nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    vel_vals, dist_vals = _extract_valid_pairs(velocity, distance, vel_nodata, dist_nodata)
    result = _compute_correlation(vel_vals, dist_vals, "velocity_vs_canal_distance")

    # Also compute binned statistics for a distance-subsidence profile
    if len(vel_vals) >= 100:
        bin_edges = np.arange(0, min(dist_vals.max(), 3000) + 200, 200)
        bin_means = []
        bin_centers = []
        bin_counts = []
        for i in range(len(bin_edges) - 1):
            in_bin = (dist_vals >= bin_edges[i]) & (dist_vals < bin_edges[i + 1])
            if in_bin.sum() >= 10:
                bin_means.append(float(np.mean(vel_vals[in_bin])))
                bin_centers.append(float((bin_edges[i] + bin_edges[i + 1]) / 2))
                bin_counts.append(int(in_bin.sum()))
        result["distance_profile"] = {
            "bin_centers_m": bin_centers,
            "mean_velocity_mm_yr": bin_means,
            "pixel_counts": bin_counts,
        }
        logger.info(
            "Distance-subsidence profile: %d bins from 0 to %.0f m",
            len(bin_centers), bin_edges[-1],
        )

    return result


def validate_subsidence_with_ndvi(
    velocity_path: Path,
    ndvi_path: Path,
    output_dir: Path,
) -> dict:
    """Correlate subsidence velocity with Sentinel-2 NDVI composite.

    Degraded peatland (drained, cleared) typically shows lower NDVI
    than intact peat swamp forest. If subsidence is real and driven
    by land cover change, expect positive correlation: more subsidence
    (negative velocity) in areas with lower NDVI.

    The NDVI composite must already be computed and saved as a GeoTIFF.
    This function handles reprojection to match the velocity grid.

    Args:
        velocity_path: Path to subsidence velocity GeoTIFF (mm/yr).
        ndvi_path: Path to NDVI composite GeoTIFF (-1 to 1).
        output_dir: Directory for output files.

    Returns:
        Dict with correlation statistics.
    """
    logger.info("Validating velocity vs Sentinel-2 NDVI")

    vel_data, vel_meta = read_raster(velocity_path)
    velocity = vel_data[0]
    vel_nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    # Reproject NDVI to match velocity grid
    ndvi_aligned_path = output_dir / "validation_ndvi_aligned.tif"
    _reproject_to_match(ndvi_path, velocity_path, ndvi_aligned_path)
    ndvi_data, ndvi_meta = read_raster(ndvi_aligned_path)
    ndvi = ndvi_data[0]

    # NDVI nodata is typically NaN
    ndvi_nodata = ndvi_meta["nodata"] if ndvi_meta["nodata"] is not None else -9999.0

    vel_vals, ndvi_vals = _extract_valid_pairs(velocity, ndvi, vel_nodata, ndvi_nodata)
    result = _compute_correlation(vel_vals, ndvi_vals, "velocity_vs_ndvi")

    # Zonal: low NDVI (<0.3) vs high NDVI (>0.6) subsidence comparison
    valid = (
        (velocity != vel_nodata)
        & np.isfinite(velocity)
        & np.isfinite(ndvi)
        & (ndvi != ndvi_nodata)
    )
    low_ndvi_mask = valid & (ndvi < 0.3)
    high_ndvi_mask = valid & (ndvi > 0.6)

    low_vel = velocity[low_ndvi_mask]
    high_vel = velocity[high_ndvi_mask]

    result["zonal_analysis"] = {
        "low_ndvi_lt_0.3_n": int(len(low_vel)),
        "low_ndvi_lt_0.3_mean_velocity": float(np.mean(low_vel)) if len(low_vel) > 0 else None,
        "high_ndvi_gt_0.6_n": int(len(high_vel)),
        "high_ndvi_gt_0.6_mean_velocity": float(np.mean(high_vel)) if len(high_vel) > 0 else None,
    }

    if len(low_vel) >= 30 and len(high_vel) >= 30:
        t_stat, t_p = stats.ttest_ind(low_vel, high_vel, equal_var=False)
        result["zonal_analysis"]["t_statistic"] = float(t_stat)
        result["zonal_analysis"]["t_p_value"] = float(t_p)
        result["zonal_analysis"]["difference_significant"] = bool(t_p < 0.05)

    return result


# ---------------------------------------------------------------------------
# Sentinel-2 NDVI download via Planetary Computer STAC
# ---------------------------------------------------------------------------

def download_sentinel2_composite(
    bbox: list[float],
    start_date: str,
    end_date: str,
    output_dir: Path,
    max_cloud_cover: int = 30,
    max_scenes: int = 20,
) -> Optional[Path]:
    """Download Sentinel-2 B4/B8 bands and compute a cloud-free NDVI composite.

    Uses the Microsoft Planetary Computer STAC API (free, no auth) to find
    Sentinel-2 L2A scenes, downloads Red (B4) and NIR (B8) bands, and
    computes a temporal median NDVI composite.

    Args:
        bbox: Bounding box as [west, south, east, north].
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).
        output_dir: Directory for output files.
        max_cloud_cover: Maximum cloud cover percentage per scene.
        max_scenes: Maximum number of scenes to composite.

    Returns:
        Path to the NDVI composite GeoTIFF, or None if download fails.
    """
    try:
        import pystac_client
        import planetary_computer
        import rasterio
        from rasterio.windows import from_bounds as window_from_bounds
    except ImportError as exc:
        logger.warning(
            "Sentinel-2 NDVI download requires pystac-client and planetary-computer packages: %s",
            exc,
        )
        return None

    catalog_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ndvi_output = output_dir / "validation_ndvi_composite.tif"

    logger.info(
        "Searching Planetary Computer for Sentinel-2 L2A: bbox=%s, dates=%s to %s, cloud<=%d%%",
        bbox, start_date, end_date, max_cloud_cover,
    )

    try:
        catalog = pystac_client.Client.open(
            catalog_url,
            modifier=planetary_computer.sign_inplace,
        )

        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date}/{end_date}",
            query={"eo:cloud_cover": {"lt": max_cloud_cover}},
            max_items=max_scenes,
        )

        items = list(search.items())
        if not items:
            logger.warning("No Sentinel-2 scenes found matching criteria")
            return None

        logger.info("Found %d Sentinel-2 scenes, computing NDVI composite", len(items))

        ndvi_stack = []
        transform_ref = None
        crs_ref = None
        shape_ref = None

        for item in items:
            try:
                red_href = item.assets["B04"].href
                nir_href = item.assets["B08"].href

                with rasterio.open(red_href) as red_ds:
                    # Read only the AOI window
                    win = window_from_bounds(*bbox, transform=red_ds.transform)
                    red = red_ds.read(1, window=win).astype(np.float32)
                    if transform_ref is None:
                        transform_ref = red_ds.window_transform(win)
                        crs_ref = red_ds.crs
                        shape_ref = red.shape

                with rasterio.open(nir_href) as nir_ds:
                    win = window_from_bounds(*bbox, transform=nir_ds.transform)
                    nir = nir_ds.read(1, window=win).astype(np.float32)

                # Ensure shapes match (scenes may have slightly different extents)
                if red.shape != shape_ref or nir.shape != shape_ref:
                    logger.debug(
                        "Skipping scene %s: shape mismatch %s vs %s",
                        item.id, red.shape, shape_ref,
                    )
                    continue

                # Sentinel-2 L2A reflectance is scaled by 10000
                red = red / 10000.0
                nir = nir / 10000.0

                denominator = nir + red
                ndvi = np.where(denominator > 0, (nir - red) / denominator, np.nan)
                ndvi_stack.append(ndvi)
                logger.debug("Scene %s: NDVI mean=%.3f", item.id, np.nanmean(ndvi))

            except Exception as exc:
                logger.debug("Failed to process scene %s: %s", item.id, exc)
                continue

        if not ndvi_stack:
            logger.warning("No Sentinel-2 scenes could be processed")
            return None

        # Temporal median composite (robust to residual clouds)
        ndvi_composite = np.nanmedian(np.stack(ndvi_stack, axis=0), axis=0)
        logger.info(
            "NDVI composite from %d scenes: min=%.3f, max=%.3f, mean=%.3f",
            len(ndvi_stack),
            np.nanmin(ndvi_composite),
            np.nanmax(ndvi_composite),
            np.nanmean(ndvi_composite),
        )

        # Replace NaN with nodata
        ndvi_composite = np.where(np.isfinite(ndvi_composite), ndvi_composite, -9999.0)

        write_cog(
            data=ndvi_composite.astype(np.float32),
            output_path=ndvi_output,
            crs=crs_ref,
            transform=transform_ref,
            nodata=-9999.0,
            band_names=["ndvi_composite"],
            dtype="float32",
        )

        logger.info("Sentinel-2 NDVI composite written: %s", ndvi_output)
        return ndvi_output

    except Exception as exc:
        logger.warning("Sentinel-2 NDVI download failed (non-fatal): %s", exc)
        return None


# ---------------------------------------------------------------------------
# Main validation runner
# ---------------------------------------------------------------------------

def run_validation(
    velocity_path: Path,
    output_dir: Path,
    vv_path: Optional[Path] = None,
    coherence_path: Optional[Path] = None,
    canal_distance_path: Optional[Path] = None,
    ndvi_path: Optional[Path] = None,
    bbox: Optional[list[float]] = None,
    ndvi_start_date: Optional[str] = None,
    ndvi_end_date: Optional[str] = None,
) -> dict:
    """Run all available cross-validation analyses.

    Executes each validation that has the required input data, skipping
    those without inputs. Results are written to validation_report.json.

    Args:
        velocity_path: Path to subsidence velocity GeoTIFF (mm/yr).
        output_dir: Directory for validation outputs.
        vv_path: Path to VV backscatter composite (optional).
        coherence_path: Path to temporal coherence raster (optional).
        canal_distance_path: Path to canal distance raster (optional).
        ndvi_path: Path to pre-existing NDVI composite (optional).
        bbox: AOI bounding box for Sentinel-2 download attempt.
        ndvi_start_date: Start date for Sentinel-2 search (YYYY-MM-DD).
        ndvi_end_date: End date for Sentinel-2 search (YYYY-MM-DD).

    Returns:
        Dict containing all validation results.
    """
    output_dir = Path(output_dir)
    validation_dir = output_dir / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "velocity_path": str(velocity_path),
        "correlations": {},
    }

    # 1. Velocity vs VV backscatter
    if vv_path and vv_path.exists():
        try:
            result = validate_velocity_vs_backscatter(
                velocity_path, vv_path, validation_dir,
            )
            report["correlations"]["velocity_vs_vv_backscatter"] = result
        except Exception as exc:
            logger.warning("Velocity vs VV backscatter validation failed: %s", exc)
            report["correlations"]["velocity_vs_vv_backscatter"] = {
                "status": "error", "error": str(exc),
            }
    else:
        logger.info("VV backscatter not available, skipping backscatter validation")

    # 2. Velocity vs coherence
    if coherence_path and coherence_path.exists():
        try:
            result = validate_velocity_vs_coherence(
                velocity_path, coherence_path, validation_dir,
            )
            report["correlations"]["velocity_vs_coherence"] = result
        except Exception as exc:
            logger.warning("Velocity vs coherence validation failed: %s", exc)
            report["correlations"]["velocity_vs_coherence"] = {
                "status": "error", "error": str(exc),
            }
    else:
        logger.info("Coherence raster not available, skipping coherence validation")

    # 3. Velocity vs canal distance
    if canal_distance_path and canal_distance_path.exists():
        try:
            result = validate_velocity_vs_canal_distance(
                velocity_path, canal_distance_path, validation_dir,
            )
            report["correlations"]["velocity_vs_canal_distance"] = result
        except Exception as exc:
            logger.warning("Velocity vs canal distance validation failed: %s", exc)
            report["correlations"]["velocity_vs_canal_distance"] = {
                "status": "error", "error": str(exc),
            }
    else:
        logger.info("Canal distance not available, skipping canal distance validation")

    # 4. Sentinel-2 NDVI
    # Try to download if not provided and bbox is available
    if ndvi_path is None and bbox is not None:
        ndvi_start = ndvi_start_date or "2024-01-01"
        ndvi_end = ndvi_end_date or "2024-12-31"
        logger.info("Attempting Sentinel-2 NDVI download for cross-validation")
        ndvi_path = download_sentinel2_composite(
            bbox=bbox,
            start_date=ndvi_start,
            end_date=ndvi_end,
            output_dir=validation_dir,
        )

    if ndvi_path and ndvi_path.exists():
        try:
            result = validate_subsidence_with_ndvi(
                velocity_path, ndvi_path, validation_dir,
            )
            report["correlations"]["velocity_vs_ndvi"] = result
            report["ndvi_path"] = str(ndvi_path)
        except Exception as exc:
            logger.warning("Velocity vs NDVI validation failed: %s", exc)
            report["correlations"]["velocity_vs_ndvi"] = {
                "status": "error", "error": str(exc),
            }
    else:
        logger.info("NDVI composite not available, skipping NDVI validation")

    # Write report
    report_path = validation_dir / "validation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Validation report written: %s", report_path)

    # Summary
    n_total = len(report["correlations"])
    n_significant = sum(
        1 for v in report["correlations"].values()
        if isinstance(v, dict) and v.get("status") == "significant"
    )
    logger.info(
        "Validation summary: %d correlations computed, %d statistically significant (p < 0.05)",
        n_total, n_significant,
    )

    return report
