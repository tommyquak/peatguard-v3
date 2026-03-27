"""Subsidence severity classification.

Classifies velocity maps into severity categories based on
thresholds from peatland literature. The classification follows
the interpretation guidelines in the PeatGuard README:

    Class 1 (Severe):          < -50 mm/yr   (heavily drained peat)
    Class 2 (Active drying):   -50 to -20    (ongoing drying)
    Class 3 (Moderate drying): -20 to -5     (slow but ongoing carbon loss)
    Class 4 (Stable):          -5 to +5      (natural variability range)
    Class 5 (Rebound/noise):   > +5          (measurement noise or rebound)
    Class 6 (Water):           water mask

Natural peat accumulation is ~1 mm/yr. Any subsidence below -5 mm/yr
on peat indicates net carbon loss (Hooijer et al., 2012), so the
"stable" class is restricted to the +/-5 mm/yr natural variability
envelope rather than the previous -20 to 0 range.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from peatguard.config import ClassificationConfig
from peatguard.export.cog import read_raster, write_cog

logger = logging.getLogger(__name__)

# Class codes and labels
CLASS_SEVERE = 1
CLASS_ACTIVE_DRYING = 2
CLASS_MODERATE_DRYING = 3
CLASS_STABLE = 4
CLASS_REBOUND_NOISE = 5
CLASS_WATER = 6
CLASS_NODATA = 0

CLASS_LABELS = {
    CLASS_NODATA: "NoData",
    CLASS_SEVERE: "Severe (< -50 mm/yr)",
    CLASS_ACTIVE_DRYING: "Active drying (-50 to -20 mm/yr)",
    CLASS_MODERATE_DRYING: "Moderate drying (-20 to -5 mm/yr)",
    CLASS_STABLE: "Stable (-5 to +5 mm/yr)",
    CLASS_REBOUND_NOISE: "Rebound/Noise (> +5 mm/yr)",
    CLASS_WATER: "Water body",
}


def classify_subsidence(
    velocity_mm_yr: np.ndarray,
    nodata: float = -9999.0,
    thresholds: Optional[ClassificationConfig] = None,
    water_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Classify subsidence velocity into severity categories.

    Args:
        velocity_mm_yr: 2D array of velocity in mm/yr.
        nodata: NoData value in the input.
        thresholds: Classification thresholds. Uses defaults if None.
        water_mask: Optional boolean 2D array where True = water pixel.
            Water pixels are assigned CLASS_WATER (6) regardless of
            velocity, preventing false subsidence detections over
            open water bodies.

    Returns:
        2D uint8 array of class codes (0=nodata, 1-6=classes).
    """
    if thresholds is None:
        thresholds = ClassificationConfig()

    classified = np.full_like(velocity_mm_yr, CLASS_NODATA, dtype=np.uint8)
    valid = (velocity_mm_yr != nodata) & np.isfinite(velocity_mm_yr)

    classified[valid & (velocity_mm_yr < thresholds.severe_threshold)] = CLASS_SEVERE
    classified[
        valid
        & (velocity_mm_yr >= thresholds.severe_threshold)
        & (velocity_mm_yr < thresholds.active_drying_threshold)
    ] = CLASS_ACTIVE_DRYING
    classified[
        valid
        & (velocity_mm_yr >= thresholds.active_drying_threshold)
        & (velocity_mm_yr < thresholds.moderate_drying_threshold)
    ] = CLASS_MODERATE_DRYING
    classified[
        valid
        & (velocity_mm_yr >= thresholds.moderate_drying_threshold)
        & (velocity_mm_yr < thresholds.stable_threshold)
    ] = CLASS_STABLE
    classified[valid & (velocity_mm_yr >= thresholds.stable_threshold)] = CLASS_REBOUND_NOISE

    # Apply water mask: override any classification on water pixels
    if water_mask is not None:
        if water_mask.shape != velocity_mm_yr.shape:
            logger.warning(
                "Water mask shape %s does not match velocity shape %s, skipping",
                water_mask.shape,
                velocity_mm_yr.shape,
            )
        else:
            n_reclassified = ((classified != CLASS_NODATA) & water_mask).sum()
            classified[water_mask] = CLASS_WATER
            logger.info(
                "Water mask applied: %d pixels reclassified to water "
                "(%d were previously non-nodata)",
                water_mask.sum(),
                n_reclassified,
            )

    # Log class distribution
    for code, label in CLASS_LABELS.items():
        count = (classified == code).sum()
        pct = count / classified.size * 100 if classified.size > 0 else 0
        logger.info("  %s: %d pixels (%.1f%%)", label, count, pct)

    return classified


def classify_subsidence_file(
    velocity_path: Path,
    output_path: Path,
    thresholds: Optional[ClassificationConfig] = None,
    water_mask_path: Optional[Path] = None,
) -> Path:
    """Classify a subsidence velocity GeoTIFF and write the result.

    Args:
        velocity_path: Path to velocity GeoTIFF (mm/yr).
        output_path: Path for classified output.
        thresholds: Classification thresholds.
        water_mask_path: Optional path to water mask GeoTIFF (uint8,
            1=water). If provided, water pixels are classified as
            CLASS_WATER instead of a subsidence class.

    Returns:
        Path to the classified GeoTIFF.
    """
    logger.info("Classifying subsidence: %s", velocity_path.name)

    data, metadata = read_raster(velocity_path)
    velocity = data[0]

    # Load water mask if provided
    water_mask = None
    if water_mask_path is not None and water_mask_path.exists():
        logger.info("Loading water mask: %s", water_mask_path.name)
        wm_data, wm_meta = read_raster(water_mask_path)
        wm_arr = wm_data[0].astype(bool)

        # Handle CRS/shape mismatch by reprojecting water mask to velocity grid
        if wm_arr.shape != velocity.shape:
            logger.info(
                "Reprojecting water mask from %s to velocity grid %s",
                wm_arr.shape,
                velocity.shape,
            )
            import rasterio
            from rasterio.warp import Resampling, reproject

            wm_reprojected = np.zeros(velocity.shape, dtype=np.uint8)
            reproject(
                source=wm_arr.astype(np.uint8),
                destination=wm_reprojected,
                src_transform=wm_meta["transform"],
                src_crs=wm_meta["crs"],
                dst_transform=metadata["transform"],
                dst_crs=metadata["crs"],
                resampling=Resampling.nearest,
            )
            water_mask = wm_reprojected.astype(bool)
        else:
            water_mask = wm_arr

    nodata = metadata["nodata"] if metadata["nodata"] is not None else -9999.0
    classified = classify_subsidence(
        velocity, nodata=nodata, thresholds=thresholds, water_mask=water_mask
    )

    return write_cog(
        data=classified,
        output_path=output_path,
        crs=metadata["crs"],
        transform=metadata["transform"],
        nodata=CLASS_NODATA,
        band_names=["subsidence_class"],
        dtype="uint8",
    )
