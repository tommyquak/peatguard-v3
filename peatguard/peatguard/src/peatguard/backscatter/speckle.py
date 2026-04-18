"""Speckle filtering for SAR backscatter imagery.

Implements the Lee Sigma filter using scipy, replacing SNAP's
built-in speckle filter. The Lee Sigma filter preserves edges
better than simple boxcar averaging while reducing speckle noise.

Reference:
    Lee, J.-S. (1983). Digital image smoothing and the sigma filter.
    Computer Vision, Graphics, and Image Processing, 24(2), 255-269.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.ndimage import uniform_filter

logger = logging.getLogger(__name__)


def lee_sigma_filter(
    data: np.ndarray,
    window_size: int = 7,
    sigma_factor: float = 0.9,
    num_looks: int = 1,
) -> np.ndarray:
    """Apply Lee Sigma speckle filter to a SAR intensity image.

    The filter computes local statistics within a window and replaces
    the center pixel with a weighted average of pixels within a sigma
    range, preserving edges and point targets.

    Args:
        data: 2D array of SAR intensity values (linear scale, not dB).
        window_size: Filter window size (must be odd).
        sigma_factor: Sigma multiplier for the acceptance range.
        num_looks: Number of looks in the input image. GRD typically = 1.

    Returns:
        Filtered 2D array with reduced speckle.
    """
    if window_size % 2 == 0:
        raise ValueError(f"window_size must be odd, got {window_size}")

    # Compute local mean and variance
    local_mean = uniform_filter(data, size=window_size, mode="reflect")
    local_sq_mean = uniform_filter(data ** 2, size=window_size, mode="reflect")
    local_var = local_sq_mean - local_mean ** 2
    local_var = np.maximum(local_var, 0)  # Numerical stability

    # Coefficient of variation for speckle noise
    # For a single-look SAR image, theoretical Cv = 1.0
    noise_var = local_mean ** 2 / max(num_looks, 1)

    # Weight factor based on local statistics
    # w = 1 means keep original, w = 0 means use local mean
    signal_var = np.maximum(local_var - noise_var, 0)
    denom = signal_var + noise_var
    weight = np.where(denom > 0, signal_var / denom, 0.0)

    # Lee filter: output = mean + weight * (pixel - mean)
    filtered = local_mean + weight * (data - local_mean)

    # Apply sigma range constraint
    # Only accept pixels within sigma_factor * std of local mean
    local_std = np.sqrt(local_var)
    sigma_range = sigma_factor * local_std
    lower = local_mean - sigma_range
    upper = local_mean + sigma_range

    # Pixels outside sigma range are replaced with local mean
    out_of_range = (data < lower) | (data > upper)
    filtered = np.where(out_of_range, local_mean, filtered)

    return filtered.astype(data.dtype)


def apply_speckle_filter(
    input_path: Path,
    output_path: Path,
    window_size: int = 7,
    sigma_factor: float = 0.9,
) -> Path:
    """Apply speckle filter to a calibrated GeoTIFF.

    Args:
        input_path: Path to input calibrated sigma0 GeoTIFF.
        output_path: Path for filtered output.
        window_size: Filter window size (default 7).
        sigma_factor: Sigma multiplier (default 0.9).

    Returns:
        Path to the filtered GeoTIFF.
    """
    import rasterio

    logger.info(
        "Applying Lee Sigma filter (window=%d) to %s",
        window_size,
        input_path.name,
    )

    with rasterio.open(input_path) as src:
        data = src.read(1)
        profile = src.profile.copy()
        gcps = src.gcps

    filtered = lee_sigma_filter(data, window_size=window_size, sigma_factor=sigma_factor)

    # Write filtered output, preserving GCPs for geocoding downstream.
    # GCPs must be written during the initial file creation -- reopening
    # in r+ mode after write can silently drop them.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(filtered, 1)
        if gcps and len(gcps[0]) > 0:
            dst.gcps = gcps

    logger.info("Filtered output: %s", output_path.name)
    return output_path
