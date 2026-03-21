"""Goldstein phase filtering for interferograms.

Implements the Goldstein adaptive phase filter to reduce noise in
wrapped interferograms while preserving phase gradients. This module
provides a standalone implementation as an alternative to ISCE2's
built-in filter.

Reference:
    Goldstein, R.M. and Werner, C.L. (1998). Radar interferogram
    filtering for geophysical applications. Geophysical Research
    Letters, 25(21), 4035-4038.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.fft import fft2, ifft2

logger = logging.getLogger(__name__)


def goldstein_filter(
    interferogram: np.ndarray,
    alpha: float = 0.8,
    patch_size: int = 32,
    overlap: int = 8,
) -> np.ndarray:
    """Apply Goldstein adaptive filter to a complex interferogram.

    The filter works on overlapping patches in the frequency domain.
    The power spectrum is raised to the exponent alpha, which
    adaptively weights the filter based on the local fringe quality.

    Args:
        interferogram: 2D complex array (wrapped interferogram).
        alpha: Filter strength (0 = no filtering, 1 = maximum).
        patch_size: Size of FFT patches in pixels.
        overlap: Overlap between adjacent patches.

    Returns:
        Filtered complex interferogram.
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")

    height, width = interferogram.shape
    step = patch_size - overlap
    filtered = np.zeros_like(interferogram)
    weight = np.zeros((height, width), dtype=np.float32)

    # Hanning window for smooth patch blending
    window = np.outer(np.hanning(patch_size), np.hanning(patch_size)).astype(np.float32)

    for row_start in range(0, height - patch_size + 1, step):
        for col_start in range(0, width - patch_size + 1, step):
            row_end = row_start + patch_size
            col_end = col_start + patch_size

            patch = interferogram[row_start:row_end, col_start:col_end]

            # FFT of the patch
            spectrum = fft2(patch)

            # Compute power spectrum and apply adaptive weighting
            power = np.abs(spectrum)
            power_max = power.max()
            if power_max > 0:
                normalized_power = power / power_max
                filter_weights = normalized_power ** alpha
                spectrum_filtered = spectrum * filter_weights
            else:
                spectrum_filtered = spectrum

            # Inverse FFT
            patch_filtered = ifft2(spectrum_filtered)

            # Accumulate with windowed blending
            filtered[row_start:row_end, col_start:col_end] += patch_filtered * window
            weight[row_start:row_end, col_start:col_end] += window

    # Normalize by accumulated weights
    mask = weight > 0
    filtered[mask] /= weight[mask]

    # Copy unfiltered edges where patches don't reach
    filtered[~mask] = interferogram[~mask]

    logger.info(
        "Goldstein filter applied (alpha=%.2f, patch=%d, overlap=%d)",
        alpha,
        patch_size,
        overlap,
    )
    return filtered


def filter_interferogram_file(
    input_path: Path,
    output_path: Path,
    alpha: float = 0.8,
    patch_size: int = 32,
) -> Path:
    """Apply Goldstein filter to an interferogram stored on disk.

    Reads a complex interferogram from a binary or GeoTIFF file,
    applies the Goldstein filter, and writes the result.

    Args:
        input_path: Path to the input interferogram.
        output_path: Path for filtered output.
        alpha: Filter strength.
        patch_size: FFT patch size.

    Returns:
        Path to the filtered interferogram.
    """
    logger.info("Filtering interferogram: %s", input_path.name)

    # Handle both numpy binary and rasterio-readable formats
    if input_path.suffix == ".npy":
        ifg = np.load(str(input_path))
        filtered = goldstein_filter(ifg, alpha=alpha, patch_size=patch_size)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(output_path), filtered)
    else:
        import rasterio

        with rasterio.open(input_path) as src:
            # Read as complex if available, otherwise construct from bands
            if np.issubdtype(src.dtypes[0], np.complexfloating):
                ifg = src.read(1)
            elif src.count >= 2:
                real = src.read(1)
                imag = src.read(2)
                ifg = real + 1j * imag
            else:
                raise ValueError(f"Cannot interpret {input_path} as complex interferogram")

            profile = src.profile.copy()

        filtered = goldstein_filter(ifg, alpha=alpha, patch_size=patch_size)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        profile.update(dtype="complex64", count=1)
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(filtered, 1)

    logger.info("Filtered output: %s", output_path.name)
    return output_path
