"""Canal detection from VV backscatter imagery.

Identifies drainage canals and ditches in peatlands using VV
backscatter. Canals appear as dark linear features because water
surfaces produce specular reflection (low backscatter). The
detection pipeline uses thresholding, morphological operations,
and connected component analysis to extract canal networks.

Future: U-Net semantic segmentation model for improved detection.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.ndimage import distance_transform_edt

from peatguard.export.cog import read_raster

logger = logging.getLogger(__name__)


def threshold_canals(
    vv_data: np.ndarray,
    percentile: float = 10.0,
    nodata: float = -9999.0,
) -> np.ndarray:
    """Detect canals using a percentile-based backscatter threshold.

    Canals are dark features in VV backscatter. The bottom N percentile
    of backscatter values (excluding nodata) are classified as potential
    canal pixels.

    Args:
        vv_data: 2D array of VV backscatter (dB or linear scale).
        percentile: Percentile threshold for canal classification.
        nodata: NoData value to exclude.

    Returns:
        Binary mask where True = canal pixel.
    """
    valid = (vv_data != nodata) & np.isfinite(vv_data) & (vv_data > 0)

    if not np.any(valid):
        logger.warning("No valid pixels for canal detection")
        return np.zeros_like(vv_data, dtype=bool)

    threshold = np.percentile(vv_data[valid], percentile)
    canal_mask = (vv_data < threshold) & valid

    logger.info(
        "Canal threshold: %.4f (%.1f percentile), %d pixels detected",
        threshold,
        percentile,
        canal_mask.sum(),
    )
    return canal_mask


def morphological_cleanup(
    canal_mask: np.ndarray,
    min_length_pixels: int = 10,
    dilation_size: int = 3,
) -> np.ndarray:
    """Clean up canal detections using morphological operations.

    Removes noise (small isolated detections) and connects nearby
    canal fragments. Uses skimage morphology for line-aware processing.

    Args:
        canal_mask: Binary canal mask.
        min_length_pixels: Minimum connected component length to retain.
        dilation_size: Size of dilation structuring element.

    Returns:
        Cleaned binary canal mask.
    """
    from skimage.morphology import (
        binary_closing,
        binary_dilation,
        disk,
        remove_small_objects,
        skeletonize,
    )

    # Close small gaps between canal segments
    closed = binary_closing(canal_mask, disk(2))

    # Remove small isolated detections
    cleaned = remove_small_objects(closed, min_size=min_length_pixels)

    # Optional: thin to centerline for vector extraction
    # skeleton = skeletonize(cleaned)

    # Slight dilation to recover canal width
    if dilation_size > 0:
        cleaned = binary_dilation(cleaned, disk(dilation_size // 2))

    logger.info(
        "Morphological cleanup: %d -> %d canal pixels",
        canal_mask.sum(),
        cleaned.sum(),
    )
    return cleaned


def compute_canal_distance(
    canal_mask: np.ndarray,
    pixel_resolution_m: float = 10.0,
) -> np.ndarray:
    """Compute distance from every pixel to the nearest canal.

    Uses scipy's Euclidean distance transform, scaled by pixel
    resolution to produce distances in meters.

    Args:
        canal_mask: Binary canal mask.
        pixel_resolution_m: Pixel size in meters.

    Returns:
        2D array of distances to nearest canal in meters.
    """
    distance_pixels = distance_transform_edt(~canal_mask)
    distance_m = distance_pixels * pixel_resolution_m

    logger.info(
        "Canal distance: min=%.1f m, max=%.1f m, mean=%.1f m",
        distance_m.min(),
        distance_m.max(),
        distance_m.mean(),
    )
    return distance_m


def analyze_subsidence_by_distance(
    subsidence: np.ndarray,
    distance_m: np.ndarray,
    intervals_m: Optional[list[float]] = None,
    nodata: float = -9999.0,
) -> list[dict]:
    """Analyze mean subsidence at different distances from canals.

    Bins pixels by their distance to the nearest canal and computes
    mean subsidence for each bin. This reveals the spatial influence
    of drainage canals on peat subsidence.

    Args:
        subsidence: 2D array of subsidence values (mm/yr).
        distance_m: 2D array of distances to nearest canal (meters).
        intervals_m: Distance bin boundaries in meters.
        nodata: NoData value in the subsidence array.

    Returns:
        List of dicts with 'start_m', 'end_m', 'mean_subsidence',
        'pixel_count' for each distance bin.
    """
    if intervals_m is None:
        intervals_m = [0, 50, 100, 250, 500, 1000]

    valid = (subsidence != nodata) & np.isfinite(subsidence)
    results = []

    for i in range(len(intervals_m) - 1):
        start = intervals_m[i]
        end = intervals_m[i + 1]
        bin_mask = valid & (distance_m >= start) & (distance_m < end)
        pixel_count = bin_mask.sum()

        if pixel_count > 0:
            mean_sub = float(np.nanmean(subsidence[bin_mask]))
        else:
            mean_sub = float("nan")

        results.append({
            "start_m": start,
            "end_m": end,
            "mean_subsidence_mm_yr": mean_sub,
            "pixel_count": int(pixel_count),
        })

    return results


def detect_canals(
    vv_path: Path,
    output_mask_path: Optional[Path] = None,
    output_distance_path: Optional[Path] = None,
    percentile: float = 10.0,
    min_length_pixels: int = 10,
) -> tuple[np.ndarray, np.ndarray]:
    """Full canal detection pipeline from a VV backscatter GeoTIFF.

    Args:
        vv_path: Path to VV backscatter GeoTIFF.
        output_mask_path: Optional path to save canal mask as GeoTIFF.
        output_distance_path: Optional path to save distance map as GeoTIFF.
        percentile: Backscatter percentile threshold.
        min_length_pixels: Minimum connected component size.

    Returns:
        Tuple of (canal_mask, distance_map_meters).
    """
    data, metadata = read_raster(vv_path)
    vv = data[0]  # First band

    # Get pixel resolution from transform
    pixel_res = abs(metadata["transform"][0])

    # Detect and clean
    raw_mask = threshold_canals(vv, percentile=percentile)
    clean_mask = morphological_cleanup(raw_mask, min_length_pixels=min_length_pixels)
    distance_m = compute_canal_distance(clean_mask, pixel_resolution_m=pixel_res)

    # Optionally save outputs
    if output_mask_path is not None:
        from peatguard.export.cog import write_cog

        write_cog(
            data=clean_mask.astype(np.uint8),
            output_path=output_mask_path,
            crs=metadata["crs"],
            transform=metadata["transform"],
            nodata=255,
            band_names=["canal_mask"],
            dtype="uint8",
        )

    if output_distance_path is not None:
        from peatguard.export.cog import write_cog

        write_cog(
            data=distance_m.astype(np.float32),
            output_path=output_distance_path,
            crs=metadata["crs"],
            transform=metadata["transform"],
            nodata=-9999.0,
            band_names=["canal_distance_m"],
            dtype="float32",
        )

    return clean_mask, distance_m
