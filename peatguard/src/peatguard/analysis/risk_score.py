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
    max_influence_m: float = 1000.0,
) -> np.ndarray:
    """Compute canal proximity risk factor (0-1).

    Risk decreases exponentially with distance from the canal.
    Pixels beyond max_influence_m are assigned zero proximity risk.

    Args:
        distance_m: 2D array of distances to nearest canal in meters.
        max_influence_m: Maximum influence distance in meters.

    Returns:
        2D array of proximity risk scores (0-1, higher = closer to canal).
    """
    # Exponential decay with distance
    # At distance 0: risk = 1.0
    # At max_influence_m: risk ~ 0.05
    decay_rate = 3.0 / max_influence_m
    proximity_risk = np.exp(-decay_rate * distance_m)

    # Zero out beyond influence distance
    proximity_risk[distance_m > max_influence_m] = 0.0

    return proximity_risk.astype(np.float32)


def compute_subsidence_risk(
    velocity_mm_yr: np.ndarray,
    severe_threshold: float = -50.0,
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
    proximity_weight: float = 0.4,
    subsidence_weight: float = 0.6,
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
    proximity_weight: float = 0.4,
    subsidence_weight: float = 0.6,
    max_influence_m: float = 1000.0,
) -> Path:
    """Generate a combined risk score map from velocity and distance rasters.

    Args:
        velocity_path: Path to subsidence velocity GeoTIFF (mm/yr).
        distance_path: Path to canal distance GeoTIFF (meters).
        output_path: Path for the risk score output.
        proximity_weight: Weight for canal proximity risk.
        subsidence_weight: Weight for subsidence risk.
        max_influence_m: Maximum canal influence distance.

    Returns:
        Path to the risk score GeoTIFF.
    """
    logger.info("Generating risk map from %s and %s", velocity_path.name, distance_path.name)

    vel_data, vel_meta = read_raster(velocity_path)
    dist_data, dist_meta = read_raster(distance_path)

    velocity = vel_data[0]
    distance = dist_data[0]

    nodata = vel_meta["nodata"] if vel_meta["nodata"] is not None else -9999.0

    proximity_risk = compute_proximity_risk(distance, max_influence_m)
    subsidence_risk = compute_subsidence_risk(velocity, nodata=nodata)
    combined = compute_combined_risk(
        proximity_risk,
        subsidence_risk,
        proximity_weight,
        subsidence_weight,
    )

    # Mark nodata pixels
    invalid = (velocity == nodata) | ~np.isfinite(velocity)
    combined[invalid] = -9999.0

    logger.info(
        "Risk map: min=%.3f, max=%.3f, mean=%.3f (valid pixels)",
        np.nanmin(combined[~invalid]),
        np.nanmax(combined[~invalid]),
        np.nanmean(combined[~invalid]),
    )

    return write_cog(
        data=combined,
        output_path=output_path,
        crs=vel_meta["crs"],
        transform=vel_meta["transform"],
        nodata=-9999.0,
        band_names=["canal_risk_score"],
        dtype="float32",
    )
