"""Geocoding and terrain correction for InSAR products.

Reprojects InSAR outputs from radar coordinates to map-projected
coordinates using a DEM for orthorectification. Supports both
ISCE2-native geocoding and rasterio-based reprojection.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.warp import calculate_default_transform, reproject

from peatguard.config import PeatGuardConfig
from peatguard.export.cog import write_cog

logger = logging.getLogger(__name__)


def geocode_array(
    data: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    target_crs: int = 32649,
    resolution_m: float = 10.0,
    nodata: float = -9999.0,
    bounds: Optional[tuple[float, float, float, float]] = None,
) -> tuple[np.ndarray, rasterio.transform.Affine, CRS]:
    """Geocode a radar-geometry array using lat/lon coordinate arrays.

    Uses the latitude and longitude grids (from ISCE2's geometry files)
    to map radar pixels to a regular projected grid.

    Args:
        data: 2D array in radar geometry.
        lat: 2D array of latitudes for each pixel.
        lon: 2D array of longitudes for each pixel.
        target_crs: Target EPSG code.
        resolution_m: Output pixel spacing in meters.
        nodata: NoData fill value.
        bounds: Optional (west, south, east, north) in target CRS.

    Returns:
        Tuple of (geocoded_array, transform, crs).
    """
    from pyproj import Transformer

    logger.info("Geocoding array (%dx%d) to EPSG:%d", data.shape[0], data.shape[1], target_crs)

    dst_crs = CRS.from_epsg(target_crs)

    # Transform lat/lon to target CRS
    transformer = Transformer.from_crs("EPSG:4326", dst_crs, always_xy=True)
    x, y = transformer.transform(lon, lat)

    if bounds is None:
        x_min, x_max = np.nanmin(x), np.nanmax(x)
        y_min, y_max = np.nanmin(y), np.nanmax(y)
    else:
        x_min, y_min, x_max, y_max = bounds

    # Compute output grid dimensions
    width = int(np.ceil((x_max - x_min) / resolution_m))
    height = int(np.ceil((y_max - y_min) / resolution_m))

    transform = from_bounds(x_min, y_min, x_max, y_max, width, height)

    # Map source pixels to output grid
    from rasterio.transform import rowcol

    geocoded = np.full((height, width), nodata, dtype=np.float32)

    # Flatten for vectorized operation
    valid = ~np.isnan(data) & ~np.isnan(x) & ~np.isnan(y)
    x_valid = x[valid]
    y_valid = y[valid]
    data_valid = data[valid]

    # Convert projected coordinates to pixel indices
    cols = ((x_valid - x_min) / resolution_m).astype(int)
    rows = ((y_max - y_valid) / resolution_m).astype(int)

    # Clip to valid range
    valid_idx = (rows >= 0) & (rows < height) & (cols >= 0) & (cols < width)
    geocoded[rows[valid_idx], cols[valid_idx]] = data_valid[valid_idx]

    logger.info("Geocoded output: %dx%d pixels", height, width)
    return geocoded, transform, dst_crs


def geocode_geotiff(
    input_path: Path,
    output_path: Path,
    target_crs: int = 32649,
    resolution_m: float = 10.0,
    resampling: Resampling = Resampling.bilinear,
    bounds: Optional[tuple[float, float, float, float]] = None,
) -> Path:
    """Reproject a GeoTIFF to the target CRS.

    For inputs that already have geospatial metadata (CRS + transform),
    this uses rasterio's standard reprojection workflow.

    Args:
        input_path: Input GeoTIFF path.
        output_path: Output path.
        target_crs: Target EPSG code.
        resolution_m: Output pixel spacing.
        resampling: Resampling method.
        bounds: Optional output bounds in target CRS.

    Returns:
        Path to the geocoded GeoTIFF.
    """
    logger.info("Geocoding %s to EPSG:%d at %.1fm", input_path.name, target_crs, resolution_m)
    dst_crs = CRS.from_epsg(target_crs)

    with rasterio.open(input_path) as src:
        if bounds is not None:
            dst_transform, dst_width, dst_height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *bounds, resolution=resolution_m
            )
        else:
            dst_transform, dst_width, dst_height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds, resolution=resolution_m
            )

        profile = src.profile.copy()
        profile.update(
            crs=dst_crs,
            transform=dst_transform,
            width=dst_width,
            height=dst_height,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output_path, "w", **profile) as dst:
            for band in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, band),
                    destination=rasterio.band(dst, band),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=resampling,
                )

    logger.info("Geocoded: %s (%dx%d)", output_path.name, dst_width, dst_height)
    return output_path
