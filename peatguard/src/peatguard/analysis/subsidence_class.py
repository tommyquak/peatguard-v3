"""Subsidence severity classification.

Classifies velocity maps into severity categories based on
thresholds from peatland literature. The classification follows
the interpretation guidelines in the PeatGuard README:

    Class 1 (Severe):       < -50 mm/yr   (heavily drained peat)
    Class 2 (Active drying): -50 to -20    (ongoing drying)
    Class 3 (Stable):       -20 to 0       (stable or rewetted)
    Class 4 (Noise/uplift):  > 0           (measurement noise or rebound)
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
CLASS_STABLE = 3
CLASS_NOISE_UPLIFT = 4
CLASS_NODATA = 0

CLASS_LABELS = {
    CLASS_NODATA: "NoData",
    CLASS_SEVERE: "Severe (< -50 mm/yr)",
    CLASS_ACTIVE_DRYING: "Active drying (-50 to -20 mm/yr)",
    CLASS_STABLE: "Stable (-20 to 0 mm/yr)",
    CLASS_NOISE_UPLIFT: "Noise/Uplift (> 0 mm/yr)",
}


def classify_subsidence(
    velocity_mm_yr: np.ndarray,
    nodata: float = -9999.0,
    thresholds: Optional[ClassificationConfig] = None,
) -> np.ndarray:
    """Classify subsidence velocity into severity categories.

    Args:
        velocity_mm_yr: 2D array of velocity in mm/yr.
        nodata: NoData value in the input.
        thresholds: Classification thresholds. Uses defaults if None.

    Returns:
        2D uint8 array of class codes (0=nodata, 1-4=classes).
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
        & (velocity_mm_yr < thresholds.stable_threshold)
    ] = CLASS_STABLE
    classified[valid & (velocity_mm_yr >= thresholds.stable_threshold)] = CLASS_NOISE_UPLIFT

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
) -> Path:
    """Classify a subsidence velocity GeoTIFF and write the result.

    Args:
        velocity_path: Path to velocity GeoTIFF (mm/yr).
        output_path: Path for classified output.
        thresholds: Classification thresholds.

    Returns:
        Path to the classified GeoTIFF.
    """
    logger.info("Classifying subsidence: %s", velocity_path.name)

    data, metadata = read_raster(velocity_path)
    velocity = data[0]

    nodata = metadata["nodata"] if metadata["nodata"] is not None else -9999.0
    classified = classify_subsidence(velocity, nodata=nodata, thresholds=thresholds)

    return write_cog(
        data=classified,
        output_path=output_path,
        crs=metadata["crs"],
        transform=metadata["transform"],
        nodata=CLASS_NODATA,
        band_names=["subsidence_class"],
        dtype="uint8",
    )
