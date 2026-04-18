"""Orbital ramp removal for displacement maps.

Fits and subtracts a linear plane from displacement maps to remove
long-wavelength artifacts from orbital errors and atmospheric
gradients. This is a standalone fallback for cases where MintPy's
built-in deramp is not used.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from peatguard.export.cog import read_raster, write_cog

logger = logging.getLogger(__name__)


def fit_ramp(
    data: np.ndarray,
    nodata: float = -9999.0,
) -> np.ndarray:
    """Fit a linear plane (ramp) to the data using least squares.

    Args:
        data: 2D array with the signal to deramp.
        nodata: NoData value to exclude from fitting.

    Returns:
        2D array representing the estimated ramp.
    """
    height, width = data.shape
    valid = (data != nodata) & np.isfinite(data)

    if valid.sum() < 3:
        logger.warning("Insufficient valid pixels for ramp fitting")
        return np.zeros_like(data)

    row_coords, col_coords = np.meshgrid(
        np.arange(height, dtype=np.float64),
        np.arange(width, dtype=np.float64),
        indexing="ij",
    )

    # Build design matrix [1, row, col] for plane fit
    rows_valid = row_coords[valid].ravel()
    cols_valid = col_coords[valid].ravel()
    values = data[valid].ravel()

    A = np.column_stack([
        np.ones(len(values)),
        rows_valid,
        cols_valid,
    ])

    # Least squares fit
    coeffs, _, _, _ = np.linalg.lstsq(A, values, rcond=None)

    # Reconstruct ramp surface
    ramp = coeffs[0] + coeffs[1] * row_coords + coeffs[2] * col_coords

    logger.info(
        "Ramp coefficients: intercept=%.6f, row_slope=%.6e, col_slope=%.6e",
        coeffs[0],
        coeffs[1],
        coeffs[2],
    )
    return ramp


def deramp(
    data: np.ndarray,
    nodata: float = -9999.0,
) -> np.ndarray:
    """Remove a linear ramp from a 2D array.

    Args:
        data: 2D array to deramp.
        nodata: NoData value to preserve.

    Returns:
        Deramped 2D array with the linear trend removed.
    """
    ramp = fit_ramp(data, nodata=nodata)
    valid = (data != nodata) & np.isfinite(data)

    result = data.copy()
    result[valid] = data[valid] - ramp[valid]

    logger.info(
        "Deramped: original range [%.4f, %.4f] -> [%.4f, %.4f]",
        np.nanmin(data[valid]) if valid.any() else 0,
        np.nanmax(data[valid]) if valid.any() else 0,
        np.nanmin(result[valid]) if valid.any() else 0,
        np.nanmax(result[valid]) if valid.any() else 0,
    )
    return result


def deramp_file(
    input_path: Path,
    output_path: Path,
) -> Path:
    """Deramp a GeoTIFF displacement map.

    Args:
        input_path: Path to the input displacement GeoTIFF.
        output_path: Path for the deramped output.

    Returns:
        Path to the deramped GeoTIFF.
    """
    logger.info("Deramping: %s", input_path.name)

    data, metadata = read_raster(input_path)
    displacement = data[0]

    nodata = metadata["nodata"] if metadata["nodata"] is not None else -9999.0
    deramped = deramp(displacement, nodata=nodata)

    return write_cog(
        data=deramped.astype(np.float32),
        output_path=output_path,
        crs=metadata["crs"],
        transform=metadata["transform"],
        nodata=nodata,
        band_names=["deramped_displacement"],
        dtype="float32",
    )
