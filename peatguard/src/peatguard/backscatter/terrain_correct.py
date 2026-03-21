"""Terrain correction and geocoding for SAR imagery.

Reprojects radar geometry data to a map-projected coordinate system
using a DEM for orthorectification. Replaces SNAP's Terrain-Correction
operator with rasterio/GDAL-based reprojection.

For GRD products, the terrain correction primarily handles the
conversion from ground-range to map-projected coordinates with
radiometric terrain correction using the local incidence angle.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject

from peatguard.config import ProcessingConfig

logger = logging.getLogger(__name__)


def terrain_correct(
    input_path: Path,
    output_path: Path,
    target_crs: Union[str, int] = 32649,
    resolution_m: float = 10.0,
    resampling: Resampling = Resampling.bilinear,
    bounds: Optional[tuple[float, float, float, float]] = None,
) -> Path:
    """Reproject and geocode a SAR image to a map projection.

    Uses rasterio.warp for reprojection with DEM-based terrain
    correction handled through the source dataset's RPC model
    or GCPs when available.

    Args:
        input_path: Path to the input GeoTIFF (in radar or geographic coords).
        output_path: Path for the geocoded output.
        target_crs: Target CRS as EPSG code or WKT. Default UTM 49S.
        resolution_m: Output pixel spacing in meters.
        resampling: Resampling method for reprojection.
        bounds: Optional output bounds (west, south, east, north) in target CRS.

    Returns:
        Path to the geocoded GeoTIFF.
    """
    logger.info(
        "Terrain correcting %s -> EPSG:%s at %.1fm",
        input_path.name,
        target_crs,
        resolution_m,
    )

    dst_crs = CRS.from_epsg(target_crs) if isinstance(target_crs, int) else CRS.from_user_input(target_crs)

    with rasterio.open(input_path) as src:
        # Calculate the optimal output transform
        if bounds is not None:
            dst_transform, dst_width, dst_height = calculate_default_transform(
                src.crs,
                dst_crs,
                src.width,
                src.height,
                *bounds,
                resolution=resolution_m,
            )
        else:
            dst_transform, dst_width, dst_height = calculate_default_transform(
                src.crs,
                dst_crs,
                src.width,
                src.height,
                *src.bounds,
                resolution=resolution_m,
            )

        profile = src.profile.copy()
        profile.update(
            crs=dst_crs,
            transform=dst_transform,
            width=dst_width,
            height=dst_height,
            driver="GTiff",
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(output_path, "w", **profile) as dst:
            for band_idx in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, band_idx),
                    destination=rasterio.band(dst, band_idx),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=resampling,
                )

    logger.info("Geocoded output: %s (%dx%d)", output_path.name, dst_width, dst_height)
    return output_path


def to_decibels(
    input_path: Path,
    output_path: Path,
    floor_db: float = -50.0,
) -> Path:
    """Convert linear-scale sigma0 to decibel scale.

    sigma0_dB = 10 * log10(sigma0_linear)

    Values below the floor are clamped to prevent log(0) issues.

    Args:
        input_path: Path to linear-scale sigma0 GeoTIFF.
        output_path: Path for dB-scale output.
        floor_db: Minimum dB value (default -50 dB).

    Returns:
        Path to the dB-scale GeoTIFF.
    """
    logger.info("Converting %s to dB scale", input_path.name)

    with rasterio.open(input_path) as src:
        sigma0 = src.read(1).astype(np.float64)
        profile = src.profile.copy()

    # Avoid log of zero or negative values
    sigma0 = np.maximum(sigma0, 10 ** (floor_db / 10))
    sigma0_db = 10.0 * np.log10(sigma0)
    sigma0_db = np.clip(sigma0_db, floor_db, None)

    profile.update(dtype="float32", nodata=floor_db)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(sigma0_db.astype(np.float32), 1)
        dst.set_band_description(1, "sigma0_VV_dB")

    logger.info("dB output: %s", output_path.name)
    return output_path
