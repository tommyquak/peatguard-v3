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

    # For GCP-based data (Sentinel-1 GRD), use GDAL Warp via a VRT
    # that embeds the GCPs. This handles the polynomial transform correctly,
    # unlike rasterio.warp.reproject which expects affine src_transform.
    with rasterio.open(input_path) as src:
        src_crs = src.crs
        gcps = src.gcps
        has_gcps = gcps and len(gcps[0]) > 0

    if has_gcps:
        _terrain_correct_gcps(input_path, output_path, dst_crs, resolution_m, resampling, bounds)
    else:
        _terrain_correct_affine(input_path, output_path, dst_crs, resolution_m, resampling, bounds)

    logger.info("Geocoded output: %s", output_path.name)
    return output_path


def _terrain_correct_gcps(
    input_path: Path,
    output_path: Path,
    dst_crs: CRS,
    resolution_m: float,
    resampling: Resampling,
    bounds: Optional[tuple[float, float, float, float]] = None,
) -> None:
    """Reproject GCP-based imagery using GDAL Warp (handles polynomial transforms).

    Args:
        bounds: Optional (west, south, east, north) in target CRS to clip output.
                Without bounds, produces full-swath output which can be very large.
    """
    from osgeo import gdal

    gdal.UseExceptions()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    epsg = dst_crs.to_epsg()
    srs_str = f"EPSG:{epsg}" if epsg else dst_crs.to_wkt()

    warp_kwargs = dict(
        dstSRS=srs_str,
        xRes=resolution_m,
        yRes=resolution_m,
        resampleAlg="bilinear",
        format="GTiff",
        tps=True,  # Thin Plate Spline from GCPs
        errorThreshold=0.125,
    )

    # Clip to bounds if provided (prevents OOM from full-swath geocoding)
    if bounds:
        # bounds is (west, south, east, north) in geographic coords.
        # Convert to target CRS if needed.
        from pyproj import Transformer
        transformer = Transformer.from_crs("EPSG:4326", srs_str, always_xy=True)
        x_min, y_min = transformer.transform(bounds[0], bounds[1])
        x_max, y_max = transformer.transform(bounds[2], bounds[3])
        # Add 10km buffer for edge effects
        buffer = 10000  # meters
        warp_kwargs["outputBounds"] = (x_min - buffer, y_min - buffer,
                                        x_max + buffer, y_max + buffer)
        logger.info("Clipping to bounds: [%.0f, %.0f, %.0f, %.0f] (with 10km buffer)",
                     x_min - buffer, y_min - buffer, x_max + buffer, y_max + buffer)

    warp_options = gdal.WarpOptions(**warp_kwargs)

    ds = gdal.Warp(str(output_path), str(input_path), options=warp_options)
    if ds is None:
        raise RuntimeError(f"GDAL Warp failed for {input_path}")
    width = ds.RasterXSize
    height = ds.RasterYSize
    ds = None  # close

    logger.info("GCP warp complete: %dx%d", width, height)


def _terrain_correct_affine(
    input_path: Path,
    output_path: Path,
    dst_crs: CRS,
    resolution_m: float,
    resampling: Resampling,
    bounds: Optional[tuple[float, float, float, float]],
) -> None:
    """Reproject affine-transform imagery using rasterio.warp."""
    with rasterio.open(input_path) as src:
        src_crs = src.crs
        if src.transform.is_identity or (src.transform.a == 1 and src.transform.e == -1):
            logger.warning("Source has no geolocation (identity transform).")

        if bounds is not None:
            dst_transform, dst_width, dst_height = calculate_default_transform(
                src_crs, dst_crs, src.width, src.height,
                *bounds, resolution=resolution_m,
            )
        else:
            dst_transform, dst_width, dst_height = calculate_default_transform(
                src_crs, dst_crs, src.width, src.height,
                *src.bounds, resolution=resolution_m,
            )

        profile = src.profile.copy()
        profile.update(
            crs=dst_crs,
            transform=dst_transform,
            width=dst_width,
            height=dst_height,
            driver="GTiff",
        )
        profile.pop("gcps", None)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(output_path, "w", **profile) as dst:
            for band_idx in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, band_idx),
                    destination=rasterio.band(dst, band_idx),
                    src_transform=src.transform,
                    src_crs=src_crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=resampling,
                )

    logger.info("Affine reproject complete: %dx%d", dst_width, dst_height)


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
