"""Peatland degradation risk scoring.

Combines canal proximity and subsidence velocity into a normalized
risk score (0-1) that indicates the likelihood and severity of
ongoing peat degradation at each pixel. Higher scores indicate
greater risk of continued carbon loss.

The risk model weights:
    - Distance to canal (inverse relationship: closer = higher risk)
    - Subsidence velocity (magnitude: faster sinking = higher risk)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from peatguard.export.cog import read_raster, write_cog

logger = logging.getLogger(__name__)


def compute_proximity_risk(
    distance_m: np.ndarray,
    max_influence_m: float = 1200.0,
) -> np.ndarray:
    """Compute canal proximity risk factor (0-1).

    Uses linear decay based on the Dupuit equation approximation:
    water table drawdown in tropical peat is roughly linear with
    distance from drainage canals. Hooijer et al. (2012) and
    Jaenicke et al. (2010) found drainage effects extend 1-1.5 km.

    Args:
        distance_m: 2D array of distances to nearest canal in meters.
        max_influence_m: Maximum influence distance in meters.
            Default 1200m from Hooijer et al. (2012).

    Returns:
        2D array of proximity risk scores (0-1, higher = closer to canal).
    """
    # Linear decay: risk = max(0, 1 - d/R)
    # At distance 0: risk = 1.0
    # At max_influence_m: risk = 0.0
    proximity_risk = np.clip(1.0 - distance_m / max_influence_m, 0.0, 1.0)

    return proximity_risk.astype(np.float32)


def compute_subsidence_risk(
    velocity_mm_yr: np.ndarray,
    severe_threshold: float = -40.0,
    nodata: float = -9999.0,
) -> np.ndarray:
    """Compute subsidence severity risk factor (0-1).

    Normalizes subsidence velocity to a 0-1 scale where the severe
    threshold maps to 1.0 and zero subsidence maps to 0.0.

    Args:
        velocity_mm_yr: 2D array of subsidence velocity in mm/yr.
        severe_threshold: Threshold for maximum risk (mm/yr, negative).
        nodata: NoData value.

    Returns:
        2D array of subsidence risk scores (0-1, higher = more subsidence).
    """
    valid = (velocity_mm_yr != nodata) & np.isfinite(velocity_mm_yr)
    risk = np.zeros_like(velocity_mm_yr, dtype=np.float32)

    # Only negative velocity contributes to risk
    negative = valid & (velocity_mm_yr < 0)
    risk[negative] = np.clip(-velocity_mm_yr[negative] / abs(severe_threshold), 0.0, 1.0)

    return risk


def compute_combined_risk(
    proximity_risk: np.ndarray,
    subsidence_risk: np.ndarray,
    proximity_weight: float = 0.45,
    subsidence_weight: float = 0.55,
) -> np.ndarray:
    """Combine proximity and subsidence risk into a single score.

    Args:
        proximity_risk: Canal proximity risk (0-1).
        subsidence_risk: Subsidence severity risk (0-1).
        proximity_weight: Weight for proximity component.
        subsidence_weight: Weight for subsidence component.

    Returns:
        2D array of combined risk scores (0-1).
    """
    total_weight = proximity_weight + subsidence_weight
    combined = (
        proximity_weight * proximity_risk + subsidence_weight * subsidence_risk
    ) / total_weight

    return np.clip(combined, 0.0, 1.0).astype(np.float32)


def generate_risk_map(
    velocity_path: Path,
    distance_path: Path,
    output_path: Path,
    proximity_weight: float = 0.45,
    subsidence_weight: float = 0.55,
    max_influence_m: float = 1200.0,
    severe_velocity_mm_yr: float = -40.0,
    water_mask_path: Optional[Path] = None,
    coherence_path: Optional[Path] = None,
    coherence_threshold: float = 0.7,
) -> Path:
    """Generate a combined risk score map from velocity and distance rasters.

    Args:
        velocity_path: Path to subsidence velocity GeoTIFF (mm/yr).
        distance_path: Path to canal distance GeoTIFF (meters).
        output_path: Path for the risk score output.
        proximity_weight: Weight for canal proximity risk.
        subsidence_weight: Weight for subsidence risk.
        max_influence_m: Maximum canal influence distance.
        water_mask_path: Optional path to water mask GeoTIFF.
            Water pixels are excluded from the risk score (set to
            nodata) because they are not peatland and should not
            contribute to degradation risk assessment.

    Returns:
        Path to the risk score GeoTIFF.
    """
    logger.info("Generating risk map from %s and %s", velocity_path.name, distance_path.name)

    vel_data, vel_meta = read_raster(velocity_path)
    dist_data, dist_meta = read_raster(distance_path)

    velocity = vel_data[0]
    distance = dist_data[0]

    nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    # Smooth velocity with a median filter to reduce pixel-level noise before
    # risk scoring. InSAR velocity has high-frequency noise (std ~80-100 mm/yr)
    # that creates blotchy risk maps. A 5x5 median preserves edges (canal
    # boundaries, land cover transitions) while suppressing speckle-like noise.
    from scipy.ndimage import median_filter
    valid = (velocity != nodata) & np.isfinite(velocity)
    vel_smoothed = velocity.copy()
    # Fill nodata with global median (not 0) to avoid edge bias. Filling with
    # 0 biases the median filter toward 0 at valid/nodata boundaries, since
    # the global median (~-25 mm/yr) is much closer to real peat velocities.
    global_median = np.median(velocity[valid]) if np.any(valid) else 0.0
    vel_smoothed[~valid] = global_median
    vel_smoothed = median_filter(vel_smoothed, size=9).astype(np.float32)
    vel_smoothed[~valid] = nodata  # restore nodata
    logger.info("Applied 9x9 median filter to velocity before risk scoring")

    # Coherence filter: exclude low-coherence pixels that produce noisy risk.
    # Matches the coherence filtering used in carbon_loss for consistency.
    if coherence_path is not None and coherence_path.exists():
        coh_data, coh_meta = read_raster(coherence_path)
        coh = coh_data[0]
        if coh.shape == velocity.shape:
            low_coh = coh < coherence_threshold
            valid[low_coh] = False
            vel_smoothed[low_coh] = nodata
            logger.info(
                "Risk coherence filter: %d pixels excluded (coh < %.1f)",
                int(low_coh.sum()), coherence_threshold,
            )
            del low_coh
        else:
            logger.warning(
                "Coherence shape %s != velocity shape %s, skipping filter",
                coh.shape, velocity.shape,
            )
        del coh_data, coh

    proximity_risk = compute_proximity_risk(distance, max_influence_m)
    subsidence_risk = compute_subsidence_risk(
        vel_smoothed, severe_threshold=severe_velocity_mm_yr, nodata=nodata
    )
    del vel_smoothed

    # Full weighted risk (requires valid velocity)
    combined_full = compute_combined_risk(
        proximity_risk,
        subsidence_risk,
        proximity_weight,
        subsidence_weight,
    )

    # Distance validity: distance_path is canal_distance.tif. Nodata can be
    # either the raster's declared nodata or non-finite values.
    dist_nodata = dist_meta.get("nodata")
    dist_valid = np.isfinite(distance)
    if dist_nodata is not None:
        dist_valid &= distance != dist_nodata

    # Proximity-only fallback: where velocity is unavailable but canal
    # distance is, publish the proximity component (0-1) on its own so the
    # map covers the AOI instead of collapsing to a tiny high-coherence
    # patch. Confidence band below distinguishes "velocity-backed" (2)
    # from "proximity-only" (1) for the map reader.
    vel_valid = valid.copy()  # after coherence filter
    fallback_cells = dist_valid & ~vel_valid
    combined = combined_full.copy()
    combined[fallback_cells] = proximity_risk[fallback_cells]

    # Confidence band: 0 nodata, 1 proximity-only, 2 velocity-backed.
    confidence = np.zeros_like(combined, dtype=np.uint8)
    confidence[fallback_cells] = 1
    confidence[vel_valid] = 2

    # Invalid = neither velocity nor distance valid (nowhere to compute risk)
    invalid = ~vel_valid & ~fallback_cells

    # Exclude water pixels from risk score and confidence
    if water_mask_path is not None and water_mask_path.exists():
        wm_data, wm_meta = read_raster(water_mask_path)
        water = wm_data[0].astype(bool)

        # Handle shape mismatch by reprojecting water mask
        if water.shape != velocity.shape:
            import rasterio
            from rasterio.warp import Resampling, reproject

            logger.info(
                "Reprojecting water mask to risk grid (%s -> %s)",
                water.shape,
                velocity.shape,
            )
            wm_reprojected = np.zeros(velocity.shape, dtype=np.uint8)
            reproject(
                source=water.astype(np.uint8),
                destination=wm_reprojected,
                src_transform=wm_meta["transform"],
                src_crs=wm_meta["crs"],
                dst_transform=vel_meta["transform"],
                dst_crs=vel_meta["crs"],
                resampling=Resampling.nearest,
            )
            water = wm_reprojected.astype(bool)

        n_water_excluded = (water & ~invalid).sum()
        invalid = invalid | water
        confidence[water] = 0
        logger.info(
            "Water mask applied to risk score: %d water pixels excluded",
            n_water_excluded,
        )

    combined[invalid] = -9999.0

    n_full = int(vel_valid.sum() & ~invalid if False else (vel_valid & ~invalid).sum())
    n_prox = int((fallback_cells & ~invalid).sum())
    n_total = combined.size
    logger.info(
        "Risk map coverage: velocity-backed=%d (%.1f%%), proximity-only=%d (%.1f%%), total=%d (%.1f%%)",
        n_full, 100 * n_full / n_total,
        n_prox, 100 * n_prox / n_total,
        n_full + n_prox, 100 * (n_full + n_prox) / n_total,
    )

    valid_mask = ~invalid
    if valid_mask.any():
        logger.info(
            "Risk map: min=%.3f, max=%.3f, mean=%.3f (valid pixels)",
            np.nanmin(combined[valid_mask]),
            np.nanmax(combined[valid_mask]),
            np.nanmean(combined[valid_mask]),
        )
    else:
        logger.warning("Risk map: no valid pixels")

    # Write confidence sidecar next to the risk raster
    confidence_path = output_path.parent / f"{output_path.stem}_confidence.tif"
    write_cog(
        data=confidence,
        output_path=confidence_path,
        crs=vel_meta["crs"],
        transform=vel_meta["transform"],
        nodata=0,
        band_names=["risk_confidence"],
        dtype="uint8",
    )
    logger.info("Risk confidence sidecar: %s", confidence_path.name)

    return write_cog(
        data=combined,
        output_path=output_path,
        crs=vel_meta["crs"],
        transform=vel_meta["transform"],
        nodata=-9999.0,
        band_names=["canal_risk_score"],
        dtype="float32",
    )
